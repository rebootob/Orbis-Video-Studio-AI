import io
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.asset_lock import AssetLock
from app.models.assembly import AssemblyTimeline
from app.models.qc import QCRun, ApprovalRecord
from app.models.render_batch import RenderBatch
from app.models.render_job import RenderJob
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger, LedgerAdjustment
from app.services.archive.constants import (
    ARCHIVE_FORMAT_VERSION,
    MAX_UNCOMPRESSED_BYTES,
    MAX_COMPRESSION_RATIO,
    MAX_FILE_COUNT,
)
from app.services.archive.security import ArchiveSecurityValidator, ArchiveSecurityError
from app.services.archive.checksums import (
    ArchiveChecksumService,
    ChecksumVerificationError,
    TamperedManifestError,
    TamperedPayloadError,
)
from app.services.archive.export_service import ProjectExportService, ArchiveExportError
from app.services.archive.import_service import (
    ProjectImportService,
    ArchiveImportError,
    ProjectCollisionError,
    VersionIncompatibilityError,
    ArchivePreflightError,
    ArchivePreflightValidator,
)
from app.services.budget import BudgetService
from app.services.job_dispatch import JobDispatchService
from app.services.render_job import RenderJobService
from app.services.storage.mock import InMemoryObjectStorageProvider


# ==========================================
# 1. Archive Security Tests
# ==========================================

def test_archive_security_path_traversal():
    """Archive with path traversal entries must be rejected immediately."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "w") as zf:
            zf.writestr("../evil.txt", b"malicious content")

    try:
        with pytest.raises(ArchiveSecurityError, match="traversal"):
            ArchiveSecurityValidator.inspect_archive(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_archive_security_absolute_paths():
    """Archive with absolute paths must be rejected."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "w") as zf:
            zf.writestr("/etc/passwd", b"root:x:0:0")

    try:
        with pytest.raises(ArchiveSecurityError, match="prohibited"):
            ArchiveSecurityValidator.inspect_archive(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_archive_security_drive_letter():
    """Archive with Windows drive letter must be rejected."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "w") as zf:
            zf.writestr("C:/Windows/System32/calc.exe", b"malware")

    try:
        with pytest.raises(ArchiveSecurityError, match="Drive-letter"):
            ArchiveSecurityValidator.inspect_archive(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_archive_security_forbidden_extension():
    """Archive containing executable/forbidden files must be rejected."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "w") as zf:
            zf.writestr("assets/script.sh", b"#!/bin/sh\nrm -rf /")

    try:
        with pytest.raises(ArchiveSecurityError, match="Forbidden file extension"):
            ArchiveSecurityValidator.inspect_archive(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_archive_security_bomb_ratio():
    """Archive with excessive compression ratio (> 10:1) must be rejected."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 50MB of zeroes compresses to < 100KB -> ratio > 500:1
            zf.writestr("manifest.json", b"\0" * (50 * 1024 * 1024))

    try:
        with pytest.raises(ArchiveSecurityError, match="Potential decompression bomb"):
            ArchiveSecurityValidator.inspect_archive(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_archive_security_magic_bytes():
    """Non-ZIP archive must be rejected by magic bytes inspection."""
    with tempfile.NamedTemporaryFile(suffix=".orbis", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"NOT A REAL ZIP FILE HEADER")
        tmp.flush()

    try:
        with pytest.raises(ArchiveSecurityError, match="Invalid archive signature"):
            ArchiveSecurityValidator.inspect_archive(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ==========================================
# 2. Checksums & Integrity Tests
# ==========================================

def test_canonical_json_determinism():
    """Canonical JSON formatting must produce byte-identical output regardless of key order."""
    d1 = {"z": 1, "a": {"y": 2, "b": 3}}
    d2 = {"a": {"b": 3, "y": 2}, "z": 1}
    b1 = ArchiveChecksumService.canonical_json_dumps(d1)
    b2 = ArchiveChecksumService.canonical_json_dumps(d2)
    assert b1 == b2


def test_non_circular_trust_root_and_tamper_detection():
    """Checksums must verify untampered archives and detect tampering in payload, manifest, or checksums."""
    temp_dir = tempfile.mkdtemp(prefix="test_chk_")
    try:
        os.makedirs(os.path.join(temp_dir, "assets"), exist_ok=True)
        payload_path = os.path.join(temp_dir, "assets", "test.mp4")
        with open(payload_path, "wb") as f:
            f.write(b"sample video bytes")

        payload_sha = ArchiveChecksumService.compute_sha256_file(payload_path)
        manifest = {
            "archive_format_version": "1.0.0",
            "schema_version": "1.0.0",
            "package_type": "FULL_SELF_CONTAINED",
            "project": {"original_project_id": str(uuid.uuid4()), "title": "Checksum Test"},
            "file_manifest": {
                "assets/test.mp4": {
                    "sha256": payload_sha,
                    "size_bytes": 18,
                }
            }
        }
        manifest_bytes = ArchiveChecksumService.canonical_json_dumps(manifest)
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "wb") as f:
            f.write(manifest_bytes)
        manifest_sha = ArchiveChecksumService.compute_sha256_file(manifest_path)

        checksums_bytes = ArchiveChecksumService.generate_checksums_content({
            "assets/test.mp4": payload_sha,
            "manifest.json": manifest_sha,
        })
        with open(os.path.join(temp_dir, "checksums.sha256"), "wb") as f:
            f.write(checksums_bytes)

        # 1. Untampered package passes
        verified, verified_manifest = ArchiveChecksumService.verify_sandbox_checksums(temp_dir)
        assert verified is True
        assert verified_manifest["project"]["title"] == "Checksum Test"

        # 2. Tamper payload -> fails closed
        with open(payload_path, "wb") as f:
            f.write(b"corrupted video bytes")
        with pytest.raises(TamperedPayloadError):
            ArchiveChecksumService.verify_sandbox_checksums(temp_dir)

        # Restore payload
        with open(payload_path, "wb") as f:
            f.write(b"sample video bytes")

        # 3. Tamper manifest -> fails closed
        with open(manifest_path, "wb") as f:
            f.write(b'{"tampered": true}')
        with pytest.raises(TamperedManifestError):
            ArchiveChecksumService.verify_sandbox_checksums(temp_dir)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ==========================================
# 3. Project Export & Secret Stripping Tests
# ==========================================

def test_project_export_success(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """Export must query and serialize project graph, include storage binaries, and strip secrets."""
    proj = Project(
        title="Cyberpunk Adventure",
        description="Full feature export test",
        video_mode="STORY",
        status="DRAFT",
        mode_config={"api_key": "sk-secret-token", "provider_url": "https://api.secret.internal"},
        default_config={"db_password": "super-secret-password"},
    )
    db_session.add(proj)
    db_session.flush()

    scene = Scene(project_id=proj.id, scene_number=1, heading="Scene 1")
    db_session.add(scene)
    db_session.flush()

    shot = Shot(scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED", status="DRAFT")
    db_session.add(shot)
    db_session.flush()

    storage_key = f"projects/{proj.id}/assets/sample.png"
    sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_data"
    mock_storage.put_object("default", storage_key, sample_bytes, "image/png")

    asset = Asset(
        project_id=proj.id,
        name="Keyframe 1",
        original_filename="sample.png",
        asset_type="KEYFRAME",
        content_type="image/png",
        file_size_bytes=len(sample_bytes),
        checksum_sha256=ArchiveChecksumService.compute_sha256_bytes(sample_bytes),
        storage_bucket="default",
        storage_key=storage_key,
    )
    db_session.add(asset)
    db_session.flush()

    lock = AssetLock(
        project_id=proj.id,
        entity_type="SHOT",
        entity_id=shot.id,
        is_locked=True,
    )
    db_session.add(lock)
    db_session.commit()

    export_service = ProjectExportService(storage_provider=mock_storage)
    archive_path, manifest = export_service.export_project(db=db_session, project_id=proj.id)

    try:
        assert os.path.exists(archive_path)
        assert manifest["project"]["title"] == "Cyberpunk Adventure"
        assert manifest["entity_counts"]["scenes"] == 1
        assert manifest["entity_counts"]["shots"] == 1
        assert manifest["entity_counts"]["assets"] == 1

        # Inspect stripped secrets
        proj_data = manifest["project"]
        assert "api_key" not in (proj_data.get("mode_config") or {})
        assert "db_password" not in (proj_data.get("default_config") or {})

        # Inspect ZIP contents
        with zipfile.ZipFile(archive_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "checksums.sha256" in names
            assert "assets/manifest.json" in names
            assert any(name.startswith("assets/data/") for name in names)
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)


def test_project_export_missing_asset_fails_closed(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """Export must fail closed if any binary asset listed in DB cannot be streamed from storage."""
    proj = Project(title="Missing Asset Proj", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()

    asset = Asset(
        project_id=proj.id,
        name="Missing Asset",
        original_filename="missing.png",
        asset_type="KEYFRAME",
        content_type="image/png",
        file_size_bytes=100,
        checksum_sha256="abc12345",
        storage_bucket="default",
        storage_key=f"projects/{proj.id}/assets/non_existent.png",
    )
    db_session.add(asset)
    db_session.commit()

    export_service = ProjectExportService(storage_provider=mock_storage)
    with pytest.raises(ArchiveExportError, match="missing from storage"):
        export_service.export_project(db=db_session, project_id=proj.id)


# ==========================================
# 4. Import CLONE & RESTORE Mode Tests
# ==========================================

def test_project_import_clone_mode(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """Import in CLONE mode must generate new UUIDs, remap FKs, copy storage objects, and set lineage."""
    orig_proj = Project(title="Original Cyberpunk", video_mode="STORY")
    db_session.add(orig_proj)
    db_session.flush()

    scene = Scene(project_id=orig_proj.id, scene_number=1, heading="Scene 1")
    db_session.add(scene)
    db_session.flush()

    shot = Shot(scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED", status="DRAFT")
    db_session.add(shot)
    db_session.flush()

    storage_key = f"projects/{orig_proj.id}/assets/sample.png"
    asset_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRcloned_sample"
    mock_storage.put_object("default", storage_key, asset_bytes, "image/png")

    asset = Asset(
        project_id=orig_proj.id,
        name="Sample Asset",
        original_filename="sample.png",
        asset_type="KEYFRAME",
        content_type="image/png",
        file_size_bytes=len(asset_bytes),
        checksum_sha256=ArchiveChecksumService.compute_sha256_bytes(asset_bytes),
        storage_bucket="default",
        storage_key=storage_key,
    )
    db_session.add(asset)
    db_session.flush()

    lock = AssetLock(
        project_id=orig_proj.id,
        entity_type="SHOT",
        entity_id=shot.id,
        is_locked=True,
    )
    db_session.add(lock)
    db_session.commit()

    export_service = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_service.export_project(db=db_session, project_id=orig_proj.id)

    try:
        import_service = ProjectImportService(storage_provider=mock_storage)

        # Preflight validation
        val_res = import_service.validate_project_archive(archive_path, db_session)
        assert val_res["valid"] is True
        assert val_res["collision_detected"] is True  # orig_proj still in DB
        assert val_res["allowed_modes"] == ["CLONE"]

        # Execute CLONE import
        cloned_proj = import_service.execute_import(
            db=db_session,
            archive_path=archive_path,
            import_mode="CLONE",
            override_title="Cloned Cyberpunk 2077",
        )

        assert cloned_proj.id != orig_proj.id
        assert cloned_proj.title == "Cloned Cyberpunk 2077"
        assert cloned_proj.source_project_id == orig_proj.id
        assert cloned_proj.source_archive_checksum is not None
        assert cloned_proj.imported_at is not None

        # Verify scenes and shots remapped
        cloned_scenes = db_session.query(Scene).filter(Scene.project_id == cloned_proj.id).all()
        assert len(cloned_scenes) == 1
        assert cloned_scenes[0].id != scene.id

        cloned_shots = db_session.query(Shot).filter(Shot.scene_id == cloned_scenes[0].id).all()
        assert len(cloned_shots) == 1
        assert cloned_shots[0].id != shot.id

        # Verify polymorphic lock remapped
        cloned_locks = db_session.query(AssetLock).filter(AssetLock.project_id == cloned_proj.id).all()
        assert len(cloned_locks) == 1
        assert cloned_locks[0].entity_id == cloned_shots[0].id

        # Verify storage key copied under new project ID and original intact
        cloned_assets = db_session.query(Asset).filter(Asset.project_id == cloned_proj.id).all()
        assert len(cloned_assets) == 1
        new_key = cloned_assets[0].storage_key
        assert new_key.startswith(f"projects/{cloned_proj.id}/")
        assert mock_storage.object_exists(cloned_assets[0].storage_bucket, new_key)
        assert mock_storage.object_exists("default", storage_key)  # original untouched
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)


def test_project_import_restore_mode_and_collision(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """Import in RESTORE mode preserves original IDs and fails with 409 on collision."""
    orig_proj = Project(title="Restore Test Proj", video_mode="SHORT")
    db_session.add(orig_proj)
    db_session.commit()

    export_service = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_service.export_project(db=db_session, project_id=orig_proj.id)

    try:
        import_service = ProjectImportService(storage_provider=mock_storage)

        # 1. When project still in DB -> RESTORE mode must raise ProjectCollisionError
        with pytest.raises(ProjectCollisionError, match="already exists"):
            import_service.execute_import(db=db_session, archive_path=archive_path, import_mode="RESTORE")

        # 2. Delete project from DB -> RESTORE mode succeeds with exact original UUID
        orig_id = orig_proj.id
        db_session.delete(orig_proj)
        db_session.commit()

        restored_proj = import_service.execute_import(db=db_session, archive_path=archive_path, import_mode="RESTORE")
        assert restored_proj.id == orig_id
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)


# ==========================================
# 5. Historical Execution Truth & Worker Fencing
# ==========================================

def test_historical_execution_truth_and_worker_fencing(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """Imported historical jobs must preserve original statuses bit-for-bit and be fenced from workers and indexes."""
    proj = Project(title="Execution Truth Proj", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()

    scene = Scene(project_id=proj.id, scene_number=1, heading="Act 1")
    db_session.add(scene)
    db_session.flush()

    shot = Shot(scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED", status="DRAFT")
    db_session.add(shot)
    db_session.flush()

    # Active GenerationJob in original project
    gen_job = GenerationJob(
        shot_id=shot.id,
        provider_name="mock_provider",
        payload={"prompt": "Cyberpunk flying car"},
        job_type="VIDEO",
        status="RUNNING",
        retry_count=2,
        error_message="Previous network timeout",
    )
    db_session.add(gen_job)

    timeline = AssemblyTimeline(project_id=proj.id, version=1, status="READY")
    db_session.add(timeline)
    db_session.flush()

    qc_run = QCRun(project_id=proj.id, timeline_id=timeline.id, timeline_version=1)
    db_session.add(qc_run)
    db_session.flush()

    approval = ApprovalRecord(project_id=proj.id, timeline_id=timeline.id, timeline_version=1, qc_run_id=qc_run.id)
    db_session.add(approval)
    db_session.flush()

    # Active RenderJob in original project
    render_job = RenderJob(
        project_id=proj.id,
        timeline_id=timeline.id,
        timeline_version=1,
        approval_id=approval.id,
        idempotency_key=f"render_{proj.id}_master",
        status="CLAIMED",
        render_variant_key="preset_1080p_mp4",
    )
    db_session.add(render_job)

    # UsageLedger in original project
    ledger = UsageLedger(
        project_id=proj.id,
        provider="mock_provider",
        operation="VIDEO_GENERATION",
        actual_cost=12.50,
        cost_status="COMMITTED",
    )
    db_session.add(ledger)
    db_session.commit()

    export_service = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_service.export_project(db=db_session, project_id=proj.id)

    try:
        import_service = ProjectImportService(storage_provider=mock_storage)
        cloned_proj = import_service.execute_import(db=db_session, archive_path=archive_path, import_mode="CLONE")

        # 1. Historical Truth Preservation: statuses are NOT overwritten with CANCELLED
        cloned_shots = (
            db_session.query(Shot)
            .join(Scene, Shot.scene_id == Scene.id)
            .filter(Scene.project_id == cloned_proj.id)
            .all()
        )
        cloned_shot_ids = [s.id for s in cloned_shots]
        cloned_gen_job = (
            db_session.query(GenerationJob)
            .filter(
                GenerationJob.shot_id.in_(cloned_shot_ids),
                GenerationJob.error_message == "Previous network timeout",
            )
            .one()
        )
        assert cloned_gen_job.status == "RUNNING"
        assert cloned_gen_job.retry_count == 2
        assert cloned_gen_job.error_message == "Previous network timeout"
        assert cloned_gen_job.imported_historical is True
        assert cloned_gen_job.execution_disabled is True

        cloned_render_job = db_session.query(RenderJob).filter(RenderJob.project_id == cloned_proj.id).one()
        assert cloned_render_job.status == "CLAIMED"
        assert cloned_render_job.imported_historical is True
        assert cloned_render_job.execution_disabled is True

        # 2. Worker Fencing: Workers ignore imported historical jobs
        # Render worker claiming should return None because imported job is fenced
        claimed_render = RenderJobService.claim_next_render_job(db=db_session, worker_id="worker-test")
        assert claimed_render is None

        # 3. Budget Fencing: committed cost excludes imported historical ledgers
        committed_cost = BudgetService.get_project_committed_cost(db=db_session, project_id=cloned_proj.id)
        assert committed_cost == 0.0

        # 4. Uniqueness Index Coexistence: A new live job can be submitted on the same shot / variant
        # without violating partial unique indexes
        cloned_scene = db_session.query(Scene).filter(Scene.project_id == cloned_proj.id).one()
        cloned_shot = db_session.query(Shot).filter(Shot.scene_id == cloned_scene.id).one()

        new_live_job = GenerationJob(
            shot_id=cloned_shot.id,
            provider_name="mock_provider",
            payload={"prompt": "New live prompt"},
            job_type="VIDEO",
            status="QUEUED",
            imported_historical=False,
            execution_disabled=False,
        )
        db_session.add(new_live_job)
        db_session.commit()

        # Both co-exist in the database
        jobs_on_shot = db_session.query(GenerationJob).filter(GenerationJob.shot_id == cloned_shot.id).all()
        assert len(jobs_on_shot) == 2
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)


# ==========================================
# 6. API Endpoints Round-Trip Tests
# ==========================================

def test_api_archive_export_and_import_round_trip(client: TestClient, db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """End-to-end round trip test through FastAPI endpoints."""
    # 1. Create project via API
    create_resp = client.post("/api/v1/projects", json={"title": "API Cyberpunk", "video_mode": "STORY"})
    assert create_resp.status_code == 201
    proj_id = create_resp.json()["id"]

    # 2. Export project archive
    export_resp = client.post(
        f"/api/v1/projects/{proj_id}/export",
        json={"package_type": "FULL_SELF_CONTAINED", "include_history": True, "include_renders": True},
    )
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/octet-stream"
    archive_bytes = export_resp.content
    assert len(archive_bytes) > 0

    # 3. Validate archive pre-flight
    files = {"file": ("api_cyberpunk.orbis", io.BytesIO(archive_bytes), "application/octet-stream")}
    val_resp = client.post("/api/v1/projects/import/validate", files=files)
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert val_data["title"] == "API Cyberpunk"
    assert val_data["collision_detected"] is True
    assert val_data["allowed_modes"] == ["CLONE"]

    # 4. Execute import in CLONE mode
    files = {"file": ("api_cyberpunk.orbis", io.BytesIO(archive_bytes), "application/octet-stream")}
    exec_resp = client.post(
        "/api/v1/projects/import/execute",
        files=files,
        data={"import_mode": "CLONE", "override_title": "API Cyberpunk Cloned"},
    )
    assert exec_resp.status_code == 201
    exec_data = exec_resp.json()
    assert exec_data["title"] == "API Cyberpunk Cloned"
    assert exec_data["import_mode"] == "CLONE"
    assert exec_data["project_id"] != proj_id
    assert exec_data["source_project_id"] == proj_id



# ==========================================
# 7. Phase-3 Preflight & Asset Completeness Tests
# ==========================================

def repack_archive_with_tamper(src_archive_path: str, tamper_fn) -> str:
    """Helper to extract an archive, apply a tampering mutation, and re-sign with valid Phase-2 checksums."""
    temp_dir = tempfile.mkdtemp(prefix="tamper_preflight_")
    try:
        with zipfile.ZipFile(src_archive_path, "r") as zf:
            zf.extractall(temp_dir)
        tamper_fn(temp_dir)

        # Re-compute hashes for all payload files (excluding manifest.json and checksums.sha256)
        file_hashes = {}
        file_sizes = {}
        for root, _, files in os.walk(temp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, temp_dir).replace("\\", "/")
                if rel_path in ("manifest.json", "checksums.sha256"):
                    continue
                file_hashes[rel_path] = ArchiveChecksumService.compute_sha256_file(full_path)
                file_sizes[rel_path] = os.path.getsize(full_path)

        # Update manifest.json's file_manifest
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        manifest_data["file_manifest"] = {
            rel_path: {
                "sha256": file_hashes[rel_path],
                "size_bytes": file_sizes[rel_path],
            }
            for rel_path in sorted(file_hashes.keys())
        }

        manifest_bytes = ArchiveChecksumService.canonical_json_dumps(manifest_data)
        with open(manifest_path, "wb") as f:
            f.write(manifest_bytes)
        manifest_sha = ArchiveChecksumService.compute_sha256_bytes(manifest_bytes)

        # Re-generate checksums.sha256
        checksum_payload_map = dict(file_hashes)
        checksum_payload_map["manifest.json"] = manifest_sha
        checksums_bytes = ArchiveChecksumService.generate_checksums_content(checksum_payload_map)
        with open(os.path.join(temp_dir, "checksums.sha256"), "wb") as f:
            f.write(checksums_bytes)

        # Re-zip
        out_zip = tempfile.NamedTemporaryFile(suffix=".orbis", delete=False).name
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(manifest_path, arcname="manifest.json", compress_type=zipfile.ZIP_DEFLATED)
            zf.write(os.path.join(temp_dir, "checksums.sha256"), arcname="checksums.sha256", compress_type=zipfile.ZIP_DEFLATED)
            for rel_path in sorted(file_hashes.keys()):
                zf.write(os.path.join(temp_dir, rel_path), arcname=rel_path, compress_type=zipfile.ZIP_DEFLATED)
        return out_zip
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_preflight_asset_json_missing_from_manifest(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """A. Asset JSON exists but assets manifest entry missing -> reject."""
    proj = Project(title="Test A", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()
    content = b"sample image"
    content_hash = ArchiveChecksumService.compute_sha256_bytes(content)
    storage_key = f"projects/{proj.id}/assets/test.jpg"
    mock_storage.put_object("default", storage_key, content, "image/jpeg")
    asset = Asset(
        project_id=proj.id,
        name="test.jpg",
        original_filename="test.jpg",
        asset_type="IMAGE",
        content_type="image/jpeg",
        file_size_bytes=len(content),
        checksum_sha256=content_hash,
        storage_bucket="default",
        storage_key=storage_key,
    )
    db_session.add(asset)
    db_session.commit()

    export_svc = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_svc.export_project(db=db_session, project_id=proj.id)

    def tamper(td):
        manifest_p = os.path.join(td, "assets", "manifest.json")
        with open(manifest_p, "w", encoding="utf-8") as f:
            json.dump({}, f)

    tampered_zip = repack_archive_with_tamper(archive_path, tamper)
    try:
        import_svc = ProjectImportService(storage_provider=mock_storage)
        with pytest.raises(ArchiveImportError, match="no entry in assets/manifest.json"):
            import_svc.validate_project_archive(tampered_zip, db_session)
        with pytest.raises(ArchiveImportError, match="no entry in assets/manifest.json"):
            import_svc.execute_import(db_session, tampered_zip, import_mode="CLONE")
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)
        if os.path.exists(tampered_zip):
            os.remove(tampered_zip)


def test_preflight_assets_manifest_payload_missing(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """B. assets manifest entry exists but payload missing -> reject."""
    proj = Project(title="Test B", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()
    content = b"sample image"
    content_hash = ArchiveChecksumService.compute_sha256_bytes(content)
    storage_key = f"projects/{proj.id}/assets/test.jpg"
    mock_storage.put_object("default", storage_key, content, "image/jpeg")
    asset = Asset(
        project_id=proj.id,
        name="test.jpg",
        original_filename="test.jpg",
        asset_type="IMAGE",
        content_type="image/jpeg",
        file_size_bytes=len(content),
        checksum_sha256=content_hash,
        storage_bucket="default",
        storage_key=storage_key,
    )
    db_session.add(asset)
    db_session.commit()

    export_svc = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_svc.export_project(db=db_session, project_id=proj.id)

    td = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(td)
        assets_data_dir = os.path.join(td, "assets", "data")
        for f in os.listdir(assets_data_dir):
            os.remove(os.path.join(assets_data_dir, f))
        val = ArchivePreflightValidator(td)
        with pytest.raises(ArchiveImportError, match="binary payload missing"):
            val.validate_graph()
    finally:
        shutil.rmtree(td, ignore_errors=True)
        if os.path.exists(archive_path):
            os.remove(archive_path)


def test_preflight_payload_hash_size_mismatch(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """C. payload hash/size mismatch -> reject."""
    proj = Project(title="Test C", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()
    content = b"sample image original"
    content_hash = ArchiveChecksumService.compute_sha256_bytes(content)
    storage_key = f"projects/{proj.id}/assets/test.jpg"
    mock_storage.put_object("default", storage_key, content, "image/jpeg")
    asset = Asset(
        project_id=proj.id,
        name="test.jpg",
        original_filename="test.jpg",
        asset_type="IMAGE",
        content_type="image/jpeg",
        file_size_bytes=len(content),
        checksum_sha256=content_hash,
        storage_bucket="default",
        storage_key=storage_key,
    )
    db_session.add(asset)
    db_session.commit()

    export_svc = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_svc.export_project(db=db_session, project_id=proj.id)

    td = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(td)
        assets_data_dir = os.path.join(td, "assets", "data")
        for f in os.listdir(assets_data_dir):
            with open(os.path.join(assets_data_dir, f), "wb") as bf:
                bf.write(b"corrupted content with different hash")
        val = ArchivePreflightValidator(td)
        with pytest.raises(ArchiveImportError, match="(size mismatch|checksum mismatch)"):
            val.validate_graph()
    finally:
        shutil.rmtree(td, ignore_errors=True)
        if os.path.exists(archive_path):
            os.remove(archive_path)


def test_preflight_fk_points_to_nonexistent_asset(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """D. FK points to nonexistent Asset -> reject."""
    proj = Project(title="Test D", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()
    scene = Scene(project_id=proj.id, scene_number=1, heading="Scene 1")
    db_session.add(scene)
    db_session.flush()
    shot = Shot(scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(shot)
    db_session.commit()

    export_svc = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_svc.export_project(db=db_session, project_id=proj.id)

    def tamper(td):
        shots_p = os.path.join(td, "entities", "shots.json")
        with open(shots_p, "r", encoding="utf-8") as f:
            shots_list = json.load(f)
        shots_list[0]["source_asset_id"] = str(uuid.uuid4())
        with open(shots_p, "w", encoding="utf-8") as f:
            json.dump(shots_list, f)

    tampered_zip = repack_archive_with_tamper(archive_path, tamper)
    try:
        import_svc = ProjectImportService(storage_provider=mock_storage)
        with pytest.raises(ArchiveImportError, match="nonexistent source Asset"):
            import_svc.validate_project_archive(tampered_zip, db_session)
        with pytest.raises(ArchiveImportError, match="nonexistent source Asset"):
            import_svc.execute_import(db_session, tampered_zip, import_mode="CLONE")
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)
        if os.path.exists(tampered_zip):
            os.remove(tampered_zip)


def test_preflight_shot_points_to_nonexistent_scene(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """E. Shot points to nonexistent Scene -> reject."""
    proj = Project(title="Test E", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()
    scene = Scene(project_id=proj.id, scene_number=1, heading="Scene 1")
    db_session.add(scene)
    db_session.flush()
    shot = Shot(scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(shot)
    db_session.commit()

    export_svc = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_svc.export_project(db=db_session, project_id=proj.id)

    def tamper(td):
        shots_p = os.path.join(td, "entities", "shots.json")
        with open(shots_p, "r", encoding="utf-8") as f:
            shots_list = json.load(f)
        shots_list[0]["scene_id"] = str(uuid.uuid4())
        with open(shots_p, "w", encoding="utf-8") as f:
            json.dump(shots_list, f)

    tampered_zip = repack_archive_with_tamper(archive_path, tamper)
    try:
        import_svc = ProjectImportService(storage_provider=mock_storage)
        with pytest.raises(ArchiveImportError, match="nonexistent Scene"):
            import_svc.validate_project_archive(tampered_zip, db_session)
        with pytest.raises(ArchiveImportError, match="nonexistent Scene"):
            import_svc.execute_import(db_session, tampered_zip, import_mode="CLONE")
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)
        if os.path.exists(tampered_zip):
            os.remove(tampered_zip)


def test_preflight_asset_lock_target_missing(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """F. AssetLock polymorphic target missing -> reject."""
    proj = Project(title="Test F", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()
    scene = Scene(project_id=proj.id, scene_number=1, heading="Scene 1")
    db_session.add(scene)
    db_session.commit()

    export_svc = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_svc.export_project(db=db_session, project_id=proj.id)

    def tamper(td):
        locks_p = os.path.join(td, "entities", "asset_locks.json")
        locks_list = [{
            "id": str(uuid.uuid4()),
            "project_id": str(proj.id),
            "entity_type": "SHOT",
            "entity_id": str(uuid.uuid4()),
            "is_locked": True,
        }]
        with open(locks_p, "w", encoding="utf-8") as f:
            json.dump(locks_list, f)

    tampered_zip = repack_archive_with_tamper(archive_path, tamper)
    try:
        import_svc = ProjectImportService(storage_provider=mock_storage)
        with pytest.raises(ArchiveImportError, match="references nonexistent SHOT"):
            import_svc.validate_project_archive(tampered_zip, db_session)
        with pytest.raises(ArchiveImportError, match="references nonexistent SHOT"):
            import_svc.execute_import(db_session, tampered_zip, import_mode="CLONE")
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)
        if os.path.exists(tampered_zip):
            os.remove(tampered_zip)


# ==========================================
# 8. Round-Trip History Preservation Test
# ==========================================

def test_export_clone_import_history_preservation_round_trip(db_session: Session, mock_storage: InMemoryObjectStorageProvider):
    """4. Real export -> CLONE import round-trip proving exact preservation of historical values and authority fencing."""
    proj = Project(title="History Round-Trip Proj", video_mode="STORY")
    db_session.add(proj)
    db_session.flush()

    scene = Scene(project_id=proj.id, scene_number=1, heading="Intro Scene")
    db_session.add(scene)
    db_session.flush()

    shot = Shot(scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED")
    db_session.add(shot)
    db_session.flush()

    timeline = AssemblyTimeline(project_id=proj.id, version=1, status="READY")
    db_session.add(timeline)
    db_session.flush()

    qc_run = QCRun(project_id=proj.id, timeline_id=timeline.id, timeline_version=1)
    db_session.add(qc_run)
    db_session.flush()

    approval = ApprovalRecord(project_id=proj.id, timeline_id=timeline.id, timeline_version=1, qc_run_id=qc_run.id)
    db_session.add(approval)
    db_session.flush()

    retry_time = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    poll_time = datetime(2026, 9, 10, 12, 5, 0, tzinfo=timezone.utc)

    # 1. GenerationJob with full history fields
    gen_job = GenerationJob(
        shot_id=shot.id,
        job_type="VIDEO",
        provider_name="vidu",
        provider_job_id="prov-job-roundtrip-999",
        status="POLLING",
        idempotency_key="exact_gj_idem_12345",
        cost_usd=0.85,
        retry_count=1,
        max_retries=4,
        poll_count=18,
        max_polls=50,
        claimed_by="worker-live-1",
        claim_token="claim-token-123",
        claim_expires_at=datetime.now(timezone.utc),
        next_retry_at=retry_time,
        next_poll_at=poll_time,
        submission_attempt_id="submission-attempt-xyz",
        payload={"prompt": "Detailed neon cyber street"},
        result={"video_url": "https://vidu.mock/stream.mp4"},
    )
    db_session.add(gen_job)
    db_session.flush()

    # 2. RenderBatch
    render_batch = RenderBatch(
        project_id=proj.id,
        timeline_id=timeline.id,
        timeline_version=1,
        status="COMPLETED",
        total_variants=1,
        completed_variants=1,
        failed_variants=0,
    )
    db_session.add(render_batch)
    db_session.flush()

    # 3. RenderJob with full history fields
    render_job = RenderJob(
        project_id=proj.id,
        timeline_id=timeline.id,
        timeline_version=1,
        approval_id=approval.id,
        batch_id=render_batch.id,
        render_profile="MASTER_HD",
        render_variant_key="preset_1080p_mp4",
        status="RUNNING",
        idempotency_key="exact_rj_idem_67890",
        progress=0.65,
        claimed_by="render-worker-1",
        claim_token="render-token-456",
        claim_expires_at=datetime.now(timezone.utc),
        retry_count=2,
        max_retries=5,
        estimated_cost_usd=3.50,
        actual_cost_usd=3.40,
        error_message="Previous GPU heartbeat delayed",
        render_metadata={"codec": "h264", "bitrate": "12M"},
    )
    db_session.add(render_job)
    db_session.flush()

    # 4. UsageLedger with exact fields linked to RenderJob
    ledger = UsageLedger(
        project_id=proj.id,
        shot_id=shot.id,
        job_id=gen_job.id,
        render_job_id=render_job.id,
        provider="vidu",
        operation="VIDEO_GENERATION",
        model="vidu-v2",
        usage_units=1,
        estimated_cost=4.00,
        actual_cost=3.80,
        currency="USD",
        cost_status="CONFIRMED",
        provider_event_id="evt-roundtrip-777",
        idempotency_key="exact_ul_idem_99999",
        description="Vidu generation round-trip billing",
    )
    db_session.add(ledger)
    db_session.flush()

    render_job.current_usage_ledger_id = ledger.id

    # 5. LedgerAdjustment
    adj = LedgerAdjustment(
        ledger_id=ledger.id,
        previous_cost=4.00,
        adjusted_cost=3.80,
        reason="Corporate tier discount applied",
        actor="billing_audit_service",
    )
    db_session.add(adj)
    db_session.commit()

    # Export project
    export_svc = ProjectExportService(storage_provider=mock_storage)
    archive_path, _ = export_svc.export_project(db=db_session, project_id=proj.id)

    try:
        import_svc = ProjectImportService(storage_provider=mock_storage)
        cloned_proj = import_svc.execute_import(db=db_session, archive_path=archive_path, import_mode="CLONE")

        # 1. Verify Cloned RenderJob Preserved Truth
        cloned_rj = db_session.query(RenderJob).filter(RenderJob.project_id == cloned_proj.id).one()
        assert cloned_rj.idempotency_key == "exact_rj_idem_67890"  # NO "imported_" prefix!
        assert cloned_rj.progress == 0.65
        assert cloned_rj.retry_count == 2
        assert cloned_rj.max_retries == 5
        assert cloned_rj.estimated_cost_usd == 3.50
        assert cloned_rj.actual_cost_usd == 3.40
        assert cloned_rj.error_message == "Previous GPU heartbeat delayed"
        assert cloned_rj.render_metadata == {"codec": "h264", "bitrate": "12M"}
        assert cloned_rj.status == "RUNNING"
        assert cloned_rj.claimed_by is None  # worker lease cleared
        assert cloned_rj.claim_token is None
        assert cloned_rj.claim_expires_at is None
        assert cloned_rj.imported_historical is True
        assert cloned_rj.execution_disabled is True

        # 2. Verify Cloned GenerationJob Preserved Truth
        cloned_scene = db_session.query(Scene).filter(Scene.project_id == cloned_proj.id).one()
        cloned_shot = db_session.query(Shot).filter(Shot.scene_id == cloned_scene.id).one()
        cloned_gj = db_session.query(GenerationJob).filter(GenerationJob.shot_id == cloned_shot.id).one()
        assert cloned_gj.idempotency_key == "exact_gj_idem_12345"  # NO "imported_" prefix!
        assert cloned_gj.cost_usd == 0.85
        assert cloned_gj.retry_count == 1
        assert cloned_gj.max_retries == 4
        assert cloned_gj.poll_count == 18
        assert cloned_gj.max_polls == 50
        assert cloned_gj.submission_attempt_id == "submission-attempt-xyz"
        assert cloned_gj.provider_job_id == "prov-job-roundtrip-999"
        assert cloned_gj.payload == {"prompt": "Detailed neon cyber street"}
        assert cloned_gj.result == {"video_url": "https://vidu.mock/stream.mp4"}
        assert cloned_gj.status == "POLLING"
        assert cloned_gj.claimed_by is None  # worker lease cleared
        assert cloned_gj.claim_token is None
        assert cloned_gj.imported_historical is True
        assert cloned_gj.execution_disabled is True

        # 3. Verify Cloned UsageLedger Preserved Truth & Linkage
        cloned_ledger = db_session.query(UsageLedger).filter(UsageLedger.project_id == cloned_proj.id).one()
        assert cloned_ledger.idempotency_key == "exact_ul_idem_99999"  # NO "imported_" prefix!
        assert cloned_ledger.provider_event_id == "evt-roundtrip-777"
        assert cloned_ledger.cost_status == "CONFIRMED"
        assert cloned_ledger.estimated_cost == 4.00
        assert cloned_ledger.actual_cost == 3.80
        assert cloned_ledger.currency == "USD"
        assert cloned_ledger.imported_historical is True

        # Verify current_usage_ledger linkage is preserved via remapped ID
        assert cloned_rj.current_usage_ledger_id == cloned_ledger.id

        # 4. Verify LedgerAdjustment Preserved Truth
        cloned_adj = db_session.query(LedgerAdjustment).filter(LedgerAdjustment.ledger_id == cloned_ledger.id).one()
        assert cloned_adj.previous_cost == 4.00
        assert cloned_adj.adjusted_cost == 3.80
        assert cloned_adj.reason == "Corporate tier discount applied"
        assert cloned_adj.actor == "billing_audit_service"

        # 5. Worker Fencing: Workers cannot claim imported jobs
        # Mark source project jobs as execution_disabled to verify cloned imported jobs are fenced
        render_job.execution_disabled = True
        gen_job.execution_disabled = True
        db_session.commit()

        claimed_render = RenderJobService.claim_next_render_job(db=db_session, worker_id="test-worker-idle")
        assert claimed_render is None
        claimed_gen = JobDispatchService.claim_next_job(db=db_session, worker_id="test-worker-idle")
        assert claimed_gen is None

        # 6. Authority / Index Separation: Live unique slots are NOT blocked by imported jobs
        # RenderJob live variant slot
        live_rj = RenderJob(
            project_id=cloned_proj.id,
            timeline_id=cloned_rj.timeline_id,
            timeline_version=1,
            approval_id=cloned_rj.approval_id,
            render_profile="MASTER_HD",
            render_variant_key="preset_1080p_mp4",  # SAME VARIANT AS HISTORICAL
            status="QUEUED",
            idempotency_key="new_live_render_job_idem",
            imported_historical=False,
            execution_disabled=False,
        )
        db_session.add(live_rj)
        db_session.commit()

        # GenerationJob live shot slot
        live_gj = GenerationJob(
            shot_id=cloned_shot.id,  # SAME SHOT AS HISTORICAL
            job_type="VIDEO",
            provider_name="vidu",
            status="PENDING",
            idempotency_key="new_live_generation_job_idem",
            imported_historical=False,
            execution_disabled=False,
        )
        db_session.add(live_gj)
        db_session.commit()

        # Confirm both live and historical co-exist on the same shot / variant
        rjs = db_session.query(RenderJob).filter(RenderJob.project_id == cloned_proj.id).all()
        assert len(rjs) == 2
        gjs = db_session.query(GenerationJob).filter(GenerationJob.shot_id == cloned_shot.id).all()
        assert len(gjs) == 2

    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)
