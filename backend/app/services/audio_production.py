"""Audio Production and Mixing Service for Core V1.

Manages audio planning, clip classification, deterministic mock and provider generation,
atomic pre-provider claims, UsageLedger budget reservation, fail-closed reconciliation,
and speech-over-music auto-ducking mixing metadata.
"""
import uuid
import hashlib
import asyncio
import concurrent.futures
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.services.storage.factory import get_storage_provider
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.audio_clip import (
    AudioClip,
    AudioSourceType,
    AudioType,
    AudioGenerationMode,
    AudioScope,
    DuckingRole,
)
from app.models.audio_plan import AudioPlan
from app.models.audio_history import AudioPlanVersion, AudioClipHistory
from app.schemas.audio_spec import AudioSpec
from app.providers.audio.factory import AudioProviderFactory
from app.providers.audio.base import (
    AudioGenerationParams,
    AudioJobResult,
    IAudioProviderAdapter,
)
from app.services.pricing import CostStatus, ProviderPricingService
from app.services.cost_ledger import CostLedgerService
from app.services.budget import BudgetService


ACTIVE_AUDIO_STATUSES = {"SUBMITTING", "GENERATING", "POLLING", "RECONCILIATION_REQUIRED"}


class AudioProductionService:
    """Core V1 Audio Production Service."""

    @staticmethod
    def auto_classify_clip(
        audio_type: AudioType,
        source_type: Optional[AudioSourceType] = None,
        generation_mode: Optional[AudioGenerationMode] = None,
        scope: Optional[AudioScope] = None,
        video_supports_native_audio: bool = False,
    ) -> Dict[str, Any]:
        """Auto-classify audio dimensions while strictly maintaining orthogonality.
        Human overrides are always preserved.
        """
        # 1. Source Type Default
        eff_source = source_type
        if eff_source is None:
            if audio_type == AudioType.ORIGINAL_AUDIO:
                eff_source = AudioSourceType.EMBEDDED_VIDEO_AUDIO
            else:
                eff_source = AudioSourceType.GENERATED_AUDIO

        # 2. Generation Mode Default
        eff_mode = generation_mode
        if eff_mode is None:
            if audio_type == AudioType.ORIGINAL_AUDIO:
                eff_mode = AudioGenerationMode.EMBEDDED_EXISTING
            elif audio_type == AudioType.DIALOGUE and video_supports_native_audio:
                eff_mode = AudioGenerationMode.WITH_VIDEO
            else:
                eff_mode = AudioGenerationMode.SEPARATE_AUDIO

        # 3. Scope Default
        eff_scope = scope
        if eff_scope is None:
            if audio_type == AudioType.BGM:
                eff_scope = AudioScope.PROJECT
            elif audio_type == AudioType.AMBIENCE:
                eff_scope = AudioScope.SCENE
            elif audio_type == AudioType.ORIGINAL_AUDIO:
                eff_scope = AudioScope.VIDEO_CLIP
            else:
                eff_scope = AudioScope.SHOT

        # 4. Ducking Role & DB reduction
        if audio_type in (AudioType.VO, AudioType.DIALOGUE):
            ducking_role = DuckingRole.FOREGROUND
            ducking_amount_db = 0.0
        elif audio_type == AudioType.BGM:
            ducking_role = DuckingRole.BACKGROUND
            ducking_amount_db = -12.0
        elif audio_type == AudioType.AMBIENCE:
            ducking_role = DuckingRole.BACKGROUND
            ducking_amount_db = -6.0
        elif audio_type == AudioType.ORIGINAL_AUDIO:
            ducking_role = DuckingRole.EMBEDDED
            ducking_amount_db = 0.0
        else:  # SFX
            ducking_role = DuckingRole.EVENT
            ducking_amount_db = 0.0

        return {
            "source_type": eff_source.value if isinstance(eff_source, AudioSourceType) else str(eff_source),
            "generation_mode": eff_mode.value if isinstance(eff_mode, AudioGenerationMode) else str(eff_mode),
            "scope": eff_scope.value if isinstance(eff_scope, AudioScope) else str(eff_scope),
            "ducking_role": ducking_role.value if isinstance(ducking_role, DuckingRole) else str(ducking_role),
            "ducking_amount_db": ducking_amount_db,
        }

    @classmethod
    def record_plan_version(
        cls,
        db: Session,
        plan: AudioPlan,
        actor: str = "SYSTEM",
        action: str = "CREATE",
        change_reason: Optional[str] = None,
    ) -> AudioPlanVersion:
        v_num = getattr(plan, "version", None) or 1
        version = AudioPlanVersion(
            id=uuid.uuid4(),
            audio_plan_id=plan.id,
            project_id=plan.project_id,
            version_number=v_num,
            status=plan.status,
            plan_data=plan.plan_data,
            actor=actor,
            action=action,
            change_reason=change_reason,
            created_at=datetime.now(timezone.utc),
        )
        db.add(version)
        db.flush()
        return version

    @classmethod
    def record_clip_history(
        cls,
        db: Session,
        clip: AudioClip,
        actor: str = "SYSTEM",
        action: str = "CREATE",
        change_reason: Optional[str] = None,
    ) -> AudioClipHistory:
        v_num = getattr(clip, "version", None) or 1
        hist = AudioClipHistory(
            id=uuid.uuid4(),
            clip_id=clip.id,
            project_id=clip.project_id,
            version_number=v_num,
            audio_type=clip.audio_type,
            source_type=clip.source_type,
            generation_mode=clip.generation_mode,
            scope=clip.scope,
            name=clip.name,
            prompt=clip.prompt,
            start_time=clip.start_time,
            duration_seconds=clip.duration_seconds,
            volume=clip.volume,
            mute=clip.mute,
            fade_in=clip.fade_in,
            fade_out=clip.fade_out,
            ducking_role=clip.ducking_role,
            ducking_amount_db=clip.ducking_amount_db,
            language=clip.language,
            speaker=clip.speaker,
            is_locked=clip.is_locked,
            status=clip.status,
            asset_id=clip.asset_id,
            provenance=clip.provenance,
            actor=actor,
            action=action,
            change_reason=change_reason,
            created_at=datetime.now(timezone.utc),
        )
        db.add(hist)
        db.flush()
        return hist

    @classmethod
    def lock_clip(
        cls,
        db: Session,
        project_id: uuid.UUID,
        clip_id: uuid.UUID,
        actor: str = "USER",
        reason: Optional[str] = None,
    ) -> AudioClip:
        clip = db.query(AudioClip).filter(AudioClip.id == clip_id, AudioClip.project_id == project_id).first()
        if not clip:
            raise HTTPException(status_code=404, detail=f"AudioClip '{clip_id}' not found in project '{project_id}'.")
        if not clip.is_locked:
            clip.is_locked = True
            clip.version += 1
            clip.updated_at = datetime.now(timezone.utc)
            cls.record_clip_history(db, clip, actor=actor, action="LOCK", change_reason=reason or "AudioClip locked")
            db.commit()
            db.refresh(clip)
        return clip

    @classmethod
    def unlock_clip(
        cls,
        db: Session,
        project_id: uuid.UUID,
        clip_id: uuid.UUID,
        actor: str = "USER",
        reason: Optional[str] = None,
    ) -> AudioClip:
        clip = db.query(AudioClip).filter(AudioClip.id == clip_id, AudioClip.project_id == project_id).first()
        if not clip:
            raise HTTPException(status_code=404, detail=f"AudioClip '{clip_id}' not found in project '{project_id}'.")
        if clip.is_locked:
            clip.is_locked = False
            clip.version += 1
            clip.updated_at = datetime.now(timezone.utc)
            cls.record_clip_history(db, clip, actor=actor, action="UNLOCK", change_reason=reason or "AudioClip explicitly unlocked")
            db.commit()
            db.refresh(clip)
        return clip

    @classmethod
    def restore_plan_version(
        cls,
        db: Session,
        project_id: uuid.UUID,
        version_number: int,
        actor: str = "USER",
    ) -> AudioPlan:
        plan = db.query(AudioPlan).filter(AudioPlan.project_id == project_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail=f"No audio plan found for project '{project_id}'.")
        version_record = (
            db.query(AudioPlanVersion)
            .filter(AudioPlanVersion.project_id == project_id, AudioPlanVersion.version_number == version_number)
            .first()
        )
        if not version_record:
            raise HTTPException(status_code=404, detail=f"Plan version '{version_number}' not found.")
        now = datetime.now(timezone.utc)
        plan.version += 1
        plan.status = version_record.status
        plan.plan_data = version_record.plan_data
        plan.updated_at = now
        cls.record_plan_version(
            db,
            plan,
            actor=actor,
            action="RESTORE_PLAN",
            change_reason=f"Restored from version {version_number}",
        )
        db.commit()
        db.refresh(plan)
        return plan

    @classmethod
    def list_audio_clips(
        cls,
        db: Session,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        audio_type: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> Tuple[List[AudioClip], int]:
        base_query = db.query(AudioClip).filter(AudioClip.project_id == project_id)
        if audio_type:
            base_query = base_query.filter(AudioClip.audio_type == audio_type)
        if scope:
            base_query = base_query.filter(AudioClip.scope == scope)
        total = base_query.count()
        items = (
            base_query
            .order_by(AudioClip.start_time.asc(), AudioClip.created_at.asc(), AudioClip.id.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    @classmethod
    def get_plan_history(
        cls,
        db: Session,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AudioPlanVersion], int]:
        base_query = db.query(AudioPlanVersion).filter(AudioPlanVersion.project_id == project_id)
        total = base_query.count()
        items = (
            base_query
            .order_by(AudioPlanVersion.version_number.desc(), AudioPlanVersion.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    @classmethod
    def get_clip_history(
        cls,
        db: Session,
        project_id: uuid.UUID,
        clip_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AudioClipHistory], int]:
        base_query = db.query(AudioClipHistory).filter(
            AudioClipHistory.project_id == project_id,
            AudioClipHistory.clip_id == clip_id,
        )
        total = base_query.count()
        items = (
            base_query
            .order_by(AudioClipHistory.version_number.desc(), AudioClipHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    @classmethod
    def generate_audio_plan(
        cls,
        db: Session,
        project_id: uuid.UUID,
        video_provider_name: Optional[str] = None,
    ) -> AudioPlan:
        """Analyze project narrative, scenes, shots, and video assets to generate a structured AudioPlan."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        # Query existing scenes and shots ordered
        scenes = (
            db.query(Scene)
            .filter(Scene.project_id == project_id)
            .order_by(Scene.scene_number.asc())
            .all()
        )
        scene_ids = [s.id for s in scenes]

        shots: List[Shot] = []
        if scene_ids:
            shots = (
                db.query(Shot)
                .filter(Shot.scene_id.in_(scene_ids))
                .order_by(Shot.shot_number.asc())
                .all()
            )

        # 1. CANONICAL PROVIDER-CAPABILITY ROUTING
        # Resolve selected/current VideoProvider capability truth
        eff_video_provider = video_provider_name
        if not eff_video_provider and shots:
            shot_ids = [sh.id for sh in shots]
            latest_video_job = (
                db.query(GenerationJob)
                .filter(GenerationJob.shot_id.in_(shot_ids))
                .order_by(GenerationJob.created_at.desc())
                .first()
            )
            if latest_video_job and latest_video_job.provider_name:
                eff_video_provider = latest_video_job.provider_name

        from app.providers.factory import ProviderFactory
        video_supports_native_audio = False
        try:
            video_adapter = ProviderFactory.get_provider(eff_video_provider)
            video_supports_native_audio = bool(
                getattr(video_adapter, "supports_native_audio", False)
                or getattr(video_adapter, "supports_dialogue", False)
            )
        except Exception:
            video_supports_native_audio = False

        # Get or create AudioPlan
        plan = db.query(AudioPlan).filter(AudioPlan.project_id == project_id).first()
        now = datetime.now(timezone.utc)
        if not plan:
            plan = AudioPlan(
                id=uuid.uuid4(),
                project_id=project_id,
                status="DRAFT",
                version=1,
                created_at=now,
                updated_at=now,
            )
            db.add(plan)
            db.flush()
        else:
            plan.version += 1
            plan.status = "DRAFT"
            plan.updated_at = now

        # Map existing clips by (audio_type, shot_id, scene_id, scope) to avoid duplicate recreation
        existing_clips = db.query(AudioClip).filter(AudioClip.project_id == project_id).all()
        existing_clip_map = {}
        for c in existing_clips:
            key = (c.audio_type, c.shot_id, c.scene_id, c.scope)
            existing_clip_map[key] = c

        created_clips: List[AudioClip] = []

        # 1. Project BGM Track
        bgm_key = (AudioType.BGM.value, None, None, AudioScope.PROJECT.value)
        if bgm_key not in existing_clip_map:
            bgm_cls = cls.auto_classify_clip(AudioType.BGM)
            bgm_clip = AudioClip(
                id=uuid.uuid4(),
                project_id=project_id,
                name=f"{project.title or 'Project'} - Main Theme",
                prompt=f"Cinematic background music score for {project.title or 'film'}",
                audio_type=AudioType.BGM.value,
                source_type=bgm_cls["source_type"],
                generation_mode=bgm_cls["generation_mode"],
                scope=bgm_cls["scope"],
                ducking_role=bgm_cls["ducking_role"],
                ducking_amount_db=bgm_cls["ducking_amount_db"],
                start_time=0.0,
                duration_seconds=30.0,
                volume=0.8,
                status="PENDING",
                created_at=now,
                updated_at=now,
            )
            db.add(bgm_clip)
            created_clips.append(bgm_clip)

        # 2. Scene Ambience Tracks
        scene_time_offset = 0.0
        for sc in scenes:
            amb_key = (AudioType.AMBIENCE.value, None, sc.id, AudioScope.SCENE.value)
            if amb_key not in existing_clip_map:
                amb_cls = cls.auto_classify_clip(AudioType.AMBIENCE)
                amb_clip = AudioClip(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    scene_id=sc.id,
                    name=f"Scene {sc.scene_number} - {sc.heading or 'Ambience'}",
                    prompt=f"Environmental background room tone / ambience for {sc.setting or sc.heading or 'scene'}",
                    audio_type=AudioType.AMBIENCE.value,
                    source_type=amb_cls["source_type"],
                    generation_mode=amb_cls["generation_mode"],
                    scope=amb_cls["scope"],
                    ducking_role=amb_cls["ducking_role"],
                    ducking_amount_db=amb_cls["ducking_amount_db"],
                    start_time=scene_time_offset,
                    duration_seconds=15.0,
                    volume=0.6,
                    status="PENDING",
                    created_at=now,
                    updated_at=now,
                )
                db.add(amb_clip)
                created_clips.append(amb_clip)
            scene_time_offset += 15.0

        # 3. Shot-level VO, Dialogue, and Embedded Audio Tracks
        shot_time_offset = 0.0
        for sh in shots:
            shot_duration = float(sh.duration_seconds or 4.0)
            
            # Check for original embedded video audio
            # Finding 4: Embedded Audio Truth. Verify referenced asset is VIDEO and verify audio presence metadata.
            if sh.source_asset_id:
                source_asset = db.get(Asset, sh.source_asset_id)
                is_video = bool(
                    source_asset and (
                        source_asset.asset_type.upper() == "VIDEO"
                        or (source_asset.content_type and source_asset.content_type.startswith("video/"))
                    )
                )
                if is_video:
                    meta = sh.source_metadata or {}
                    has_audio_explicit = meta.get("has_audio")
                    audio_channels = meta.get("audio_channels")
                    audio_stream_count = meta.get("audio_stream_count")

                    if has_audio_explicit is False or audio_channels == 0 or audio_stream_count == 0:
                        has_audio = False
                    elif has_audio_explicit is True or (isinstance(audio_channels, int) and audio_channels > 0) or (isinstance(audio_stream_count, int) and audio_stream_count > 0):
                        has_audio = True
                    else:
                        has_audio = None

                    # If has_audio is False: truthfully omit ORIGINAL_AUDIO clip
                    if has_audio is not False:
                        orig_key = (AudioType.ORIGINAL_AUDIO.value, sh.id, sh.scene_id, AudioScope.VIDEO_CLIP.value)
                        if orig_key not in existing_clip_map:
                            orig_cls = cls.auto_classify_clip(AudioType.ORIGINAL_AUDIO)
                            clip_status = "READY" if has_audio is True else "UNKNOWN"
                            presence_val = "VERIFIED" if has_audio is True else "UNKNOWN"
                            orig_clip = AudioClip(
                                id=uuid.uuid4(),
                                project_id=project_id,
                                scene_id=sh.scene_id,
                                shot_id=sh.id,
                                video_asset_id=sh.source_asset_id,
                                name=f"Shot {sh.shot_number} - Original Audio",
                                prompt="Original embedded audio track from video source",
                                audio_type=AudioType.ORIGINAL_AUDIO.value,
                                source_type=orig_cls["source_type"],
                                generation_mode=orig_cls["generation_mode"],
                                scope=orig_cls["scope"],
                                ducking_role=orig_cls["ducking_role"],
                                ducking_amount_db=orig_cls["ducking_amount_db"],
                                start_time=shot_time_offset,
                                duration_seconds=shot_duration,
                                volume=1.0,
                                status=clip_status,
                                provenance={
                                    "audio_presence": presence_val,
                                    "source_asset_id": str(sh.source_asset_id),
                                    "content_type": source_asset.content_type if source_asset else None,
                                },
                                created_at=now,
                                updated_at=now,
                            )
                            db.add(orig_clip)
                            created_clips.append(orig_clip)

            # Check for dialogue vs voiceover in shot attributes
            text_prompt = (
                getattr(sh, "voiceover_text", None)
                or getattr(sh, "dialogue_text", None)
                or getattr(sh, "action", None)
                or getattr(sh, "visual_prompt", None)
                or getattr(sh, "video_prompt", None)
            )
            meta = sh.source_metadata or {}
            text_prompt = (
                meta.get("dialogue_text")
                or meta.get("voiceover_text")
                or getattr(sh, "voiceover_text", None)
                or getattr(sh, "dialogue_text", None)
                or getattr(sh, "action", None)
                or getattr(sh, "visual_prompt", None)
                or getattr(sh, "video_prompt", None)
            )
            speaker = meta.get("speaker_name") or getattr(sh, "speaker_name", None) or getattr(sh, "subject", None) or "Narrator"
            is_dialogue = bool(meta.get("is_dialogue") or meta.get("dialogue_text") or getattr(sh, "dialogue_text", None))
            atype = AudioType.DIALOGUE if is_dialogue else AudioType.VO

            voice_key = (atype.value, sh.id, sh.scene_id, AudioScope.SHOT.value)
            if voice_key not in existing_clip_map and text_prompt:
                v_cls = cls.auto_classify_clip(atype, video_supports_native_audio=video_supports_native_audio)
                v_clip = AudioClip(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    scene_id=sh.scene_id,
                    shot_id=sh.id,
                    name=f"Shot {sh.shot_number} - {atype.value}",
                    prompt=text_prompt,
                    audio_type=atype.value,
                    source_type=v_cls["source_type"],
                    generation_mode=v_cls["generation_mode"],
                    scope=v_cls["scope"],
                    ducking_role=v_cls["ducking_role"],
                    ducking_amount_db=v_cls["ducking_amount_db"],
                    speaker=speaker,
                    start_time=shot_time_offset,
                    duration_seconds=shot_duration,
                    volume=1.0,
                    status="PENDING",
                    created_at=now,
                    updated_at=now,
                )
                db.add(v_clip)
                created_clips.append(v_clip)

            # Check for SFX prompt
            sfx_text = getattr(sh, "sound_effects", None)
            if sfx_text:
                sfx_key = (AudioType.SFX.value, sh.id, sh.scene_id, AudioScope.SHOT.value)
                if sfx_key not in existing_clip_map:
                    sfx_cls = cls.auto_classify_clip(AudioType.SFX)
                    sfx_clip = AudioClip(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        scene_id=sh.scene_id,
                        shot_id=sh.id,
                        name=f"Shot {sh.shot_number} - SFX",
                        prompt=sh.sound_effects,
                        audio_type=AudioType.SFX.value,
                        source_type=sfx_cls["source_type"],
                        generation_mode=sfx_cls["generation_mode"],
                        scope=sfx_cls["scope"],
                        ducking_role=sfx_cls["ducking_role"],
                        ducking_amount_db=sfx_cls["ducking_amount_db"],
                        start_time=shot_time_offset,
                        duration_seconds=min(shot_duration, 4.0),
                        volume=0.9,
                        status="PENDING",
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(sfx_clip)
                    created_clips.append(sfx_clip)

            shot_time_offset += shot_duration

        # Compute plan data summary
        total_clips = len(existing_clips) + len(created_clips)
        plan.plan_data = {
            "summary": {
                "total_scenes": len(scenes),
                "total_shots": len(shots),
                "total_audio_clips": total_clips,
                "created_new_clips": len(created_clips),
                "total_timeline_seconds": shot_time_offset,
            },
            "tracks": {
                "bgm_count": sum(1 for c in existing_clips + created_clips if c.audio_type == AudioType.BGM.value),
                "ambience_count": sum(1 for c in existing_clips + created_clips if c.audio_type == AudioType.AMBIENCE.value),
                "vo_count": sum(1 for c in existing_clips + created_clips if c.audio_type == AudioType.VO.value),
                "dialogue_count": sum(1 for c in existing_clips + created_clips if c.audio_type == AudioType.DIALOGUE.value),
                "sfx_count": sum(1 for c in existing_clips + created_clips if c.audio_type == AudioType.SFX.value),
                "original_count": sum(1 for c in existing_clips + created_clips if c.audio_type == AudioType.ORIGINAL_AUDIO.value),
            },
            "provider_hints": {
                "default_provider": AudioProviderFactory.get_default_provider_name(),
                "available_providers": AudioProviderFactory.list_providers(),
            },
        }

        # Update Project status if in video completed stage
        if project.status in ("VIDEO_IN_PROGRESS", "VIDEO_GENERATED", "VIDEO_APPROVED", "FINAL_REVIEW"):
            project.status = "AUDIO_PLAN_GENERATED"
            project.updated_at = now

        # Finding 1: Full History Retention & Audit for created clips and plan
        for c in created_clips:
            cls.record_clip_history(db, c, actor="SYSTEM", action="CREATE", change_reason="Initial creation from audio plan")

        cls.record_plan_version(
            db,
            plan,
            actor="USER",
            action="GENERATE_PLAN" if plan.version > 1 else "CREATE_PLAN",
            change_reason=f"Generated audio plan revision {plan.version}",
        )

        db.commit()
        db.refresh(plan)
        return plan

    @classmethod
    def approve_audio_plan(
        cls,
        db: Session,
        project_id: uuid.UUID,
    ) -> AudioPlan:
        """Approve the current audio plan, transitioning stage to AUDIO_PLAN_APPROVED."""
        plan = db.query(AudioPlan).filter(AudioPlan.project_id == project_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail=f"No audio plan found for project '{project_id}'.")

        project = db.get(Project, project_id)
        now = datetime.now(timezone.utc)
        plan.status = "APPROVED"
        plan.updated_at = now

        if project:
            project.status = "AUDIO_PLAN_APPROVED"
            project.updated_at = now

        cls.record_plan_version(
            db,
            plan,
            actor="USER",
            action="APPROVE_PLAN",
            change_reason="Audio plan approved",
        )
        db.commit()
        db.refresh(plan)
        return plan

    @classmethod
    def generate_clip_audio(
        cls,
        db: Session,
        project_id: uuid.UUID,
        clip_id: uuid.UUID,
        provider_name: Optional[str] = None,
        cost_authorized: bool = False,
        actor: str = "USER",
        provider_specific_params: Optional[Dict[str, Any]] = None,
    ) -> AudioClip:
        """Generate audio for a single AudioClip with atomic pre-provider claim and budget reservation."""
        # 1. Project lock for atomic budget check
        project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        clip = db.query(AudioClip).filter(AudioClip.id == clip_id, AudioClip.project_id == project_id).first()
        if not clip:
            raise HTTPException(status_code=404, detail=f"AudioClip '{clip_id}' not found in project '{project_id}'.")

        if clip.is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"AudioClip '{clip_id}' is locked against modification.",
            )

        if clip.status in ("SUBMITTING", "GENERATING", "POLLING"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"AudioClip '{clip_id}' already has active generation in progress ({clip.status}).",
            )

        if clip.status == "RECONCILIATION_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"AudioClip '{clip_id}' requires reconciliation. Resolve ambiguous outcome first.",
            )

        # 2. GENERATION_MODE MUST CONTROL EXECUTION
        # Branch explicitly by generation_mode: EMBEDDED_EXISTING, WITH_VIDEO, SEPARATE_AUDIO

        if clip.generation_mode == AudioGenerationMode.EMBEDDED_EXISTING.value or clip.source_type == AudioSourceType.EMBEDDED_VIDEO_AUDIO.value:
            prov = clip.provenance or {}
            if prov.get("audio_presence") == "UNKNOWN":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Embedded audio presence is unknown or unverified; audio stream probe required before making ready.",
                )
            clip.status = "READY"
            clip.version += 1
            clip.updated_at = datetime.now(timezone.utc)
            cls.record_clip_history(db, clip, actor=actor, action="GENERATE", change_reason="Embedded video audio marked READY")
            db.commit()
            db.refresh(clip)
            return clip

        if clip.generation_mode == AudioGenerationMode.WITH_VIDEO.value:
            # CRITICAL: A WITH_VIDEO clip must NEVER silently call AudioProvider.
            # Enforce Cost Safety & Hard Budget Check before video provider regeneration
            estimated_cost = 0.10  # Video provider estimated cost
            budget_summary = BudgetService.get_budget_status(db, project_id)
            committed_cost = budget_summary.get("total_committed_cost", 0.0)
            limit = project.budget_limit
            if budget_summary.get("is_hard_limit_exceeded") or (
                limit is not None and round(committed_cost + estimated_cost, 4) > limit
            ):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Project hard budget limit exceeded or will be exceeded by video generation.",
                )

            default_cfg = getattr(project, "default_config", None) or {}
            mode_cfg = getattr(project, "mode_config", None) or {}
            has_persisted = False
            if isinstance(default_cfg, dict):
                has_persisted = bool(default_cfg.get("auto_cost_authorized") or default_cfg.get("cost_authorized"))
            if not has_persisted and isinstance(mode_cfg, dict):
                has_persisted = bool(mode_cfg.get("auto_cost_authorized") or mode_cfg.get("cost_authorized"))
            effective_cost_auth = cost_authorized or has_persisted

            if not effective_cost_auth:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Video provider regeneration is chargeable. Explicit cost authorization required.",
                )

            # Fail closed with explicit blocker string WITH_VIDEO_REQUIRES_VIDEO_REGENERATION
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="WITH_VIDEO_REQUIRES_VIDEO_REGENERATION: Native video provider regeneration for WITH_VIDEO audio is not implemented in WP014. Trigger video generation action or use SEPARATE_AUDIO mode.",
            )

        eff_provider_name = provider_name or AudioProviderFactory.get_default_provider_name()
        provider = AudioProviderFactory.get_provider(eff_provider_name)

        # Calculate estimated cost
        estimated_cost = 0.05 if clip.audio_type == AudioType.BGM.value else 0.02

        # 2. Hard budget check
        budget_summary = BudgetService.get_budget_status(db, project_id)
        committed_cost = budget_summary.get("total_committed_cost", 0.0)
        limit = project.budget_limit
        if budget_summary.get("is_hard_limit_exceeded") or (
            limit is not None and round(committed_cost + estimated_cost, 4) > limit
        ):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Project hard budget limit exceeded or will be exceeded by audio generation (committed: {committed_cost:.2f}, estimated: {estimated_cost:.2f}, limit: {limit:.2f}).",
            )

        # 3. Cost authorization check for AUTO mode
        default_cfg = getattr(project, "default_config", None) or {}
        mode_cfg = getattr(project, "mode_config", None) or {}
        has_persisted = False
        if isinstance(default_cfg, dict):
            has_persisted = bool(default_cfg.get("auto_cost_authorized") or default_cfg.get("cost_authorized"))
        if not has_persisted and isinstance(mode_cfg, dict):
            has_persisted = bool(mode_cfg.get("auto_cost_authorized") or mode_cfg.get("cost_authorized"))
        effective_cost_auth = cost_authorized or has_persisted

        if actor == "AUTO" and not effective_cost_auth:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Audio generation is chargeable. Explicit cost authorization required in AUTO mode.",
            )

        # 4. ATOMIC PRE-PROVIDER CLAIM & COST RESERVATION
        now = datetime.now(timezone.utc)
        clip.status = "SUBMITTING"
        clip.version += 1
        clip.updated_at = now
        db.flush()

        ledger_key = f"audio_clip_{clip.id}_{clip.version}"
        CostLedgerService.record_entry(
            db,
            project_id=project_id,
            shot_id=clip.shot_id,
            job_id=None,
            provider=eff_provider_name,
            operation=f"AUDIO_{clip.audio_type}",
            model=None,
            usage_units={"audio_type": clip.audio_type, "duration": clip.duration_seconds},
            estimated_cost=estimated_cost,
            currency="USD",
            cost_status=CostStatus.ESTIMATED,
            idempotency_key=ledger_key,
            description=f"Audio generation for {clip.name} ({clip.audio_type})",
            commit=False,
        )
        db.commit()

        # Build Generation Params
        params = AudioGenerationParams(
            clip_id=str(clip.id),
            audio_type=clip.audio_type,
            prompt=clip.prompt or clip.name,
            duration_seconds=clip.duration_seconds or 4.0,
            speaker=clip.speaker,
            language=clip.language or "en",
            provider_specific_params=provider_specific_params,
        )

        # 5. EXECUTE GENERATION VIA PROVIDER
        def _invoke_provider() -> AudioJobResult:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        return executor.submit(asyncio.run, provider.generate_audio(params)).result()
                return loop.run_until_complete(provider.generate_audio(params))
            except RuntimeError:
                return asyncio.run(provider.generate_audio(params))

        try:
            result: AudioJobResult = _invoke_provider()
        except Exception as exc:
            # Generic transport/timeout/connection/unknown exceptions must be treated as ambiguous.
            clip.status = "RECONCILIATION_REQUIRED"
            clip.provenance = {"error": str(exc), "stage": "submission_exception"}
            clip.updated_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Audio provider invocation failed with ambiguous outcome: {str(exc)}. Clip placed in RECONCILIATION_REQUIRED.",
            )

        now_res = datetime.now(timezone.utc)

        # 6. PROVIDER RESULT HANDLING
        if result.submission_uncertain:
            clip.status = "RECONCILIATION_REQUIRED"
            clip.provenance = {
                "provider_job_id": result.provider_job_id,
                "error": result.error_message or "Ambiguous provider submission",
            }
            clip.updated_at = now_res
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Provider response was ambiguous. Clip placed in RECONCILIATION_REQUIRED.",
            )

        if result.status == "FAILED":
            clip.status = "FAILED"
            clip.provenance = {
                "provider_job_id": result.provider_job_id,
                "error": result.error_message or "Audio generation failed",
            }
            clip.updated_at = now_res
            CostLedgerService.record_entry(
                db,
                project_id=project_id,
                shot_id=clip.shot_id,
                job_id=None,
                provider=eff_provider_name,
                operation=f"AUDIO_{clip.audio_type}",
                estimated_cost=0.0,
                actual_cost=0.0,
                currency="USD",
                cost_status=CostStatus.CANCELLED,
                idempotency_key=ledger_key,
                description=f"Failed audio generation for {clip.name}",
                commit=False,
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Audio generation failed: {result.error_message or 'Unknown error'}",
            )

        # Completed result
        audio_bytes = result.audio_data or b""
        if not audio_bytes:
            clip.status = "FAILED"
            clip.provenance = {"error": "Provider completed result missing audio content"}
            clip.updated_at = now_res
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Provider completed result missing audio content.",
            )

        # Store into Object Storage
        storage = get_storage_provider()
        asset_id = uuid.uuid4()
        storage_bucket = settings.OBJECT_STORAGE_BUCKET
        ext = "mp3" if result.content_type == "audio/mpeg" else "wav"
        storage_key = f"projects/{project_id}/audio/{clip.id}_{asset_id.hex[:8]}.{ext}"

        storage.put_object(
            bucket=storage_bucket,
            key=storage_key,
            data=audio_bytes,
            content_type=result.content_type or "audio/wav",
        )

        checksum = hashlib.sha256(audio_bytes).hexdigest()
        asset = Asset(
            id=asset_id,
            project_id=project_id,
            name=f"{clip.name} Audio",
            original_filename=f"audio_{clip.id}_{clip.audio_type}.{ext}",
            asset_type="AUDIO",
            content_type=result.content_type or "audio/wav",
            file_size_bytes=len(audio_bytes),
            checksum_sha256=checksum,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            created_at=now_res,
            updated_at=now_res,
        )
        db.add(asset)
        db.flush()

        # Update clip and confirm cost
        clip.asset_id = asset.id
        clip.status = "READY"
        clip.duration_seconds = result.duration_seconds or clip.duration_seconds
        clip.provenance = {
            "provider": eff_provider_name,
            "provider_job_id": result.provider_job_id,
            "cost_usd": result.cost_usd or estimated_cost,
        }
        clip.updated_at = now_res

        actual_cost = result.cost_usd if result.cost_usd is not None else estimated_cost
        CostLedgerService.record_entry(
            db,
            project_id=project_id,
            shot_id=clip.shot_id,
            job_id=None,
            provider=eff_provider_name,
            operation=f"AUDIO_{clip.audio_type}",
            model=None,
            usage_units={"duration": clip.duration_seconds},
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            currency="USD",
            cost_status=CostStatus.CONFIRMED,
            idempotency_key=ledger_key,
            description=f"Confirmed audio generation for {clip.name}",
            commit=False,
        )

        db.commit()
        db.refresh(clip)
        return clip

    @classmethod
    def execute_audio_batch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        action: str,
        cost_authorized: bool = False,
        actor: str = "USER",
        provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute set-based bounded batch operations for audio clips."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        # Target selection based on action
        query = db.query(AudioClip).filter(AudioClip.project_id == project_id)

        if action == "GENERATE_ALL_VO":
            query = query.filter(
                AudioClip.audio_type.in_([AudioType.VO.value, AudioType.DIALOGUE.value]),
                AudioClip.status.in_(["PENDING", "FAILED"]),
            )
        elif action == "ASSIGN_BGM":
            query = query.filter(
                AudioClip.audio_type == AudioType.BGM.value,
                AudioClip.status.in_(["PENDING", "FAILED"]),
            )
        elif action == "ASSIGN_SFX":
            query = query.filter(
                AudioClip.audio_type == AudioType.SFX.value,
                AudioClip.status.in_(["PENDING", "FAILED"]),
            )
        elif action == "ASSIGN_AMBIENCE":
            query = query.filter(
                AudioClip.audio_type == AudioType.AMBIENCE.value,
                AudioClip.status.in_(["PENDING", "FAILED"]),
            )
        elif action == "CONTINUE_INCOMPLETE_AUDIO":
            query = query.filter(AudioClip.status == "PENDING")
        elif action == "RETRY_FAILED_AUDIO":
            query = query.filter(AudioClip.status == "FAILED")
        else:
            query = query.filter(AudioClip.status.in_(["PENDING", "FAILED"]))

        target_clips = query.order_by(AudioClip.created_at.asc()).limit(50).all()

        succeeded = 0
        failed = 0
        skipped = 0
        errors = []

        for clip in target_clips:
            if clip.is_locked:
                skipped += 1
                continue
            try:
                cls.generate_clip_audio(
                    db=db,
                    project_id=project_id,
                    clip_id=clip.id,
                    provider_name=provider_name,
                    cost_authorized=cost_authorized,
                    actor=actor,
                )
                succeeded += 1
            except HTTPException as e:
                failed += 1
                errors.append({"clip_id": str(clip.id), "error": e.detail})
            except Exception as e:
                failed += 1
                errors.append({"clip_id": str(clip.id), "error": str(e)})

        return {
            "action": action,
            "processed": len(target_clips),
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        }

    @classmethod
    def compute_auto_mix(
        cls,
        db: Session,
        project_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Compute auto-ducking metadata and mixing plan for project audio tracks."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        clips = (
            db.query(AudioClip)
            .filter(AudioClip.project_id == project_id)
            .order_by(AudioClip.start_time.asc(), AudioClip.created_at.asc())
            .all()
        )

        # 1. Gather foreground speech intervals (VO, Dialogue)
        speech_intervals: List[Dict[str, Any]] = []
        for c in clips:
            if c.ducking_role == DuckingRole.FOREGROUND.value and not c.mute:
                duration = c.duration_seconds or 4.0
                speech_intervals.append({
                    "clip_id": str(c.id),
                    "name": c.name,
                    "start": c.start_time,
                    "end": c.start_time + duration,
                    "duck_attenuation_db": -12.0,
                })

        # 2. Build track mixing controls
        track_mixes = []
        for c in clips:
            is_background = c.ducking_role == DuckingRole.BACKGROUND.value
            effective_attenuation = c.ducking_amount_db if (is_background and speech_intervals) else 0.0
            track_mixes.append({
                "clip_id": str(c.id),
                "name": c.name,
                "audio_type": c.audio_type,
                "scope": c.scope,
                "ducking_role": c.ducking_role,
                "volume": c.volume,
                "mute": c.mute,
                "fade_in": c.fade_in,
                "fade_out": c.fade_out,
                "ducking_attenuation_db": effective_attenuation,
                "has_asset": c.asset_id is not None,
                "status": c.status,
            })

        mix_metadata = {
            "project_id": str(project_id),
            "speech_intervals": speech_intervals,
            "tracks": track_mixes,
            "auto_ducking_enabled": True,
            "default_ducking_amount_db": -12.0,
            "total_tracks": len(track_mixes),
            "master_volume": 1.0,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist to AudioPlan
        plan = db.query(AudioPlan).filter(AudioPlan.project_id == project_id).first()
        if plan:
            data = plan.plan_data or {}
            data["auto_mix"] = mix_metadata
            plan.plan_data = data
            plan.updated_at = datetime.now(timezone.utc)
            db.commit()

        return mix_metadata
