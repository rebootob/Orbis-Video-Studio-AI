"""P4-WP020-LIVE R3 bounded one-shot provider UAT runner.

This is intentionally not a reusable batch runner. The paid workflow must bind
it to an exact Owner-authorized main SHA and consume the R3 Issue #63 fence
immediately before the first possible chargeable provider request.

R3 contract: OpenAI x1 -> Gemini x1 -> Vidu x1 -> ElevenLabs x3, sequential,
no quality retry/regeneration, hard cap USD 1.00, fail closed on uncertainty.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.audio_clip import AudioClip
from app.models.generation_audit import GenerationAuditLog
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.render_job import RenderJob, RenderJobStatus
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story
from app.providers.audio.factory import AudioProviderFactory
from app.providers.factory import ProviderFactory
from app.providers.image.factory import ImageProviderFactory
from app.services.archive.export_service import ProjectExportService
from app.services.archive.import_service import ProjectImportService
from app.services.assembly import AssemblyService
from app.services.audio_production import AudioProductionService
from app.services.budget import BudgetService
from app.services.cost_ledger import CostLedgerService
from app.services.job_dispatch import JobDispatchService
from app.services.keyframe_generation import KeyframeGenerationService
from app.services.production_orchestrator import ProductionOrchestrator
from app.services.qc import QCService
from app.services.render_job import RenderJobService
from app.services.render_worker import CloudRenderWorker
from app.services.storage.factory import get_storage_provider
from app.services.subtitle_control import SubtitleService
from wp020_live_r3_contract import (
    HARD_CAP_USD,
    MAX_PAID_CALLS,
    PAID_CALL_SEQUENCE,
    R3_EXECUTION_ID,
    enforce_budget,
    next_paid_call,
    require_provider_success,
    sanitize_audio_clip,
    sanitize_generation_job,
    validate_runtime_binding,
)

EXECUTION_ID = os.environ.get("WP020_LIVE_EXECUTION_ID", "")
AUTHORIZED_MAIN_SHA = os.environ.get("AUTHORIZED_MAIN_SHA", "")
EVIDENCE_DIR = Path(os.environ.get("WP020_LIVE_EVIDENCE_DIR", "live_evidence"))

state: dict[str, Any] = {
    "execution_id": EXECUTION_ID,
    "authorized_main_sha": AUTHORIZED_MAIN_SHA,
    "status": "STARTED",
    "phase": "INIT",
    "paid_call_count": 0,
    "paid_calls": [],
    "spend_usd": 0.0,
    "project_id": None,
    "shot_id": None,
    "active_audio_clip_id": None,
    "provider_evidence": {},
    "failure_evidence": {},
    "downstream": {},
    "started_at": datetime.now(timezone.utc).isoformat(),
}


def _redact(text: str) -> str:
    result = str(text)
    for name in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "VIDU_API_KEY",
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_DEFAULT_VOICE_ID",
    ):
        value = os.environ.get(name)
        if value:
            result = result.replace(value, "[REDACTED]")
    return result[:2000]


def _write_evidence() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    (EVIDENCE_DIR / "summary.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    if state["status"] == "PASS":
        body = (
            f"LIVE_EXECUTION_PASS: {EXECUTION_ID}\n\n"
            f"Project: `{state.get('project_id')}`\n"
            f"Chargeable calls: {state.get('paid_call_count')}/{MAX_PAID_CALLS}\n"
            f"Committed/actual UAT cost: USD {state.get('spend_usd', 0.0):.4f}\n"
            "OpenAI x1, Gemini x1, Vidu x1, ElevenLabs x3 completed within contract.\n"
            "Downstream Assembly -> Subtitle/SRT -> QC -> Owner-authorized UAT approval -> "
            "Render -> 16:9/9:16/1:1 -> .orbis validate/CLONE = PASS.\n"
            "No secret values, raw provider bodies, or provider headers are included."
        )
    else:
        body = (
            f"LIVE_EXECUTION_STOPPED: {EXECUTION_ID}\n\n"
            f"Phase: `{state.get('phase')}`\n"
            f"Chargeable calls conservatively consumed: {state.get('paid_call_count')}/{MAX_PAID_CALLS}\n"
            f"Last known committed/actual UAT cost: USD {state.get('spend_usd', 0.0):.4f}\n"
            f"Reason: `{state.get('error', 'unknown')}`\n\n"
            "Sanitized durable failure metadata is retained in summary.json when available.\n"
            "STOP enforced. No further paid provider call is authorized after this marker."
        )
    (EVIDENCE_DIR / "issue-comment.md").write_text(body, encoding="utf-8")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _consume_paid_call(label: str) -> None:
    new_count = next_paid_call(tuple(state["paid_calls"]), label)
    state["paid_calls"].append(label)
    state["paid_call_count"] = new_count
    _write_evidence()


def _budget_guard(db, project_id: uuid.UUID) -> dict[str, Any]:
    summary = CostLedgerService.get_project_summary(db, project_id)
    committed = float(summary.get("total_committed_cost") or 0.0)
    unknown_count = int(summary.get("unknown_cost_count") or 0)
    enforce_budget(committed_usd=committed, unknown_cost_count=unknown_count)
    state["spend_usd"] = committed
    _write_evidence()
    return summary


def _capture_durable_failure_evidence() -> None:
    """Copy only allowlisted durable DB failure metadata into the workflow artifact.

    The workflow artifact survives the ephemeral PostgreSQL/MinIO teardown. This
    function deliberately excludes job payloads, provider raw bodies, headers,
    prompts, credentials, and image/audio bytes.
    """
    captured: dict[str, Any] = {}
    try:
        with SessionLocal() as db:
            shot_id = state.get("shot_id")
            if shot_id:
                try:
                    parsed_shot = uuid.UUID(str(shot_id))
                except (ValueError, TypeError):
                    parsed_shot = None
                if parsed_shot is not None:
                    job = (
                        db.query(GenerationJob)
                        .filter(GenerationJob.shot_id == parsed_shot)
                        .order_by(GenerationJob.updated_at.desc())
                        .first()
                    )
                    job_evidence = sanitize_generation_job(job)
                    if job_evidence:
                        captured["generation_job"] = job_evidence

            clip_id = state.get("active_audio_clip_id")
            if clip_id:
                try:
                    parsed_clip = uuid.UUID(str(clip_id))
                except (ValueError, TypeError):
                    parsed_clip = None
                if parsed_clip is not None:
                    clip = db.get(AudioClip, parsed_clip)
                    clip_evidence = sanitize_audio_clip(clip)
                    if clip_evidence:
                        captured["audio_clip"] = clip_evidence
    except Exception as capture_exc:
        captured["capture_error"] = _redact(f"{type(capture_exc).__name__}: {capture_exc}")
    state["failure_evidence"] = captured


def _probe_video_audio(storage, asset: Asset) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="wp020_live_r3_probe_") as td:
        path = os.path.join(td, "source.mp4")
        storage.download_file_object(asset.storage_bucket, asset.storage_key, path)
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index,channels",
                "-of",
                "json",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout or "{}")
        streams = data.get("streams") or []
        channels = sum(int(row.get("channels") or 0) for row in streams if isinstance(row, dict))
        return {
            "has_audio": bool(streams and channels > 0),
            "audio_stream_count": len(streams),
            "audio_channels": channels,
        }


def _create_bounded_storyboard_fixture(db, project: Project, story: Story) -> Shot:
    """Zero-billing deterministic bridge after the one authorized OpenAI call."""
    scene = Scene(
        id=uuid.uuid4(),
        story_id=story.id,
        scene_number=1,
        heading="WP020 LIVE R3 — Product proof",
        purpose="Bounded provider UAT",
        setting="Clean modern studio with soft neutral lighting",
        duration_seconds=4.0,
        narration="ทดสอบการสร้างวิดีโอจริงแบบจำกัดค่าใช้จ่าย",
        dialogue=[],
        scene_config={"uat_fixture": EXECUTION_ID},
    )
    db.add(scene)
    db.flush()
    before = project.status
    project.status = "STORYBOARD_GENERATED"
    ProductionOrchestrator.record_audit(
        db,
        project.id,
        before,
        "STORYBOARD_GENERATED",
        "UAT_DETERMINISTIC_STORYBOARD_BRIDGE",
        actor="WP020-LIVE-R3",
        detail="Zero-billing bridge required by the one-OpenAI-call R3 contract.",
    )
    db.commit()
    ProductionOrchestrator.approve_stage(
        db, project.id, stage="STORYBOARD_GENERATED", actor="OWNER_AUTHORIZED_LIVE_UAT"
    )

    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        status="PENDING",
        visual_prompt=(
            "Photorealistic cinematic medium-wide shot of a sleek modern creative studio, "
            "soft neutral light, subtle camera-ready product presentation, no text, no logos"
        ),
        image_prompt=(
            "Photorealistic cinematic modern creative studio, soft neutral lighting, "
            "clean composition, no text, no logos"
        ),
        video_prompt=(
            "A cinematic modern creative studio with soft neutral lighting, gentle slow camera push-in, "
            "natural realistic motion, no text, no logos"
        ),
        camera="Slow push-in",
        subject="Modern creative studio",
        action="กล้องเคลื่อนเข้าอย่างนุ่มนวลเพื่อแสดงบรรยากาศสตูดิโอ",
        duration_seconds=4.0,
        source_metadata={"uat_fixture": EXECUTION_ID},
    )
    db.add(shot)
    db.flush()
    before = project.status
    project.status = "SHOT_PLAN_GENERATED"
    ProductionOrchestrator.record_audit(
        db,
        project.id,
        before,
        "SHOT_PLAN_GENERATED",
        "UAT_DETERMINISTIC_SHOT_PLAN_BRIDGE",
        actor="WP020-LIVE-R3",
        detail="Single 4-second shot; zero-billing bridge for bounded R3 UAT.",
    )
    db.commit()
    ProductionOrchestrator.approve_stage(
        db, project.id, stage="SHOT_PLAN_GENERATED", actor="OWNER_AUTHORIZED_LIVE_UAT"
    )
    db.refresh(shot)
    return shot


def run() -> None:
    _require(EXECUTION_ID == R3_EXECUTION_ID, "Unexpected R3 LIVE execution id")
    validate_runtime_binding(
        github_sha=os.environ.get("GITHUB_SHA", ""),
        authorized_main_sha=AUTHORIZED_MAIN_SHA,
        fence_confirmed=os.environ.get("EXECUTION_FENCE_CONFIRMED") == "true",
    )
    _require(settings.OPENAI_MAX_RETRIES == 0, "OPENAI_MAX_RETRIES must be zero")
    _require(settings.OPENAI_CREATIVE_MODEL == "gpt-4o", "OpenAI model drift")
    _require(settings.DEFAULT_CREATIVE_PROFILE == "FAST", "Creative profile drift")
    _require(settings.GEMINI_IMAGE_MODEL == "gemini-3.1-flash-image", "Gemini model drift")
    _require(settings.GEMINI_IMAGE_SIZE == "1K", "Gemini size drift")
    _require(settings.VIDU_DEFAULT_MODEL == "viduq2", "Vidu model drift")
    _require(ImageProviderFactory.get_default_provider_name() == "gemini_image", "Image provider drift")
    _require(ProviderFactory.get_default_provider_name() == "vidu", "Video provider drift")
    _require(AudioProviderFactory.get_default_provider_name() == "elevenlabs_audio", "Audio provider drift")
    _require(len(PAID_CALL_SEQUENCE) == MAX_PAID_CALLS == 6, "R3 paid-call contract drift")

    storage = get_storage_provider()
    storage.ensure_bucket_exists(settings.OBJECT_STORAGE_BUCKET)

    with SessionLocal() as db:
        state["phase"] = "LIVE-01-OPENAI-STORY"
        project = Project(
            id=uuid.uuid4(),
            title="WP020 LIVE R3 Bounded UAT",
            description=(
                "สร้างวิดีโอสั้นเชิงองค์กรเกี่ยวกับทีมครีเอทีฟที่ใช้ระบบ AI ช่วยจัดกระบวนการผลิต "
                "โทนทันสมัย น่าเชื่อถือ เรียบง่าย ไม่มีแบรนด์หรือข้อความบนภาพ"
            ),
            video_mode="STORY",
            status="DRAFT",
            automation_mode="MANUAL",
            target_duration_seconds=20.0,
            budget_limit=HARD_CAP_USD,
            budget_currency="USD",
            budget_threshold_percentage=80,
        )
        db.add(project)
        db.commit()
        state["project_id"] = str(project.id)
        _require(BudgetService.get_project_committed_cost(db, project.id) == 0.0, "UAT project did not start at zero cost")

        _consume_paid_call(PAID_CALL_SEQUENCE[0])
        ProductionOrchestrator.execute_action(
            db,
            project.id,
            "GENERATE_STORY",
            parameters={
                "target_duration_seconds": 20.0,
                "tone": "corporate cinematic",
                "language": "th",
                "custom_instructions": "Keep the complete concept under 30 seconds and suitable for a one-shot bounded UAT.",
            },
            actor="OWNER_AUTHORIZED_LIVE_UAT",
        )
        story = db.query(Story).filter(Story.project_id == project.id).one()
        audit = (
            db.query(GenerationAuditLog)
            .filter(
                GenerationAuditLog.project_id == project.id,
                GenerationAuditLog.request_type == "STORY_GENERATE",
            )
            .order_by(GenerationAuditLog.created_at.desc())
            .first()
        )
        _require(audit is not None, "OpenAI story audit missing")
        require_provider_success("openai", audit.status)
        _require(audit.provider == "openai" and audit.model == "gpt-4o", "OpenAI provider/model audit drift")
        state["provider_evidence"]["openai"] = {
            "provider": audit.provider,
            "model": audit.model,
            "prompt_tokens": audit.prompt_tokens,
            "completion_tokens": audit.completion_tokens,
            "story_id": str(story.id),
        }
        _budget_guard(db, project.id)
        ProductionOrchestrator.approve_stage(
            db, project.id, stage="STORY_GENERATED", actor="OWNER_AUTHORIZED_LIVE_UAT"
        )

        state["phase"] = "ZERO-BILLING-STORYBOARD-BRIDGE"
        shot = _create_bounded_storyboard_fixture(db, project, story)
        state["shot_id"] = str(shot.id)
        _require(project.status == "SHOT_PLAN_APPROVED", "Shot-plan approval bridge failed")

        state["phase"] = "LIVE-02-GEMINI-IMAGE"
        _consume_paid_call(PAID_CALL_SEQUENCE[1])
        asset, image_job = KeyframeGenerationService.generate_shot_keyframe(
            db=db,
            project_id=project.id,
            shot_id=shot.id,
            provider_name="gemini_image",
            cost_authorized=True,
            actor="OWNER_AUTHORIZED_LIVE_UAT",
        )
        require_provider_success(
            "gemini_image",
            image_job.status,
            submission_uncertain=image_job.status == "RECONCILIATION_REQUIRED",
        )
        _require(asset is not None, "Gemini keyframe completed without Asset")
        _require(
            asset.asset_type == "KEYFRAME" and storage.object_exists(asset.storage_bucket, asset.storage_key),
            "Gemini keyframe not durable",
        )
        _require(shot.keyframe_asset_id == asset.id, "Gemini keyframe lineage missing")
        KeyframeGenerationService._check_and_advance_stage_if_all_keyframes_ready(
            db, project.id, actor="WP020-LIVE-R3"
        )
        db.refresh(project)
        _require(project.status == "IMAGES_GENERATED", "Keyframe stage did not advance")
        state["provider_evidence"]["gemini"] = {
            "job_id": str(image_job.id),
            "provider_job_id": image_job.provider_job_id,
            "asset_id": str(asset.id),
            "sha256": asset.checksum_sha256,
        }
        _budget_guard(db, project.id)
        ProductionOrchestrator.approve_stage(
            db, project.id, stage="IMAGES_GENERATED", actor="OWNER_AUTHORIZED_LIVE_UAT"
        )

        state["phase"] = "LIVE-03-VIDU-VIDEO"
        video_job = JobDispatchService.create_and_dispatch_job(
            db=db,
            shot_id=shot.id,
            provider_name="vidu",
            idempotency_key=f"{EXECUTION_ID}:VIDU:SHOT1",
            custom_params={"resolution": "720p"},
            max_retries=1,
            reference_images=None,
            lock_shot=True,
        )
        before = project.status
        project.status = "VIDEO_IN_PROGRESS"
        ProductionOrchestrator.record_audit(
            db,
            project.id,
            before,
            "VIDEO_IN_PROGRESS",
            "LIVE_VIDU_SINGLE_SHOT_DISPATCH",
            actor="OWNER_AUTHORIZED_LIVE_UAT",
            detail=f"Single 4-second text-to-video job {video_job.id}; max_retries=1.",
        )
        db.commit()
        claimed = JobDispatchService.claim_next_job(
            db, worker_id=f"{EXECUTION_ID}-vidu", job_id=video_job.id
        )
        _require(claimed is not None, "Vidu job claim failed")
        _consume_paid_call(PAID_CALL_SEQUENCE[2])
        video_job = asyncio.run(
            JobDispatchService.process_job(db, video_job.id, claim_token=claimed.claim_token)
        )
        require_provider_success(
            "vidu",
            video_job.status,
            submission_uncertain=video_job.status == "RECONCILIATION_REQUIRED",
        ) if video_job.status not in ("QUEUED", "PROCESSING") else None

        poll_deadline = time.monotonic() + 600
        while video_job.status in ("QUEUED", "PROCESSING"):
            _require(time.monotonic() < poll_deadline, "Vidu polling deadline reached")
            time.sleep(10)
            video_job = asyncio.run(JobDispatchService.poll_job_status(db, video_job.id, max_polls=60))
            if video_job.status not in ("QUEUED", "PROCESSING"):
                require_provider_success(
                    "vidu",
                    video_job.status,
                    submission_uncertain=video_job.status == "RECONCILIATION_REQUIRED",
                )
        require_provider_success(
            "vidu",
            video_job.status,
            submission_uncertain=video_job.status == "RECONCILIATION_REQUIRED",
        )
        _require(video_job.output_asset_id is not None, "Vidu completed without durable output_asset_id")
        video_asset = db.get(Asset, video_job.output_asset_id)
        db.refresh(shot)
        _require(video_asset is not None and video_asset.asset_type == "VIDEO", "Vidu VIDEO Asset missing")
        _require(storage.object_exists(video_asset.storage_bucket, video_asset.storage_key), "Vidu VIDEO object missing")
        _require(shot.source_asset_id == video_asset.id, "GenerationJob -> Asset -> Shot lineage missing")
        shot.source_metadata = {**(shot.source_metadata or {}), **_probe_video_audio(storage, video_asset)}
        db.commit()
        state["provider_evidence"]["vidu"] = {
            "job_id": str(video_job.id),
            "provider_job_id": video_job.provider_job_id,
            "asset_id": str(video_asset.id),
            "sha256": video_asset.checksum_sha256,
            "duration_seconds": 4,
            "resolution": "720p",
            "route": "text2video",
        }
        _budget_guard(db, project.id)
        ProductionOrchestrator.execute_action(
            db, project.id, "TRANSITION_TO_FINAL_REVIEW", actor="OWNER_AUTHORIZED_LIVE_UAT"
        )

        state["phase"] = "LIVE-04-ELEVENLABS-AUDIO"
        AudioProductionService.generate_audio_plan(db, project.id)
        AudioProductionService.approve_audio_plan(db, project.id)
        clips = db.query(AudioClip).filter(AudioClip.project_id == project.id).all()
        speech = next(
            (clip for clip in clips if clip.audio_type in ("VO", "DIALOGUE") and clip.status == "PENDING"),
            None,
        )
        bgm = next((clip for clip in clips if clip.audio_type == "BGM" and clip.status == "PENDING"), None)
        ambience = next(
            (clip for clip in clips if clip.audio_type == "AMBIENCE" and clip.status == "PENDING"),
            None,
        )
        _require(speech is not None and bgm is not None and ambience is not None, "Required bounded audio clips not present")

        bounded = [
            (
                speech,
                PAID_CALL_SEQUENCE[3],
                "ระบบ Orbis กำลังทดสอบการสร้างเสียงภาษาไทยแบบจำกัดค่าใช้จ่าย",
                min(float(speech.duration_seconds or 4.0), 4.0),
            ),
            (bgm, PAID_CALL_SEQUENCE[4], "Modern calm corporate technology background music", 10.0),
            (ambience, PAID_CALL_SEQUENCE[5], "Soft modern studio room ambience", 3.0),
        ]
        eleven_evidence = []
        for clip, label, prompt, duration in bounded:
            state["active_audio_clip_id"] = str(clip.id)
            clip.prompt = prompt
            clip.duration_seconds = duration
            if clip.audio_type in ("VO", "DIALOGUE"):
                clip.language = "th"
                _require(len(prompt) <= 150, "Thai TTS prompt exceeds contract")
            clip.version += 1
            clip.updated_at = datetime.now(timezone.utc)
            AudioProductionService.record_clip_history(
                db,
                clip,
                actor="WP020-LIVE-R3",
                action="UAT_BOUND",
                change_reason="Bounded to R3 LIVE call/duration contract",
            )
            db.commit()
            _consume_paid_call(label)
            ready = AudioProductionService.generate_clip_audio(
                db=db,
                project_id=project.id,
                clip_id=clip.id,
                provider_name="elevenlabs_audio",
                cost_authorized=True,
                actor="OWNER_AUTHORIZED_LIVE_UAT",
            )
            require_provider_success("elevenlabs_audio", ready.status)
            _require(ready.asset_id is not None, f"ElevenLabs {clip.audio_type} completed without asset")
            audio_asset = db.get(Asset, ready.asset_id)
            _require(
                audio_asset is not None
                and storage.object_exists(audio_asset.storage_bucket, audio_asset.storage_key),
                "ElevenLabs audio object missing",
            )
            eleven_evidence.append(
                {
                    "clip_id": str(ready.id),
                    "audio_type": ready.audio_type,
                    "asset_id": str(audio_asset.id),
                    "provider_job_id": (ready.provenance or {}).get("provider_job_id"),
                    "sha256": audio_asset.checksum_sha256,
                    "duration_seconds": ready.duration_seconds,
                }
            )
            _budget_guard(db, project.id)
        state["active_audio_clip_id"] = None
        state["provider_evidence"]["elevenlabs"] = eleven_evidence
        _require(state["paid_call_count"] == MAX_PAID_CALLS, "R3 paid-call count did not equal exact contract count")
        _require(tuple(state["paid_calls"]) == PAID_CALL_SEQUENCE, "R3 paid-call sequence drifted")

        state["phase"] = "LIVE-05-DOWNSTREAM"
        ProductionOrchestrator.execute_action(
            db, project.id, "AUTO_MIX_AUDIO", actor="OWNER_AUTHORIZED_LIVE_UAT"
        )
        ProductionOrchestrator.approve_stage(
            db, project.id, stage="AUDIO_MIX_READY", actor="OWNER_AUTHORIZED_LIVE_UAT"
        )
        ProductionOrchestrator.execute_action(
            db, project.id, "PROCEED_TO_ASSEMBLY", actor="OWNER_AUTHORIZED_LIVE_UAT"
        )

        timeline = AssemblyService.auto_assemble_timeline(db, str(project.id))
        _require(len(timeline.shot_placements) == 1, "Assembly did not contain exactly one active shot")
        _require(
            timeline.shot_placements[0].visual_asset_id == video_asset.id,
            "Assembly does not use durable Vidu VIDEO asset",
        )

        track = SubtitleService.generate(db, project.id, timeline_id=str(timeline.id), language="th")
        _require(bool(track.get("segments")), "Subtitle generation produced no segments")
        reviewed = SubtitleService.review(
            db, project.id, enabled=True, render_mode="BURN_IN", timeline_id=str(timeline.id)
        )
        _require(reviewed.get("is_reviewed") is True, "Subtitle review gate failed")
        srt, srt_meta = SubtitleService.export_srt(db, project.id, str(timeline.id))
        _require(
            bool(srt.strip())
            and srt_meta.get("sha256") == hashlib.sha256(srt.encode("utf-8")).hexdigest(),
            "SRT evidence invalid",
        )
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "subtitles.srt").write_text(srt, encoding="utf-8")

        qc_run = QCService.run_qc(db, project.id)
        _require(qc_run.blocker_count == 0, f"QC blocker_count={qc_run.blocker_count}")
        for finding in list(qc_run.findings):
            if finding.severity == "WARNING":
                QCService.record_warning_decision(
                    db,
                    project.id,
                    finding.id,
                    decision="ACCEPTED_WITH_REASON",
                    reason="Owner-authorized bounded WP020 LIVE R3 UAT evidence only",
                    actor="OWNER_AUTHORIZED_LIVE_UAT",
                )
        db.refresh(qc_run)
        approval = ProductionOrchestrator.approve_final_production(
            db,
            project.id,
            timeline_id=timeline.id,
            qc_run_id=qc_run.id,
            notes="Owner-authorized bounded WP020 LIVE R3 UAT",
            actor="OWNER_AUTHORIZED_LIVE_UAT",
        )
        _require(approval.status == "APPROVED", "Human approval record not persisted")

        worker = CloudRenderWorker(worker_id=f"{EXECUTION_ID}-render", storage_provider=storage)
        worker.validate_runtime()
        master = RenderJobService.submit_render_job(db, project.id)
        _require(worker.process_one_job(db) is True, "Master render worker did not process job")
        db.refresh(master)
        _require(
            master.status == RenderJobStatus.COMPLETED.value and master.output_asset_id is not None,
            "Master render failed",
        )

        batch = RenderJobService.submit_export_batch(
            db,
            project.id,
            preset_ids=["YT_STANDARD_1080P", "TIKTOK_REELS_9X16", "INSTAGRAM_SQUARE"],
        )
        for _ in range(3):
            _require(worker.process_one_job(db) is True, "Multi-output render worker did not process expected job")
        variants = db.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
        _require(
            len(variants) == 3 and all(job.status == RenderJobStatus.COMPLETED.value for job in variants),
            "Multi-output variants incomplete",
        )

        exporter = ProjectExportService(storage_provider=storage)
        archive_path, manifest = exporter.export_project(db=db, project_id=project.id)
        _require(
            manifest["archive_options"]["package_type"] == "FULL_SELF_CONTAINED",
            "Archive not FULL_SELF_CONTAINED",
        )
        archive_dest = EVIDENCE_DIR / f"{EXECUTION_ID}.orbis"
        shutil.copyfile(archive_path, archive_dest)
        importer = ProjectImportService(storage_provider=storage)
        validation = importer.validate_project_archive(archive_path, db)
        _require(validation.get("valid") is True, "Exported .orbis validation failed")
        clone = importer.execute_import(
            db=db,
            archive_path=archive_path,
            import_mode="CLONE",
            override_title="WP020 LIVE R3 Verified Clone",
        )
        _require(clone.id != project.id and clone.source_project_id == project.id, "CLONE lineage failed")
        _require(BudgetService.get_project_committed_cost(db, clone.id) == 0.0, "CLONE inherited live budget spend")
        os.remove(archive_path)

        final_cost = _budget_guard(db, project.id)
        state["downstream"] = {
            "timeline_id": str(timeline.id),
            "subtitle_sha256": srt_meta.get("sha256"),
            "qc_run_id": str(qc_run.id),
            "approval_id": str(approval.id),
            "master_render_job_id": str(master.id),
            "variant_render_job_ids": [str(job.id) for job in variants],
            "archive_sha256": hashlib.sha256(archive_dest.read_bytes()).hexdigest(),
            "clone_project_id": str(clone.id),
            "ledger_by_provider": final_cost.get("by_provider"),
        }
        state["phase"] = "COMPLETE"
        state["status"] = "PASS"
        _write_evidence()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        state["status"] = "STOPPED"
        state["error"] = _redact(str(exc))
        state["error_type"] = type(exc).__name__
        _capture_durable_failure_evidence()
        _write_evidence()
        raise
