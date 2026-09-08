"""Project import service for validating and extracting .orbis archive packages.

Enforces:
1. Strict 4-phase validation pipeline
2. CLONE (default, fresh UUIDs, remapped FKs, lineage) vs RESTORE (original UUIDs, fail-closed on collision)
3. Atomic database transaction with storage upload compensation rollback
4. Bit-for-bit preservation of historical execution records tagged with imported_historical=True and execution_disabled=True
"""
import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.story import Story
from app.models.story_version import StoryVersion
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.document_extraction import DocumentExtraction
from app.models.reference_library import (
    ProjectReference,
    CharacterBible,
    LocationBible,
    StyleBible,
    BrandBible,
)
from app.models.asset_lock import AssetLock
from app.models.audio_plan import AudioPlan
from app.models.audio_history import AudioPlanVersion, AudioClipHistory
from app.models.audio_clip import AudioClip
from app.models.assembly import (
    AssemblyTimeline,
    AssemblyScene,
    AssemblyShotPlacement,
    TimelineCheckpoint,
    TimelineAudit,
)
from app.models.qc import (
    QCRun,
    QCFinding,
    WarningDecision,
    ApprovalRecord,
)
from app.models.render_batch import RenderBatch
from app.models.render_job import RenderJob
from app.models.generation_job import GenerationJob
from app.models.batch_run import BatchRun, BatchRunItem
from app.models.generation_audit import GenerationAuditLog
from app.models.orchestration_audit import OrchestrationAudit
from app.models.usage_ledger import UsageLedger, LedgerAdjustment
from app.services.storage import get_storage_provider, ObjectStorageProvider
from app.services.archive.constants import SUPPORTED_MAJOR_VERSIONS
from app.services.archive.security import ArchiveSecurityValidator, ArchiveSecurityError
from app.services.archive.checksums import ArchiveChecksumService, ChecksumVerificationError

logger = logging.getLogger(__name__)


class ArchiveImportError(Exception):
    """Base error for import failures."""
    pass


class ProjectCollisionError(ArchiveImportError):
    """Raised when RESTORE mode collides with an existing project in the database."""
    pass


class VersionIncompatibilityError(ArchiveImportError):
    """Raised when archive format version is unsupported."""
    pass


def parse_datetime(dt_val: Any) -> Optional[datetime]:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    try:
        return datetime.fromisoformat(str(dt_val))
    except Exception:
        return None


def parse_uuid(u_val: Any) -> Optional[uuid.UUID]:
    if not u_val:
        return None
    if isinstance(u_val, uuid.UUID):
        return u_val
    try:
        return uuid.UUID(str(u_val))
    except Exception:
        return None


class RemapContext:
    """Manages identifier remapping for CLONE mode."""

    def __init__(self, mode: str, original_project_id: uuid.UUID, new_project_id: Optional[uuid.UUID] = None):
        self.mode = mode.upper()
        self.original_project_id = original_project_id
        self.id_map: Dict[uuid.UUID, uuid.UUID] = {}
        self.entity_type_map: Dict[Tuple[str, uuid.UUID], uuid.UUID] = {}

        if self.mode == "CLONE":
            self.new_project_id = new_project_id or uuid.uuid4()
            self.id_map[original_project_id] = self.new_project_id
        else:
            self.new_project_id = original_project_id

    def get_or_create(self, old_id: Optional[uuid.UUID], entity_type: str = "") -> Optional[uuid.UUID]:
        if old_id is None:
            return None
        if self.mode == "RESTORE":
            return old_id

        if old_id not in self.id_map:
            new_id = uuid.uuid4()
            self.id_map[old_id] = new_id
            if entity_type:
                self.entity_type_map[(entity_type.upper(), old_id)] = new_id
        return self.id_map[old_id]

    def remap_polymorphic(self, entity_type: str, old_entity_id: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
        if old_entity_id is None:
            return None
        if self.mode == "RESTORE":
            return old_entity_id

        key = (entity_type.upper(), old_entity_id)
        if key in self.entity_type_map:
            return self.entity_type_map[key]
        # Fallback to general id_map
        return self.id_map.get(old_entity_id, old_entity_id)


class ArchivePreflightError(ArchiveImportError):
    """Raised when preflight entity graph validation or asset completeness checks fail."""
    pass


class ArchivePreflightValidator:
    """Canonical Phase-3 Preflight Validator for .orbis archives.

    Parses and validates the entire bounded entity graph and asset completeness
    strictly BEFORE any database mutation or storage upload.
    """

    SUPPORTED_LOCK_TYPES = {
        "PROJECT",
        "STORY",
        "SCENE",
        "SHOT",
        "ASSET",
        "CHARACTER_BIBLE",
        "LOCATION_BIBLE",
        "STYLE_BIBLE",
        "BRAND_BIBLE",
        "AUDIO_PLAN",
        "TIMELINE",
        "ASSEMBLY_TIMELINE",
        "ASSEMBLY_SCENE",
        "ASSEMBLY_SHOT_PLACEMENT",
    }

    REQUIRED_ENTITY_FILES = [
        "project.json",
        "entities/story.json",
        "entities/scenes.json",
        "entities/shots.json",
        "entities/assets.json",
        "assets/manifest.json",
    ]

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.seen_ids: Dict[uuid.UUID, str] = {}

        # Known ID sets
        self.project_id: Optional[uuid.UUID] = None
        self.story_ids: Set[uuid.UUID] = set()
        self.story_version_ids: Set[uuid.UUID] = set()
        self.scene_ids: Set[uuid.UUID] = set()
        self.shot_ids: Set[uuid.UUID] = set()
        self.asset_ids: Set[uuid.UUID] = set()
        self.doc_extraction_ids: Set[uuid.UUID] = set()
        self.reference_ids: Set[uuid.UUID] = set()
        self.bible_ids: Set[uuid.UUID] = set()
        self.lock_ids: Set[uuid.UUID] = set()
        self.audio_plan_ids: Set[uuid.UUID] = set()
        self.audio_plan_version_ids: Set[uuid.UUID] = set()
        self.audio_clip_ids: Set[uuid.UUID] = set()
        self.audio_clip_history_ids: Set[uuid.UUID] = set()
        self.timeline_ids: Set[uuid.UUID] = set()
        self.assembly_scene_ids: Set[uuid.UUID] = set()
        self.assembly_placement_ids: Set[uuid.UUID] = set()
        self.checkpoint_ids: Set[uuid.UUID] = set()
        self.qc_run_ids: Set[uuid.UUID] = set()
        self.qc_finding_ids: Set[uuid.UUID] = set()
        self.warning_decision_ids: Set[uuid.UUID] = set()
        self.approval_ids: Set[uuid.UUID] = set()
        self.render_batch_ids: Set[uuid.UUID] = set()
        self.render_job_ids: Set[uuid.UUID] = set()
        self.generation_job_ids: Set[uuid.UUID] = set()
        self.batch_run_ids: Set[uuid.UUID] = set()
        self.batch_run_item_ids: Set[uuid.UUID] = set()
        self.usage_ledger_ids: Set[uuid.UUID] = set()
        self.ledger_adjustment_ids: Set[uuid.UUID] = set()

    def _read_json(self, rel_path: str, required: bool = True) -> Any:
        full_path = os.path.join(self.temp_dir, rel_path)
        if not os.path.exists(full_path):
            if required:
                raise ArchivePreflightError(f"Required archive file missing: '{rel_path}'")
            return None
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ArchivePreflightError(f"Invalid JSON in '{rel_path}': {str(e)}") from e

    def _register_id(self, entity_type: str, raw_id: Any) -> uuid.UUID:
        uid = parse_uuid(raw_id)
        if not uid:
            raise ArchivePreflightError(f"Missing or invalid UUID '{raw_id}' in entity '{entity_type}'")
        if uid in self.seen_ids:
            raise ArchivePreflightError(
                f"Duplicate entity ID '{uid}' detected in '{entity_type}' (already defined in '{self.seen_ids[uid]}')"
            )
        self.seen_ids[uid] = entity_type
        return uid

    def validate_graph(self) -> None:
        """Runs the complete Phase-3 graph validation and asset completeness inspection."""
        # 1. Check required entity files
        for req_f in self.REQUIRED_ENTITY_FILES:
            full_p = os.path.join(self.temp_dir, req_f)
            if not os.path.exists(full_p):
                raise ArchivePreflightError(f"Required archive file missing: '{req_f}'")

        # 2. Project
        project_raw = self._read_json("project.json", required=True)
        if not isinstance(project_raw, dict):
            raise ArchivePreflightError("project.json must contain a JSON object")
        self.project_id = self._register_id("PROJECT", project_raw.get("id"))

        # 3. Read and register IDs across all entities
        # Story
        story_data = self._read_json("entities/story.json", required=True)
        if isinstance(story_data, dict):
            st = story_data.get("story")
            if st and isinstance(st, dict):
                self.story_ids.add(self._register_id("STORY", st.get("id")))
            for sv in story_data.get("story_versions", []):
                self.story_version_ids.add(self._register_id("STORY_VERSION", sv.get("id")))

        # Scenes
        scenes_data = self._read_json("entities/scenes.json", required=True)
        if not isinstance(scenes_data, list):
            raise ArchivePreflightError("entities/scenes.json must contain a list")
        for sc in scenes_data:
            self.scene_ids.add(self._register_id("SCENE", sc.get("id")))

        # Shots
        shots_data = self._read_json("entities/shots.json", required=True)
        if not isinstance(shots_data, list):
            raise ArchivePreflightError("entities/shots.json must contain a list")
        for sh in shots_data:
            self.shot_ids.add(self._register_id("SHOT", sh.get("id")))

        # Assets
        assets_data = self._read_json("entities/assets.json", required=True)
        if not isinstance(assets_data, list):
            raise ArchivePreflightError("entities/assets.json must contain a list")
        for a in assets_data:
            self.asset_ids.add(self._register_id("ASSET", a.get("id")))

        # Document Extractions
        doc_data = self._read_json("entities/document_extractions.json", required=False) or []
        for d in doc_data:
            self.doc_extraction_ids.add(self._register_id("DOCUMENT_EXTRACTION", d.get("id")))

        # Reference Library
        ref_data = self._read_json("entities/reference_library.json", required=False) or {}
        for pr in ref_data.get("project_references", []):
            self.reference_ids.add(self._register_id("PROJECT_REFERENCE", pr.get("id")))
        for cb in ref_data.get("character_bibles", []):
            self.bible_ids.add(self._register_id("CHARACTER_BIBLE", cb.get("id")))
        for lb in ref_data.get("location_bibles", []):
            self.bible_ids.add(self._register_id("LOCATION_BIBLE", lb.get("id")))
        for sb in ref_data.get("style_bibles", []):
            self.bible_ids.add(self._register_id("STYLE_BIBLE", sb.get("id")))
        for bb in ref_data.get("brand_bibles", []):
            self.bible_ids.add(self._register_id("BRAND_BIBLE", bb.get("id")))

        # Asset Locks
        locks_data = self._read_json("entities/asset_locks.json", required=False) or []
        for lk in locks_data:
            self.lock_ids.add(self._register_id("ASSET_LOCK", lk.get("id")))

        # Audio
        audio_data = self._read_json("entities/audio.json", required=False) or {}
        for ap in audio_data.get("audio_plans", []):
            self.audio_plan_ids.add(self._register_id("AUDIO_PLAN", ap.get("id")))
        for apv in audio_data.get("audio_plan_versions", []):
            self.audio_plan_version_ids.add(self._register_id("AUDIO_PLAN_VERSION", apv.get("id")))
        for ac in audio_data.get("audio_clips", []):
            self.audio_clip_ids.add(self._register_id("AUDIO_CLIP", ac.get("id")))
        for ach in audio_data.get("audio_clip_histories", []):
            self.audio_clip_history_ids.add(self._register_id("AUDIO_CLIP_HISTORY", ach.get("id")))

        # Assembly
        assembly_data = self._read_json("entities/assembly.json", required=False) or {}
        for tm in assembly_data.get("timelines", []):
            self.timeline_ids.add(self._register_id("TIMELINE", tm.get("id")))
        for asc in assembly_data.get("assembly_scenes", []):
            self.assembly_scene_ids.add(self._register_id("ASSEMBLY_SCENE", asc.get("id")))
        for asp in assembly_data.get("assembly_shot_placements", []):
            self.assembly_placement_ids.add(self._register_id("ASSEMBLY_SHOT_PLACEMENT", asp.get("id")))
        for chk in assembly_data.get("checkpoints", []):
            self.checkpoint_ids.add(self._register_id("TIMELINE_CHECKPOINT", chk.get("id")))

        # QC
        qc_data = self._read_json("entities/qc.json", required=False) or {}
        for qr in qc_data.get("qc_runs", []):
            self.qc_run_ids.add(self._register_id("QC_RUN", qr.get("id")))
        for qf in qc_data.get("qc_findings", []):
            self.qc_finding_ids.add(self._register_id("QC_FINDING", qf.get("id")))
        for wd in qc_data.get("warning_decisions", []):
            self.warning_decision_ids.add(self._register_id("WARNING_DECISION", wd.get("id")))
        for app in qc_data.get("approvals", []):
            self.approval_ids.add(self._register_id("APPROVAL_RECORD", app.get("id")))

        # Render Jobs
        rj_data = self._read_json("entities/render_jobs.json", required=False) or {}
        for rb in rj_data.get("render_batches", []):
            self.render_batch_ids.add(self._register_id("RENDER_BATCH", rb.get("id")))
        for rj in rj_data.get("render_jobs", []):
            self.render_job_ids.add(self._register_id("RENDER_JOB", rj.get("id")))

        # Generation Jobs
        gj_data = self._read_json("entities/generation_jobs.json", required=False) or {}
        for gj in gj_data.get("generation_jobs", []):
            self.generation_job_ids.add(self._register_id("GENERATION_JOB", gj.get("id")))
        for br in gj_data.get("batch_runs", []):
            self.batch_run_ids.add(self._register_id("BATCH_RUN", br.get("id")))
        for bri in gj_data.get("batch_run_items", []):
            self.batch_run_item_ids.add(self._register_id("BATCH_RUN_ITEM", bri.get("id")))

        # Usage Ledger
        ul_data = self._read_json("history/usage_ledger.json", required=False) or {}
        for ul in ul_data.get("entries", []):
            self.usage_ledger_ids.add(self._register_id("USAGE_LEDGER", ul.get("id")))
        for adj in ul_data.get("adjustments", []):
            self.ledger_adjustment_ids.add(self._register_id("LEDGER_ADJUSTMENT", adj.get("id")))

        # 4. Check project_id integrity across all entities
        def assert_project_id(rec: Dict[str, Any], entity_name: str) -> None:
            if "project_id" in rec and rec["project_id"] is not None:
                pid = parse_uuid(rec["project_id"])
                if pid != self.project_id:
                    raise ArchivePreflightError(
                        f"Foreign project_id '{pid}' in {entity_name} does not match archive project_id '{self.project_id}'"
                    )

        if isinstance(story_data, dict):
            st = story_data.get("story")
            if st and isinstance(st, dict):
                assert_project_id(st, "Story")
            for sv in story_data.get("story_versions", []):
                assert_project_id(sv, "StoryVersion")
        for sc in scenes_data:
            assert_project_id(sc, "Scene")
        for a in assets_data:
            assert_project_id(a, "Asset")
        for pr in ref_data.get("project_references", []):
            assert_project_id(pr, "ProjectReference")
        for cb in ref_data.get("character_bibles", []):
            assert_project_id(cb, "CharacterBible")
        for lb in ref_data.get("location_bibles", []):
            assert_project_id(lb, "LocationBible")
        for sb in ref_data.get("style_bibles", []):
            assert_project_id(sb, "StyleBible")
        for bb in ref_data.get("brand_bibles", []):
            assert_project_id(bb, "BrandBible")
        for lk in locks_data:
            assert_project_id(lk, "AssetLock")
        for ap in audio_data.get("audio_plans", []):
            assert_project_id(ap, "AudioPlan")
        for ac in audio_data.get("audio_clips", []):
            assert_project_id(ac, "AudioClip")
        for tm in assembly_data.get("timelines", []):
            assert_project_id(tm, "AssemblyTimeline")
        for qr in qc_data.get("qc_runs", []):
            assert_project_id(qr, "QCRun")
        for app in qc_data.get("approvals", []):
            assert_project_id(app, "ApprovalRecord")
        for rb in rj_data.get("render_batches", []):
            assert_project_id(rb, "RenderBatch")
        for rj in rj_data.get("render_jobs", []):
            assert_project_id(rj, "RenderJob")
        for br in gj_data.get("batch_runs", []):
            assert_project_id(br, "BatchRun")
        for ul in ul_data.get("entries", []):
            assert_project_id(ul, "UsageLedger")

        # 5. Check Foreign Key graph integrity
        # StoryVersion -> Story
        if isinstance(story_data, dict):
            for sv in story_data.get("story_versions", []):
                sid = parse_uuid(sv.get("story_id"))
                if sid and sid not in self.story_ids:
                    raise ArchivePreflightError(f"StoryVersion '{sv.get('id')}' references nonexistent Story '{sid}'")

        # Shots -> Scene, Assets
        for sh in shots_data:
            scid = parse_uuid(sh.get("scene_id"))
            if not scid or scid not in self.scene_ids:
                raise ArchivePreflightError(f"Shot '{sh.get('id')}' references nonexistent Scene '{sh.get('scene_id')}'")
            if sh.get("source_asset_id"):
                aid = parse_uuid(sh["source_asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"Shot '{sh.get('id')}' references nonexistent source Asset '{sh['source_asset_id']}'")
            if sh.get("keyframe_asset_id"):
                aid = parse_uuid(sh["keyframe_asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"Shot '{sh.get('id')}' references nonexistent keyframe Asset '{sh['keyframe_asset_id']}'")

        # DocumentExtractions -> Asset
        for d in doc_data:
            aid = parse_uuid(d.get("asset_id"))
            if not aid or aid not in self.asset_ids:
                raise ArchivePreflightError(f"DocumentExtraction '{d.get('id')}' references nonexistent Asset '{d.get('asset_id')}'")

        # Reference Library -> Assets
        for pr in ref_data.get("project_references", []):
            aid = parse_uuid(pr.get("asset_id"))
            if not aid or aid not in self.asset_ids:
                raise ArchivePreflightError(f"ProjectReference '{pr.get('id')}' references nonexistent Asset '{pr.get('asset_id')}'")
        for bible_name, items in [
            ("CharacterBible", ref_data.get("character_bibles", [])),
            ("LocationBible", ref_data.get("location_bibles", [])),
            ("StyleBible", ref_data.get("style_bibles", [])),
        ]:
            for item in items:
                for ref_aid in (item.get("reference_asset_ids") or []):
                    aid = parse_uuid(ref_aid)
                    if not aid or aid not in self.asset_ids:
                        raise ArchivePreflightError(f"{bible_name} '{item.get('id')}' references nonexistent Asset '{ref_aid}'")
        for bb in ref_data.get("brand_bibles", []):
            if bb.get("logo_asset_id"):
                aid = parse_uuid(bb["logo_asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"BrandBible '{bb.get('id')}' references nonexistent logo Asset '{bb['logo_asset_id']}'")

        # Asset Locks -> polymorphic target
        for lk in locks_data:
            ent_type = (lk.get("entity_type") or "").upper()
            if ent_type not in self.SUPPORTED_LOCK_TYPES:
                raise ArchivePreflightError(f"AssetLock '{lk.get('id')}' specifies unsupported entity_type '{ent_type}'")
            eid = parse_uuid(lk.get("entity_id"))
            if not eid:
                raise ArchivePreflightError(f"AssetLock '{lk.get('id')}' has invalid entity_id '{lk.get('entity_id')}'")
            valid_target = False
            if ent_type == "PROJECT" and eid == self.project_id:
                valid_target = True
            elif ent_type == "STORY" and eid in self.story_ids:
                valid_target = True
            elif ent_type == "SCENE" and eid in self.scene_ids:
                valid_target = True
            elif ent_type == "SHOT" and eid in self.shot_ids:
                valid_target = True
            elif ent_type == "ASSET" and eid in self.asset_ids:
                valid_target = True
            elif ent_type in ("CHARACTER_BIBLE", "LOCATION_BIBLE", "STYLE_BIBLE", "BRAND_BIBLE") and eid in self.bible_ids:
                valid_target = True
            elif ent_type == "AUDIO_PLAN" and eid in self.audio_plan_ids:
                valid_target = True
            elif ent_type in ("TIMELINE", "ASSEMBLY_TIMELINE") and eid in self.timeline_ids:
                valid_target = True
            elif ent_type == "ASSEMBLY_SCENE" and eid in self.assembly_scene_ids:
                valid_target = True
            elif ent_type == "ASSEMBLY_SHOT_PLACEMENT" and eid in self.assembly_placement_ids:
                valid_target = True

            if not valid_target:
                raise ArchivePreflightError(f"AssetLock '{lk.get('id')}' references nonexistent {ent_type} '{eid}'")

        # Audio -> plans, scenes, shots, assets
        for apv in audio_data.get("audio_plan_versions", []):
            pid = parse_uuid(apv.get("audio_plan_id"))
            if not pid or pid not in self.audio_plan_ids:
                raise ArchivePreflightError(f"AudioPlanVersion '{apv.get('id')}' references nonexistent AudioPlan '{pid}'")
        for ac in audio_data.get("audio_clips", []):
            if ac.get("scene_id"):
                scid = parse_uuid(ac["scene_id"])
                if not scid or scid not in self.scene_ids:
                    raise ArchivePreflightError(f"AudioClip '{ac.get('id')}' references nonexistent Scene '{scid}'")
            if ac.get("shot_id"):
                shid = parse_uuid(ac["shot_id"])
                if not shid or shid not in self.shot_ids:
                    raise ArchivePreflightError(f"AudioClip '{ac.get('id')}' references nonexistent Shot '{shid}'")
            if ac.get("asset_id"):
                aid = parse_uuid(ac["asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"AudioClip '{ac.get('id')}' references nonexistent Asset '{aid}'")
            if ac.get("video_asset_id"):
                aid = parse_uuid(ac["video_asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"AudioClip '{ac.get('id')}' references nonexistent video Asset '{aid}'")
        for ach in audio_data.get("audio_clip_histories", []):
            cid = parse_uuid(ach.get("clip_id") or ach.get("audio_clip_id"))
            if not cid or cid not in self.audio_clip_ids:
                raise ArchivePreflightError(f"AudioClipHistory '{ach.get('id')}' references nonexistent AudioClip '{cid}'")
            if ach.get("asset_id"):
                aid = parse_uuid(ach["asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"AudioClipHistory '{ach.get('id')}' references nonexistent Asset '{aid}'")

        # Assembly -> timelines, scenes, shots, assets
        for asc in assembly_data.get("assembly_scenes", []):
            tid = parse_uuid(asc.get("timeline_id"))
            if not tid or tid not in self.timeline_ids:
                raise ArchivePreflightError(f"AssemblyScene '{asc.get('id')}' references nonexistent Timeline '{tid}'")
            scid = parse_uuid(asc.get("scene_id"))
            if not scid or scid not in self.scene_ids:
                raise ArchivePreflightError(f"AssemblyScene '{asc.get('id')}' references nonexistent Scene '{scid}'")
        for asp in assembly_data.get("assembly_shot_placements", []):
            tid = parse_uuid(asp.get("timeline_id"))
            if not tid or tid not in self.timeline_ids:
                raise ArchivePreflightError(f"AssemblyShotPlacement '{asp.get('id')}' references nonexistent Timeline '{tid}'")
            asid = parse_uuid(asp.get("assembly_scene_id"))
            if not asid or asid not in self.assembly_scene_ids:
                raise ArchivePreflightError(f"AssemblyShotPlacement '{asp.get('id')}' references nonexistent AssemblyScene '{asid}'")
            shid = parse_uuid(asp.get("shot_id"))
            if not shid or shid not in self.shot_ids:
                raise ArchivePreflightError(f"AssemblyShotPlacement '{asp.get('id')}' references nonexistent Shot '{shid}'")
            visual_asset_raw = asp.get("visual_asset_id") or asp.get("asset_id")
            if visual_asset_raw:
                aid = parse_uuid(visual_asset_raw)
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"AssemblyShotPlacement '{asp.get('id')}' references nonexistent Asset '{aid}'")
        for chk in assembly_data.get("checkpoints", []):
            tid = parse_uuid(chk.get("timeline_id"))
            if not tid or tid not in self.timeline_ids:
                raise ArchivePreflightError(f"TimelineCheckpoint '{chk.get('id')}' references nonexistent Timeline '{tid}'")

        # QC -> runs, findings, decisions, approvals
        for qr in qc_data.get("qc_runs", []):
            tid = parse_uuid(qr.get("timeline_id"))
            if not tid or tid not in self.timeline_ids:
                raise ArchivePreflightError(f"QCRun '{qr.get('id')}' references nonexistent Timeline '{tid}'")
        for qf in qc_data.get("qc_findings", []):
            qrid = parse_uuid(qf.get("qc_run_id"))
            if not qrid or qrid not in self.qc_run_ids:
                raise ArchivePreflightError(f"QCFinding '{qf.get('id')}' references nonexistent QCRun '{qrid}'")
        for wd in qc_data.get("warning_decisions", []):
            fid = parse_uuid(wd.get("finding_id"))
            if not fid or fid not in self.qc_finding_ids:
                raise ArchivePreflightError(f"WarningDecision '{wd.get('id')}' references nonexistent QCFinding '{fid}'")
        for app in qc_data.get("approvals", []):
            tid = parse_uuid(app.get("timeline_id"))
            if not tid or tid not in self.timeline_ids:
                raise ArchivePreflightError(f"ApprovalRecord '{app.get('id')}' references nonexistent Timeline '{tid}'")
            qrid = parse_uuid(app.get("qc_run_id"))
            if not qrid or qrid not in self.qc_run_ids:
                raise ArchivePreflightError(f"ApprovalRecord '{app.get('id')}' references nonexistent QCRun '{qrid}'")

        # Render Jobs
        for rb in rj_data.get("render_batches", []):
            tid = parse_uuid(rb.get("timeline_id"))
            if not tid or tid not in self.timeline_ids:
                raise ArchivePreflightError(f"RenderBatch '{rb.get('id')}' references nonexistent Timeline '{tid}'")
        for rj in rj_data.get("render_jobs", []):
            tid = parse_uuid(rj.get("timeline_id"))
            if not tid or tid not in self.timeline_ids:
                raise ArchivePreflightError(f"RenderJob '{rj.get('id')}' references nonexistent Timeline '{tid}'")
            if rj.get("approval_id"):
                appid = parse_uuid(rj["approval_id"])
                if not appid or appid not in self.approval_ids:
                    raise ArchivePreflightError(f"RenderJob '{rj.get('id')}' references nonexistent ApprovalRecord '{appid}'")
            if rj.get("batch_id"):
                bid = parse_uuid(rj["batch_id"])
                if not bid or bid not in self.render_batch_ids:
                    raise ArchivePreflightError(f"RenderJob '{rj.get('id')}' references nonexistent RenderBatch '{bid}'")
            if rj.get("output_asset_id"):
                aid = parse_uuid(rj["output_asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"RenderJob '{rj.get('id')}' references nonexistent output Asset '{aid}'")
            if rj.get("current_usage_ledger_id"):
                lid = parse_uuid(rj["current_usage_ledger_id"])
                if not lid or lid not in self.usage_ledger_ids:
                    raise ArchivePreflightError(f"RenderJob '{rj.get('id')}' references nonexistent UsageLedger '{lid}'")

        # Generation Jobs
        for gj in gj_data.get("generation_jobs", []):
            shid = parse_uuid(gj.get("shot_id"))
            if not shid or shid not in self.shot_ids:
                raise ArchivePreflightError(f"GenerationJob '{gj.get('id')}' references nonexistent Shot '{shid}'")
            if gj.get("output_asset_id"):
                aid = parse_uuid(gj["output_asset_id"])
                if not aid or aid not in self.asset_ids:
                    raise ArchivePreflightError(f"GenerationJob '{gj.get('id')}' references nonexistent output Asset '{aid}'")
        for bri in gj_data.get("batch_run_items", []):
            brid = parse_uuid(bri.get("batch_run_id"))
            if not brid or brid not in self.batch_run_ids:
                raise ArchivePreflightError(f"BatchRunItem '{bri.get('id')}' references nonexistent BatchRun '{brid}'")
            shid = parse_uuid(bri.get("shot_id"))
            if not shid or shid not in self.shot_ids:
                raise ArchivePreflightError(f"BatchRunItem '{bri.get('id')}' references nonexistent Shot '{shid}'")
            if bri.get("job_id"):
                jid = parse_uuid(bri["job_id"])
                if not jid or jid not in self.generation_job_ids:
                    raise ArchivePreflightError(f"BatchRunItem '{bri.get('id')}' references nonexistent GenerationJob '{jid}'")

        # Usage Ledger
        for ul in ul_data.get("entries", []):
            if ul.get("shot_id"):
                shid = parse_uuid(ul["shot_id"])
                if not shid or shid not in self.shot_ids:
                    raise ArchivePreflightError(f"UsageLedger '{ul.get('id')}' references nonexistent Shot '{shid}'")
            if ul.get("job_id"):
                jid = parse_uuid(ul["job_id"])
                if not jid or jid not in self.generation_job_ids:
                    raise ArchivePreflightError(f"UsageLedger '{ul.get('id')}' references nonexistent GenerationJob '{jid}'")
            if ul.get("render_job_id"):
                rjid = parse_uuid(ul["render_job_id"])
                if not rjid or rjid not in self.render_job_ids:
                    raise ArchivePreflightError(f"UsageLedger '{ul.get('id')}' references nonexistent RenderJob '{rjid}'")
        for adj in ul_data.get("adjustments", []):
            lid = parse_uuid(adj.get("ledger_id") or adj.get("ledger_entry_id"))
            if not lid or lid not in self.usage_ledger_ids:
                raise ArchivePreflightError(f"LedgerAdjustment '{adj.get('id')}' references nonexistent UsageLedger '{lid}'")

        # 6. Asset Completeness (Requirement 3)
        assets_manifest_raw = self._read_json("assets/manifest.json", required=True)
        if not isinstance(assets_manifest_raw, dict):
            raise ArchivePreflightError("assets/manifest.json must contain a JSON object catalog")

        for a_raw in assets_data:
            aid_str = str(a_raw["id"])
            if aid_str not in assets_manifest_raw:
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' declared in assets.json has no entry in assets/manifest.json"
                )
            cat_entry = assets_manifest_raw[aid_str]
            rel_path = cat_entry.get("relative_path")
            if not rel_path:
                raise ArchivePreflightError(f"Asset '{aid_str}' catalog entry missing relative_path")

            payload_path = os.path.join(self.temp_dir, rel_path)
            if not os.path.isfile(payload_path):
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' binary payload missing at relative path '{rel_path}'"
                )

            actual_size = os.path.getsize(payload_path)
            cat_size = cat_entry.get("size_bytes")
            row_size = a_raw.get("file_size_bytes")
            if cat_size is None:
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' catalog entry missing size_bytes"
                )
            if actual_size != cat_size:
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' size mismatch: payload ({actual_size} bytes) != manifest ({cat_size} bytes)"
                )
            if row_size is not None and actual_size != row_size:
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' size mismatch: payload ({actual_size} bytes) != asset row ({row_size} bytes)"
                )

            actual_sha = ArchiveChecksumService.compute_sha256_file(payload_path)
            cat_sha = cat_entry.get("sha256")
            row_sha = a_raw.get("checksum_sha256")
            if cat_sha and actual_sha.lower() != cat_sha.lower():
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' checksum mismatch: payload ({actual_sha}) != manifest ({cat_sha})"
                )
            if row_sha and actual_sha.lower() != row_sha.lower():
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' checksum mismatch: payload ({actual_sha}) != asset row ({row_sha})"
                )

        # Check that manifest entries all correspond to declared assets
        for aid_str, cat_entry in assets_manifest_raw.items():
            aid = parse_uuid(aid_str)
            if not aid or aid not in self.asset_ids:
                raise ArchivePreflightError(
                    f"Asset '{aid_str}' in assets/manifest.json is not declared in entities/assets.json"
                )


class ProjectImportService:
    """Orchestrates safe validation and atomic execution of project imports."""

    def __init__(self, storage_provider: Optional[ObjectStorageProvider] = None):
        self.storage = storage_provider or get_storage_provider()

    def validate_project_archive(self, archive_path: str, db: Session) -> Dict[str, Any]:
        """Pre-flights an archive (Phases 1-3) without modifying the database or storage."""
        temp_dir = tempfile.mkdtemp(prefix="orbis_import_val_")
        try:
            # Phase 1: Security inspection & extraction
            zf = ArchiveSecurityValidator.inspect_archive(archive_path)
            try:
                for member in zf.infolist():
                    target = ArchiveSecurityValidator.resolve_safe_extraction_path(temp_dir, member.filename)
                    if member.filename.endswith("/"):
                        os.makedirs(target, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with zf.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            finally:
                zf.close()

            # Phase 2: Checksum verification
            _, manifest = ArchiveChecksumService.verify_sandbox_checksums(temp_dir)

            # Version check
            archive_version_str = manifest.get("archive_format_version", "1.0.0")
            major_ver = int(archive_version_str.split(".")[0])
            if major_ver not in SUPPORTED_MAJOR_VERSIONS:
                raise VersionIncompatibilityError(
                    f"Archive format version '{archive_version_str}' is not supported (supported: 1.x)"
                )

            # Phase 3: Canonical Graph & Asset Completeness Preflight
            preflight = ArchivePreflightValidator(temp_dir)
            preflight.validate_graph()

            # Collision check
            orig_proj_id_str = manifest.get("project", {}).get("original_project_id")
            orig_proj_id = parse_uuid(orig_proj_id_str)
            collision = False
            if orig_proj_id and db.get(Project, orig_proj_id):
                collision = True

            allowed_modes = ["CLONE"]
            if not collision:
                allowed_modes.append("RESTORE")

            return {
                "valid": True,
                "archive_format_version": archive_version_str,
                "schema_version": manifest.get("schema_version", "1.0.0"),
                "source_project_id": orig_proj_id_str,
                "title": manifest.get("project", {}).get("title"),
                "video_mode": manifest.get("project", {}).get("video_mode"),
                "entity_counts": manifest.get("entity_counts", {}),
                "assets_summary": manifest.get("assets_summary", {}),
                "collision_detected": collision,
                "allowed_modes": allowed_modes,
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def execute_import(
        self,
        db: Session,
        archive_path: str,
        import_mode: str = "CLONE",
        override_title: Optional[str] = None,
    ) -> Project:
        """Executes full import pipeline (Phases 1-4) with atomic rollback and compensation."""
        import_mode = import_mode.upper()
        if import_mode not in ("CLONE", "RESTORE"):
            raise ArchiveImportError(f"Invalid import mode '{import_mode}'. Must be 'CLONE' or 'RESTORE'.")

        archive_checksum = ArchiveChecksumService.compute_sha256_file(archive_path)
        temp_dir = tempfile.mkdtemp(prefix="orbis_import_exec_")

        try:
            # Phase 1: Security inspection & extraction
            zf = ArchiveSecurityValidator.inspect_archive(archive_path)
            try:
                for member in zf.infolist():
                    target = ArchiveSecurityValidator.resolve_safe_extraction_path(temp_dir, member.filename)
                    if member.filename.endswith("/"):
                        os.makedirs(target, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with zf.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            finally:
                zf.close()

            # Phase 2: Checksum verification
            _, manifest = ArchiveChecksumService.verify_sandbox_checksums(temp_dir)

            archive_version_str = manifest.get("archive_format_version", "1.0.0")
            major_ver = int(archive_version_str.split(".")[0])
            if major_ver not in SUPPORTED_MAJOR_VERSIONS:
                raise VersionIncompatibilityError(
                    f"Archive format version '{archive_version_str}' is not supported (supported: 1.x)"
                )

            # Phase 3: Project identity and collision validation
            orig_proj_id = parse_uuid(manifest.get("project", {}).get("original_project_id"))
            if not orig_proj_id:
                raise ArchiveImportError("Missing original_project_id in archive manifest")

            existing_project = db.get(Project, orig_proj_id)
            if import_mode == "RESTORE" and existing_project:
                raise ProjectCollisionError(
                    f"Cannot restore: project '{orig_proj_id}' already exists in database. "
                    "Use CLONE mode to import as a new project."
                )

            # Phase 3: Canonical Graph & Asset Completeness Preflight
            # Strictly executed BEFORE any DB or storage mutation
            preflight = ArchivePreflightValidator(temp_dir)
            preflight.validate_graph()

            # Phase 4: Staged DB mutation & storage upload
            return self._stage_and_commit(
                db=db,
                temp_dir=temp_dir,
                manifest=manifest,
                import_mode=import_mode,
                orig_proj_id=orig_proj_id,
                archive_checksum=archive_checksum,
                override_title=override_title,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _stage_and_commit(
        self,
        db: Session,
        temp_dir: str,
        manifest: Dict[str, Any],
        import_mode: str,
        orig_proj_id: uuid.UUID,
        archive_checksum: str,
        override_title: Optional[str],
    ) -> Project:
        remap = RemapContext(mode=import_mode, original_project_id=orig_proj_id)
        new_project_id = remap.new_project_id
        uploaded_storage_keys: List[Tuple[str, str]] = []

        try:
            # 1. Load project.json
            with open(os.path.join(temp_dir, "project.json"), "r", encoding="utf-8") as f:
                project_raw = json.load(f)

            title = override_title
            if not title:
                if import_mode == "CLONE":
                    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                    title = f"{project_raw.get('title', 'Project')} (Imported {date_str})"
                else:
                    title = project_raw.get("title", "Project")

            mode_config = project_raw.get("mode_config") or {}
            if import_mode == "CLONE":
                mode_config["clone_lineage"] = {
                    "source_project_id": str(orig_proj_id),
                    "source_archive_checksum": archive_checksum,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }

            imported_project = Project(
                id=new_project_id,
                title=title,
                description=project_raw.get("description"),
                status=project_raw.get("status", "DRAFT"),
                video_mode=project_raw.get("video_mode", "STORY"),
                automation_mode=project_raw.get("automation_mode", "MANUAL"),
                purpose=project_raw.get("purpose"),
                target_platform=project_raw.get("target_platform"),
                target_duration_seconds=project_raw.get("target_duration_seconds"),
                preferred_aspect_ratio=project_raw.get("preferred_aspect_ratio"),
                mode_config=mode_config,
                default_config=project_raw.get("default_config"),
                budget_limit=project_raw.get("budget_limit"),
                budget_currency=project_raw.get("budget_currency", "USD"),
                budget_threshold_percentage=project_raw.get("budget_threshold_percentage", 80.0),
                source_project_id=orig_proj_id if import_mode == "CLONE" else None,
                source_archive_checksum=archive_checksum,
                imported_at=datetime.now(timezone.utc),
                created_at=parse_datetime(project_raw.get("created_at")) or datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(imported_project)

            # 2. Upload and register Assets
            assets_manifest_path = os.path.join(temp_dir, "assets", "manifest.json")
            assets_catalog: Dict[str, Any] = {}
            if os.path.exists(assets_manifest_path):
                with open(assets_manifest_path, "r", encoding="utf-8") as f:
                    assets_catalog = json.load(f)

            assets_json_path = os.path.join(temp_dir, "entities", "assets.json")
            assets_raw: List[Dict[str, Any]] = []
            if os.path.exists(assets_json_path):
                with open(assets_json_path, "r", encoding="utf-8") as f:
                    assets_raw = json.load(f)

            bucket = settings.S3_BUCKET_NAME if hasattr(settings, "S3_BUCKET_NAME") and settings.S3_BUCKET_NAME else "orbis-studio-assets"

            for a_raw in assets_raw:
                old_aid = parse_uuid(a_raw["id"])
                new_aid = remap.get_or_create(old_aid, "ASSET")
                orig_filename = a_raw.get("original_filename", "asset.bin")

                # Fresh storage key
                new_storage_key = f"projects/{new_project_id}/assets/{new_aid}/{orig_filename}"

                # Upload binary if present in archive
                catalog_entry = assets_catalog.get(str(old_aid))
                if catalog_entry:
                    rel_data_path = catalog_entry["relative_path"]
                    local_binary_path = os.path.join(temp_dir, rel_data_path)
                    if os.path.exists(local_binary_path):
                        content_type = catalog_entry.get("content_type", "application/octet-stream")
                        self.storage.upload_file_object(bucket, new_storage_key, local_binary_path, content_type)
                        uploaded_storage_keys.append((bucket, new_storage_key))

                asset_record = Asset(
                    id=new_aid,
                    project_id=new_project_id,
                    name=a_raw.get("name", orig_filename),
                    original_filename=orig_filename,
                    asset_type=a_raw.get("asset_type", "REFERENCE"),
                    content_type=a_raw.get("content_type", "application/octet-stream"),
                    file_size_bytes=a_raw.get("file_size_bytes", 0),
                    checksum_sha256=a_raw.get("checksum_sha256", ""),
                    storage_bucket=bucket,
                    storage_key=new_storage_key,
                    is_locked=a_raw.get("is_locked", False),
                    created_at=parse_datetime(a_raw.get("created_at")) or datetime.now(timezone.utc),
                    updated_at=parse_datetime(a_raw.get("updated_at")) or datetime.now(timezone.utc),
                )
                db.add(asset_record)

            # 3. Document Extractions
            doc_ext_path = os.path.join(temp_dir, "entities", "document_extractions.json")
            if os.path.exists(doc_ext_path):
                with open(doc_ext_path, "r", encoding="utf-8") as f:
                    docs = json.load(f)
                for d in docs:
                    db.add(DocumentExtraction(
                        id=remap.get_or_create(parse_uuid(d["id"]), "DOCUMENT_EXTRACTION"),
                        asset_id=remap.get_or_create(parse_uuid(d["asset_id"]), "ASSET"),
                        raw_text=d.get("raw_text", ""),
                        segments=d.get("segments"),
                        character_count=d.get("character_count", 0),
                        token_count=d.get("token_count", 0),
                        created_at=parse_datetime(d.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 4. Story & Story Versions
            story_path = os.path.join(temp_dir, "entities", "story.json")
            if os.path.exists(story_path):
                with open(story_path, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                story_raw = s_data.get("story")
                if story_raw:
                    old_sid = parse_uuid(story_raw["id"])
                    new_sid = remap.get_or_create(old_sid, "STORY")
                    db.add(Story(
                        id=new_sid,
                        project_id=new_project_id,
                        title=story_raw.get("title", ""),
                        premise=story_raw.get("premise"),
                        synopsis=story_raw.get("synopsis"),
                        target_duration=story_raw.get("target_duration"),
                        target_audience=story_raw.get("target_audience"),
                        visual_style=story_raw.get("visual_style"),
                        logline=story_raw.get("logline"),
                        version_number=story_raw.get("version_number", 1),
                        status=story_raw.get("status", "DRAFT"),
                        is_locked=story_raw.get("is_locked", False),
                        created_at=parse_datetime(story_raw.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(story_raw.get("updated_at")) or datetime.now(timezone.utc),
                    ))

                for sv in s_data.get("story_versions", []):
                    db.add(StoryVersion(
                        id=remap.get_or_create(parse_uuid(sv["id"]), "STORY_VERSION"),
                        story_id=remap.get_or_create(parse_uuid(sv["story_id"]), "STORY"),
                        project_id=new_project_id,
                        version_number=sv.get("version_number", 1),
                        title=sv.get("title", ""),
                        logline=sv.get("logline"),
                        synopsis=sv.get("synopsis"),
                        character_profiles=sv.get("character_profiles"),
                        world_setting=sv.get("world_setting"),
                        style_rules=sv.get("style_rules"),
                        status=sv.get("status", "SUPERSEDED"),
                        created_at=parse_datetime(sv.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 5. Scenes
            scenes_path = os.path.join(temp_dir, "entities", "scenes.json")
            if os.path.exists(scenes_path):
                with open(scenes_path, "r", encoding="utf-8") as f:
                    scenes_raw = json.load(f)
                for sc in scenes_raw:
                    old_scid = parse_uuid(sc["id"])
                    new_scid = remap.get_or_create(old_scid, "SCENE")
                    db.add(Scene(
                        id=new_scid,
                        story_id=remap.get_or_create(parse_uuid(sc.get("story_id")), "STORY"),
                        project_id=new_project_id if sc.get("project_id") else None,
                        scene_number=sc.get("scene_number", 1),
                        heading=sc.get("heading"),
                        description=sc.get("description") or sc.get("summary"),
                        purpose=sc.get("purpose") or sc.get("narrative_intent"),
                        setting=sc.get("setting"),
                        duration_seconds=sc.get("duration_seconds") or sc.get("estimated_duration_seconds"),
                        narration=sc.get("narration"),
                        dialogue=sc.get("dialogue"),
                        scene_config=sc.get("scene_config"),
                        is_locked=sc.get("is_locked", False),
                        created_at=parse_datetime(sc.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(sc.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 6. Shots
            shots_path = os.path.join(temp_dir, "entities", "shots.json")
            if os.path.exists(shots_path):
                with open(shots_path, "r", encoding="utf-8") as f:
                    shots_raw = json.load(f)
                for sh in shots_raw:
                    old_shid = parse_uuid(sh["id"])
                    new_shid = remap.get_or_create(old_shid, "SHOT")
                    db.add(Shot(
                        id=new_shid,
                        scene_id=remap.get_or_create(parse_uuid(sh.get("scene_id")), "SCENE"),
                        shot_number=sh.get("shot_number", 1),
                        shot_type=sh.get("shot_type", "AI_GENERATED"),
                        camera=sh.get("camera") or sh.get("camera_movement"),
                        subject=sh.get("subject"),
                        action=sh.get("action"),
                        duration_seconds=float(sh.get("duration_seconds") or 4.0),
                        visual_prompt=sh.get("visual_prompt"),
                        image_prompt=sh.get("image_prompt"),
                        video_prompt=sh.get("video_prompt"),
                        source_asset_id=remap.get_or_create(parse_uuid(sh.get("source_asset_id")), "ASSET"),
                        keyframe_asset_id=remap.get_or_create(parse_uuid(sh.get("keyframe_asset_id")), "ASSET"),
                        source_metadata=sh.get("source_metadata"),
                        provider_config=sh.get("provider_config"),
                        status=sh.get("status", "DRAFT"),
                        is_locked=sh.get("is_locked", False),
                        created_at=parse_datetime(sh.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(sh.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 7. Reference Library
            ref_path = os.path.join(temp_dir, "entities", "reference_library.json")
            if os.path.exists(ref_path):
                with open(ref_path, "r", encoding="utf-8") as f:
                    ref_data = json.load(f)
                for pr in ref_data.get("project_references", []):
                    db.add(ProjectReference(
                        id=remap.get_or_create(parse_uuid(pr["id"]), "PROJECT_REFERENCE"),
                        project_id=new_project_id,
                        asset_id=remap.get_or_create(parse_uuid(pr["asset_id"]), "ASSET"),
                        category=pr.get("category", "OTHER"),
                        tags=pr.get("tags"),
                        meta_info=pr.get("meta_info"),
                        created_at=parse_datetime(pr.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for cb in ref_data.get("character_bibles", []):
                    db.add(CharacterBible(
                        id=remap.get_or_create(parse_uuid(cb["id"]), "CHARACTER_BIBLE"),
                        project_id=new_project_id,
                        name=cb.get("name", ""),
                        description=cb.get("description"),
                        prompt_triggers=cb.get("prompt_triggers"),
                        reference_asset_ids=[str(remap.get_or_create(parse_uuid(aid), "ASSET")) for aid in (cb.get("reference_asset_ids") or [])],
                        negative_prompt_triggers=cb.get("negative_prompt_triggers"),
                        is_locked=cb.get("is_locked", False),
                        created_at=parse_datetime(cb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(cb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for lb in ref_data.get("location_bibles", []):
                    db.add(LocationBible(
                        id=remap.get_or_create(parse_uuid(lb["id"]), "LOCATION_BIBLE"),
                        project_id=new_project_id,
                        name=lb.get("name", ""),
                        description=lb.get("description"),
                        prompt_triggers=lb.get("prompt_triggers"),
                        reference_asset_ids=[str(remap.get_or_create(parse_uuid(aid), "ASSET")) for aid in (lb.get("reference_asset_ids") or [])],
                        negative_prompt_triggers=lb.get("negative_prompt_triggers"),
                        is_locked=lb.get("is_locked", False),
                        created_at=parse_datetime(lb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(lb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for sb in ref_data.get("style_bibles", []):
                    db.add(StyleBible(
                        id=remap.get_or_create(parse_uuid(sb["id"]), "STYLE_BIBLE"),
                        project_id=new_project_id,
                        style_name=sb.get("style_name", ""),
                        description=sb.get("description"),
                        prompt_preset=sb.get("prompt_preset"),
                        negative_prompt_preset=sb.get("negative_prompt_preset"),
                        reference_asset_ids=[str(remap.get_or_create(parse_uuid(aid), "ASSET")) for aid in (sb.get("reference_asset_ids") or [])],
                        is_locked=sb.get("is_locked", False),
                        created_at=parse_datetime(sb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(sb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for bb in ref_data.get("brand_bibles", []):
                    db.add(BrandBible(
                        id=remap.get_or_create(parse_uuid(bb["id"]), "BRAND_BIBLE"),
                        project_id=new_project_id,
                        brand_name=bb.get("brand_name", ""),
                        guidelines=bb.get("guidelines"),
                        logo_asset_id=remap.get_or_create(parse_uuid(bb.get("logo_asset_id")), "ASSET"),
                        colors=bb.get("colors"),
                        typography=bb.get("typography"),
                        is_locked=bb.get("is_locked", False),
                        created_at=parse_datetime(bb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(bb.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 8. Asset Locks (Polymorphic entity_id remapping)
            locks_path = os.path.join(temp_dir, "entities", "asset_locks.json")
            if os.path.exists(locks_path):
                with open(locks_path, "r", encoding="utf-8") as f:
                    locks_raw = json.load(f)
                for lk in locks_raw:
                    ent_type = lk.get("entity_type", "")
                    old_eid = parse_uuid(lk.get("entity_id"))
                    new_eid = remap.remap_polymorphic(ent_type, old_eid)
                    db.add(AssetLock(
                        id=remap.get_or_create(parse_uuid(lk["id"]), "ASSET_LOCK"),
                        project_id=new_project_id,
                        entity_type=ent_type,
                        entity_id=new_eid,
                        is_locked=lk.get("is_locked", True),
                        locked_by=lk.get("locked_by", "system"),
                        lock_reason=lk.get("lock_reason") or lk.get("reason"),
                        created_at=parse_datetime(lk.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 9. Audio Plan & Clips
            audio_path = os.path.join(temp_dir, "entities", "audio.json")
            if os.path.exists(audio_path):
                with open(audio_path, "r", encoding="utf-8") as f:
                    aud = json.load(f)
                for ap in aud.get("audio_plans", []):
                    db.add(AudioPlan(
                        id=remap.get_or_create(parse_uuid(ap["id"]), "AUDIO_PLAN"),
                        project_id=new_project_id,
                        status=ap.get("status", "DRAFT"),
                        plan_data=ap.get("plan_data"),
                        version=ap.get("version", ap.get("version_number", 1)),
                        created_at=parse_datetime(ap.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ap.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for apv in aud.get("audio_plan_versions", []):
                    db.add(AudioPlanVersion(
                        id=remap.get_or_create(parse_uuid(apv["id"]), "AUDIO_PLAN_VERSION"),
                        audio_plan_id=remap.get_or_create(parse_uuid(apv["audio_plan_id"]), "AUDIO_PLAN"),
                        project_id=new_project_id,
                        version_number=apv.get("version_number", 1),
                        status=apv.get("status", "DRAFT"),
                        plan_data=apv.get("plan_data"),
                        actor=apv.get("actor", "USER"),
                        action=apv.get("action", "CREATE"),
                        change_reason=apv.get("change_reason"),
                        created_at=parse_datetime(apv.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for ac in aud.get("audio_clips", []):
                    db.add(AudioClip(
                        id=remap.get_or_create(parse_uuid(ac["id"]), "AUDIO_CLIP"),
                        project_id=new_project_id,
                        scene_id=remap.get_or_create(parse_uuid(ac.get("scene_id")), "SCENE"),
                        shot_id=remap.get_or_create(parse_uuid(ac.get("shot_id")), "SHOT"),
                        video_asset_id=remap.get_or_create(parse_uuid(ac.get("video_asset_id")), "ASSET"),
                        asset_id=remap.get_or_create(parse_uuid(ac.get("asset_id")), "ASSET"),
                        audio_type=ac.get("audio_type", "VO"),
                        source_type=ac.get("source_type", "IMPORTED_AUDIO"),
                        generation_mode=ac.get("generation_mode", "SEPARATE_AUDIO"),
                        scope=ac.get("scope", "PROJECT"),
                        name=ac.get("name", "clip"),
                        prompt=ac.get("prompt"),
                        start_time=float(ac.get("start_time", ac.get("timeline_start_seconds", 0.0)) or 0.0),
                        duration_seconds=ac.get("duration_seconds"),
                        volume=float(ac.get("volume", 1.0) or 0.0),
                        mute=bool(ac.get("mute", ac.get("is_muted", False))),
                        fade_in=float(ac.get("fade_in", 0.0) or 0.0),
                        fade_out=float(ac.get("fade_out", 0.0) or 0.0),
                        ducking_role=ac.get("ducking_role", "BACKGROUND"),
                        ducking_amount_db=float(ac.get("ducking_amount_db", -12.0) or 0.0),
                        language=ac.get("language"),
                        speaker=ac.get("speaker"),
                        is_locked=bool(ac.get("is_locked", False)),
                        version=int(ac.get("version", 1) or 1),
                        provenance=ac.get("provenance"),
                        status=ac.get("status", "PENDING"),
                        created_at=parse_datetime(ac.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ac.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for ach in aud.get("audio_clip_histories", []):
                    raw_clip_id = ach.get("clip_id") or ach.get("audio_clip_id")
                    db.add(AudioClipHistory(
                        id=remap.get_or_create(parse_uuid(ach["id"]), "AUDIO_CLIP_HISTORY"),
                        clip_id=remap.get_or_create(parse_uuid(raw_clip_id), "AUDIO_CLIP"),
                        project_id=new_project_id,
                        version_number=int(ach.get("version_number", ach.get("iteration_number", 1)) or 1),
                        audio_type=ach.get("audio_type", "VO"),
                        source_type=ach.get("source_type", "IMPORTED_AUDIO"),
                        generation_mode=ach.get("generation_mode", "SEPARATE_AUDIO"),
                        scope=ach.get("scope", "PROJECT"),
                        name=ach.get("name", "clip"),
                        prompt=ach.get("prompt"),
                        start_time=float(ach.get("start_time", ach.get("timeline_start_seconds", 0.0)) or 0.0),
                        duration_seconds=ach.get("duration_seconds"),
                        volume=float(ach.get("volume", 1.0) or 0.0),
                        mute=bool(ach.get("mute", ach.get("is_muted", False))),
                        fade_in=float(ach.get("fade_in", 0.0) or 0.0),
                        fade_out=float(ach.get("fade_out", 0.0) or 0.0),
                        ducking_role=ach.get("ducking_role", "BACKGROUND"),
                        ducking_amount_db=float(ach.get("ducking_amount_db", -12.0) or 0.0),
                        language=ach.get("language"),
                        speaker=ach.get("speaker"),
                        is_locked=bool(ach.get("is_locked", False)),
                        status=ach.get("status", "PENDING"),
                        asset_id=remap.get_or_create(parse_uuid(ach.get("asset_id")), "ASSET"),
                        provenance=ach.get("provenance"),
                        actor=ach.get("actor", "USER"),
                        action=ach.get("action", "CREATE"),
                        change_reason=ach.get("change_reason"),
                        created_at=parse_datetime(ach.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 10. Timelines & Assembly
            assembly_path = os.path.join(temp_dir, "entities", "assembly.json")
            if os.path.exists(assembly_path):
                with open(assembly_path, "r", encoding="utf-8") as f:
                    asm = json.load(f)
                for tm in asm.get("timelines", []):
                    db.add(AssemblyTimeline(
                        id=remap.get_or_create(parse_uuid(tm["id"]), "TIMELINE"),
                        project_id=new_project_id,
                        version=tm.get("version", 1),
                        is_active=tm.get("is_active", False),
                        status=tm.get("status", "DRAFT"),
                        subtitle_state=tm.get("subtitle_state"),
                        created_at=parse_datetime(tm.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(tm.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for asc in asm.get("assembly_scenes", []):
                    db.add(AssemblyScene(
                        id=remap.get_or_create(parse_uuid(asc["id"]), "ASSEMBLY_SCENE"),
                        timeline_id=remap.get_or_create(parse_uuid(asc["timeline_id"]), "TIMELINE"),
                        scene_id=remap.get_or_create(parse_uuid(asc["scene_id"]), "SCENE"),
                        scene_order=asc.get("scene_order", 0),
                        created_at=parse_datetime(asc.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(asc.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for asp in asm.get("assembly_shot_placements", []):
                    visual_raw = asp.get("visual_asset_id") or asp.get("asset_id")
                    db.add(AssemblyShotPlacement(
                        id=remap.get_or_create(parse_uuid(asp["id"]), "ASSEMBLY_SHOT_PLACEMENT"),
                        timeline_id=remap.get_or_create(parse_uuid(asp["timeline_id"]), "TIMELINE"),
                        assembly_scene_id=remap.get_or_create(parse_uuid(asp["assembly_scene_id"]), "ASSEMBLY_SCENE"),
                        scene_id=remap.get_or_create(parse_uuid(asp.get("scene_id")), "SCENE"),
                        shot_id=remap.get_or_create(parse_uuid(asp["shot_id"]), "SHOT"),
                        shot_order=int(asp.get("shot_order", asp.get("placement_order", 0)) or 0),
                        visual_asset_id=remap.get_or_create(parse_uuid(visual_raw), "ASSET"),
                        source_type=asp.get("source_type", "VIDEO"),
                        trim_in=float(asp.get("trim_in", asp.get("trim_in_seconds", 0.0)) or 0.0),
                        trim_out=asp.get("trim_out", asp.get("trim_out_seconds")),
                        effective_duration=float(asp.get("effective_duration", asp.get("duration_seconds", 4.0)) or 4.0),
                        still_duration=float(asp.get("still_duration", 4.0) or 4.0),
                        transition_to_next=asp.get("transition_to_next", asp.get("transition_type", "CUT")),
                        is_locked=bool(asp.get("is_locked", False)),
                        version=int(asp.get("version", 1) or 1),
                        created_at=parse_datetime(asp.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(asp.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for chk in asm.get("checkpoints", []):
                    db.add(TimelineCheckpoint(
                        id=remap.get_or_create(parse_uuid(chk["id"]), "TIMELINE_CHECKPOINT"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(chk["timeline_id"]), "TIMELINE"),
                        checkpoint_number=int(chk.get("checkpoint_number", 1) or 1),
                        label=chk.get("label", "checkpoint"),
                        snapshot_data=chk.get("snapshot_data", chk.get("checkpoint_data", {})),
                        actor=chk.get("actor", "system"),
                        created_at=parse_datetime(chk.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 11. QC & Approvals
            qc_path = os.path.join(temp_dir, "entities", "qc.json")
            if os.path.exists(qc_path):
                with open(qc_path, "r", encoding="utf-8") as f:
                    qcd = json.load(f)
                for qr in qcd.get("qc_runs", []):
                    db.add(QCRun(
                        id=remap.get_or_create(parse_uuid(qr["id"]), "QC_RUN"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(qr["timeline_id"]), "TIMELINE"),
                        timeline_version=qr.get("timeline_version", 1),
                        status=qr.get("status", "PASSED"),
                        blocker_count=qr.get("blocker_count", 0),
                        warning_count=qr.get("warning_count", 0),
                        actor=qr.get("actor", "system"),
                        created_at=parse_datetime(qr.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(qr.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for qf in qcd.get("qc_findings", []):
                    target_type = qf.get("target_type") or qf.get("entity_type")
                    target_raw = qf.get("target_id") or qf.get("entity_id")
                    db.add(QCFinding(
                        id=remap.get_or_create(parse_uuid(qf["id"]), "QC_FINDING"),
                        project_id=new_project_id,
                        qc_run_id=remap.get_or_create(parse_uuid(qf["qc_run_id"]), "QC_RUN"),
                        timeline_id=remap.get_or_create(parse_uuid(qf.get("timeline_id")), "TIMELINE"),
                        rule_code=qf.get("rule_code", ""),
                        severity=qf.get("severity", "WARNING"),
                        message=qf.get("message", ""),
                        why_it_matters=qf.get("why_it_matters"),
                        recommended_fix=qf.get("recommended_fix"),
                        target_type=target_type,
                        target_id=remap.remap_polymorphic(target_type or "", parse_uuid(target_raw)),
                        target_label=qf.get("target_label"),
                        action_type=qf.get("action_type"),
                        created_at=parse_datetime(qf.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for wd in qcd.get("warning_decisions", []):
                    db.add(WarningDecision(
                        id=remap.get_or_create(parse_uuid(wd["id"]), "WARNING_DECISION"),
                        project_id=new_project_id,
                        qc_run_id=remap.get_or_create(parse_uuid(wd.get("qc_run_id")), "QC_RUN"),
                        finding_id=remap.get_or_create(parse_uuid(wd["finding_id"]), "QC_FINDING"),
                        timeline_id=remap.get_or_create(parse_uuid(wd.get("timeline_id")), "TIMELINE"),
                        decision=wd.get("decision", "ACCEPTED_WITH_REASON"),
                        reason=wd.get("reason"),
                        actor=wd.get("actor", wd.get("decided_by", "USER")),
                        decided_at=parse_datetime(wd.get("decided_at") or wd.get("created_at")) or datetime.now(timezone.utc),
                        decision_sequence=int(wd.get("decision_sequence", 1) or 1),
                    ))
                for app in qcd.get("approvals", []):
                    db.add(ApprovalRecord(
                        id=remap.get_or_create(parse_uuid(app["id"]), "APPROVAL_RECORD"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(app["timeline_id"]), "TIMELINE"),
                        timeline_version=app.get("timeline_version", 1),
                        qc_run_id=remap.get_or_create(parse_uuid(app["qc_run_id"]), "QC_RUN"),
                        status=app.get("status", "APPROVED"),
                        actor=app.get("actor") or app.get("approved_by", "USER"),
                        notes=app.get("notes"),
                        approved_at=parse_datetime(app.get("approved_at")) or datetime.now(timezone.utc),
                    ))

            # 12. Render Batches & Render Jobs (PRESERVE STATUS, FENCE WITH imported_historical=True)
            rj_path = os.path.join(temp_dir, "entities", "render_jobs.json")
            if os.path.exists(rj_path):
                with open(rj_path, "r", encoding="utf-8") as f:
                    rjd = json.load(f)
                for rb in rjd.get("render_batches", []):
                    db.add(RenderBatch(
                        id=remap.get_or_create(parse_uuid(rb["id"]), "RENDER_BATCH"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(rb["timeline_id"]), "TIMELINE"),
                        timeline_version=rb.get("timeline_version", 1),
                        status=rb.get("status", "COMPLETED"),
                        total_variants=rb.get("total_variants", 1),
                        completed_variants=rb.get("completed_variants", 1),
                        failed_variants=rb.get("failed_variants", 0),
                        estimated_total_cost_usd=rb.get("estimated_total_cost_usd", 0.0),
                        created_at=parse_datetime(rb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(rb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for rj in rjd.get("render_jobs", []):
                    # Preserve original status and values, clear worker leases and tag historical
                    db.add(RenderJob(
                        id=remap.get_or_create(parse_uuid(rj["id"]), "RENDER_JOB"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(rj["timeline_id"]), "TIMELINE"),
                        timeline_version=rj.get("timeline_version", 1),
                        approval_id=remap.get_or_create(parse_uuid(rj.get("approval_id")), "APPROVAL_RECORD"),
                        batch_id=remap.get_or_create(parse_uuid(rj.get("batch_id")), "RENDER_BATCH"),
                        render_profile=rj.get("render_profile", "MASTER_HD"),
                        render_variant_key=rj.get("render_variant_key", "MASTER"),
                        status=rj.get("status", "COMPLETED"),
                        idempotency_key=rj["idempotency_key"],
                        output_asset_id=remap.get_or_create(parse_uuid(rj.get("output_asset_id")), "ASSET"),
                        progress=float(rj.get("progress", 1.0)),
                        claimed_by=None,
                        claim_token=None,
                        claim_expires_at=None,
                        retry_count=rj.get("retry_count", 0),
                        max_retries=rj.get("max_retries", 3),
                        estimated_cost_usd=float(rj.get("estimated_cost_usd", 0.0)),
                        actual_cost_usd=float(rj["actual_cost_usd"]) if rj.get("actual_cost_usd") is not None else None,
                        error_message=rj.get("error_message"),
                        current_usage_ledger_id=remap.get_or_create(parse_uuid(rj.get("current_usage_ledger_id")), "USAGE_LEDGER") if rj.get("current_usage_ledger_id") else None,
                        render_metadata=rj.get("render_metadata"),
                        imported_historical=True,
                        execution_disabled=True,
                        created_at=parse_datetime(rj.get("created_at")) or datetime.now(timezone.utc),
                        started_at=parse_datetime(rj.get("started_at")),
                        completed_at=parse_datetime(rj.get("completed_at")),
                        updated_at=parse_datetime(rj.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 13. Generation Jobs & Batch Runs (PRESERVE STATUS, FENCE WITH imported_historical=True)
            gj_path = os.path.join(temp_dir, "entities", "generation_jobs.json")
            if os.path.exists(gj_path):
                with open(gj_path, "r", encoding="utf-8") as f:
                    gjd = json.load(f)
                for gj in gjd.get("generation_jobs", []):
                    db.add(GenerationJob(
                        id=remap.get_or_create(parse_uuid(gj["id"]), "GENERATION_JOB"),
                        shot_id=remap.get_or_create(parse_uuid(gj["shot_id"]), "SHOT"),
                        job_type=gj.get("job_type", "VIDEO"),
                        provider_name=gj.get("provider_name", "vidu"),
                        provider_job_id=gj.get("provider_job_id"),
                        status=gj.get("status", "COMPLETED"),
                        idempotency_key=gj.get("idempotency_key"),
                        cost_usd=float(gj["cost_usd"]) if gj.get("cost_usd") is not None else None,
                        error_message=gj.get("error_message"),
                        retry_count=gj.get("retry_count", 0),
                        max_retries=gj.get("max_retries", 3),
                        poll_count=gj.get("poll_count", 0),
                        max_polls=gj.get("max_polls", 60),
                        claimed_by=None,
                        claim_token=None,
                        claim_expires_at=None,
                        next_retry_at=parse_datetime(gj.get("next_retry_at")),
                        next_poll_at=parse_datetime(gj.get("next_poll_at")),
                        submission_attempt_id=gj.get("submission_attempt_id"),
                        payload=gj.get("payload"),
                        result=gj.get("result"),
                        output_asset_id=remap.get_or_create(parse_uuid(gj.get("output_asset_id")), "ASSET"),
                        imported_historical=True,
                        execution_disabled=True,
                        created_at=parse_datetime(gj.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(gj.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for br in gjd.get("batch_runs", []):
                    db.add(BatchRun(
                        id=remap.get_or_create(parse_uuid(br["id"]), "BATCH_RUN"),
                        project_id=new_project_id,
                        total_shots=br.get("total_shots", 0),
                        dispatched_shots=br.get("dispatched_shots", 0),
                        skipped_shots=br.get("skipped_shots", 0),
                        failed_shots=br.get("failed_shots", 0),
                        created_at=parse_datetime(br.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for bri in gjd.get("batch_run_items", []):
                    db.add(BatchRunItem(
                        id=remap.get_or_create(parse_uuid(bri["id"]), "BATCH_RUN_ITEM"),
                        batch_run_id=remap.get_or_create(parse_uuid(bri["batch_run_id"]), "BATCH_RUN"),
                        shot_id=remap.get_or_create(parse_uuid(bri["shot_id"]), "SHOT"),
                        job_id=remap.get_or_create(parse_uuid(bri.get("job_id")), "GENERATION_JOB"),
                        status=bri.get("status", "DISPATCHED"),
                        skip_reason=bri.get("skip_reason"),
                        created_at=parse_datetime(bri.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 14. Usage Ledger & Adjustments (PRESERVE COSTS, FENCE WITH imported_historical=True)
            ul_path = os.path.join(temp_dir, "history", "usage_ledger.json")
            if os.path.exists(ul_path):
                with open(ul_path, "r", encoding="utf-8") as f:
                    uld = json.load(f)
                for ul in uld.get("entries", []):
                    db.add(UsageLedger(
                        id=remap.get_or_create(parse_uuid(ul["id"]), "USAGE_LEDGER"),
                        project_id=new_project_id,
                        shot_id=remap.get_or_create(parse_uuid(ul.get("shot_id")), "SHOT"),
                        job_id=remap.get_or_create(parse_uuid(ul.get("job_id")), "GENERATION_JOB"),
                        render_job_id=remap.get_or_create(parse_uuid(ul.get("render_job_id")), "RENDER_JOB"),
                        provider=ul.get("provider", "vidu"),
                        operation=ul.get("operation", "VIDEO_GENERATION"),
                        model=ul.get("model"),
                        usage_units=ul.get("usage_units"),
                        estimated_cost=float(ul["estimated_cost"]) if ul.get("estimated_cost") is not None else None,
                        actual_cost=float(ul["actual_cost"]) if ul.get("actual_cost") is not None else None,
                        currency=ul.get("currency", "USD"),
                        cost_status=ul.get("cost_status", "CONFIRMED"),
                        provider_event_id=ul.get("provider_event_id"),
                        idempotency_key=ul.get("idempotency_key"),
                        description=ul.get("description"),
                        imported_historical=True,
                        created_at=parse_datetime(ul.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ul.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for adj in uld.get("adjustments", []):
                    db.add(LedgerAdjustment(
                        id=remap.get_or_create(parse_uuid(adj["id"]), "LEDGER_ADJUSTMENT"),
                        ledger_id=remap.get_or_create(parse_uuid(adj.get("ledger_id") or adj.get("ledger_entry_id")), "USAGE_LEDGER"),
                        previous_cost=adj.get("previous_cost") or adj.get("previous_actual_cost", 0.0),
                        adjusted_cost=adj.get("adjusted_cost") or adj.get("new_actual_cost", 0.0),
                        reason=adj.get("reason", "Imported historical adjustment"),
                        actor=adj.get("actor") or adj.get("adjusted_by", "system"),
                        created_at=parse_datetime(adj.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 15. History & Audits
            oa_path = os.path.join(temp_dir, "history", "orchestration_audit.json")
            if os.path.exists(oa_path):
                with open(oa_path, "r", encoding="utf-8") as f:
                    oas = json.load(f)
                for oa in oas:
                    db.add(OrchestrationAudit(
                        id=remap.get_or_create(parse_uuid(oa["id"]), "ORCHESTRATION_AUDIT"),
                        project_id=new_project_id,
                        from_state=oa.get("from_state", oa.get("from_stage", "DRAFT")),
                        to_state=oa.get("to_state", oa.get("to_stage")),
                        action=oa.get("action", oa.get("event_type", "IMPORTED_EVENT")),
                        actor=oa.get("actor", "SYSTEM"),
                        result=oa.get("result", "APPLIED"),
                        reason_code=oa.get("reason_code"),
                        detail=oa.get("detail"),
                        created_at=parse_datetime(oa.get("created_at")) or datetime.now(timezone.utc),
                    ))

            ga_path = os.path.join(temp_dir, "history", "generation_audit.json")
            if os.path.exists(ga_path):
                with open(ga_path, "r", encoding="utf-8") as f:
                    gas = json.load(f)
                for ga in gas:
                    db.add(GenerationAuditLog(
                        id=remap.get_or_create(parse_uuid(ga["id"]), "GENERATION_AUDIT_LOG"),
                        project_id=new_project_id,
                        shot_id=remap.get_or_create(parse_uuid(ga.get("shot_id")), "SHOT"),
                        provider_name=ga.get("provider_name", "vidu"),
                        operation=ga.get("operation", "VIDEO"),
                        status=ga.get("status", "SUCCESS"),
                        latency_ms=ga.get("latency_ms"),
                        tokens_used=ga.get("tokens_used"),
                        request_payload=ga.get("request_payload"),
                        response_payload=ga.get("response_payload"),
                        created_at=parse_datetime(ga.get("created_at")) or datetime.now(timezone.utc),
                    ))

            ta_path = os.path.join(temp_dir, "history", "timeline_audits.json")
            if os.path.exists(ta_path):
                with open(ta_path, "r", encoding="utf-8") as f:
                    tas = json.load(f)
                for ta in tas:
                    db.add(TimelineAudit(
                        id=remap.get_or_create(parse_uuid(ta["id"]), "TIMELINE_AUDIT"),
                        timeline_id=remap.get_or_create(parse_uuid(ta["timeline_id"]), "TIMELINE"),
                        action=ta.get("action", "UPDATE"),
                        details=ta.get("details"),
                        created_at=parse_datetime(ta.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # Commit the atomic transaction
            db.commit()
            db.refresh(imported_project)
            logger.info(f"Successfully imported project '{imported_project.id}' in mode {import_mode}")
            return imported_project

        except Exception as e:
            db.rollback()
            logger.error(f"Import failed during staged execution: {str(e)}. Compensating storage uploads...")
            # Storage compensation: purge newly uploaded S3 objects
            for b, k in uploaded_storage_keys:
                try:
                    self.storage.delete_object(b, k)
                except Exception as del_err:
                    logger.warning(f"Failed to delete compensated storage object '{k}' in bucket '{b}': {del_err}")
            raise ArchiveImportError(f"Import failed during staged execution: {str(e)}") from e
