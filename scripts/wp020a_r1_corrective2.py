from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8", newline="\n")


def repl(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{rel}: expected 1 match, got {count}: {old[:100]!r}")
    write(rel, text.replace(old, new, 1))


# Materialization must not roll back queue state committed before the provider call.
# Isolate DB mutations in savepoints; leave caller transaction healthy on failure.
rel = "backend/app/services/video_materialization.py"
text = read(rel)
old = '''        existing = db.get(Asset, asset_id)\n        if existing:\n            if existing.project_id != project.id or existing.asset_type != "VIDEO":\n                raise VideoMaterializationError("Existing deterministic video Asset conflicts with GenerationJob")\n            if shot.is_locked and shot.source_asset_id not in (None, existing.id):\n                raise VideoMaterializationError("Shot became locked before completed output could be bound")\n            job.output_asset_id = existing.id\n            shot.source_asset_id = existing.id\n            db.commit()\n            return existing\n\n        if shot.is_locked and shot.source_asset_id is not None:\n            raise VideoMaterializationError("Shot became locked before completed output could be bound")\n'''
new = '''        existing = db.get(Asset, asset_id)\n        if existing:\n            if existing.project_id != project.id or existing.asset_type != "VIDEO":\n                raise VideoMaterializationError("Existing deterministic video Asset conflicts with GenerationJob")\n            if shot.is_locked and shot.source_asset_id != existing.id:\n                raise VideoMaterializationError("Shot became locked before completed output could be bound")\n            with db.begin_nested():\n                job.output_asset_id = existing.id\n                shot.source_asset_id = existing.id\n                db.flush()\n            return existing\n\n        if shot.is_locked:\n            raise VideoMaterializationError("Shot became locked before completed output could be bound")\n'''
if text.count(old) != 1:
    raise RuntimeError("video_materialization existing/lock block mismatch")
text = text.replace(old, new, 1)
old = '''            asset = Asset(\n                id=asset_id,\n                project_id=project.id,\n                name=f"Generated Video Shot {shot.shot_number}",\n                original_filename=f"generated_shot_{shot.shot_number}.{ext}",\n                asset_type="VIDEO",\n                content_type=content_type,\n                file_size_bytes=size,\n                checksum_sha256=checksum,\n                storage_bucket=bucket,\n                storage_key=storage_key,\n                created_at=_utc_now(),\n                updated_at=_utc_now(),\n            )\n            db.add(asset)\n            db.flush()\n            job.output_asset_id = asset.id\n            shot.source_asset_id = asset.id\n            shot.updated_at = _utc_now()\n            db.commit()\n            db.refresh(asset)\n            return asset\n        except Exception as exc:\n            db.rollback()\n            if uploaded_new_object and uploaded_bucket and uploaded_key:\n                try:\n                    storage.delete_object(uploaded_bucket, uploaded_key)\n                except Exception:\n                    pass\n            if isinstance(exc, VideoMaterializationError):\n                raise\n            raise VideoMaterializationError("Completed provider video could not be durably materialized") from exc\n'''
new = '''            try:\n                with db.begin_nested():\n                    asset = Asset(\n                        id=asset_id,\n                        project_id=project.id,\n                        name=f"Generated Video Shot {shot.shot_number}",\n                        original_filename=f"generated_shot_{shot.shot_number}.{ext}",\n                        asset_type="VIDEO",\n                        content_type=content_type,\n                        file_size_bytes=size,\n                        checksum_sha256=checksum,\n                        storage_bucket=bucket,\n                        storage_key=storage_key,\n                        created_at=_utc_now(),\n                        updated_at=_utc_now(),\n                    )\n                    db.add(asset)\n                    db.flush()\n                    job.output_asset_id = asset.id\n                    shot.source_asset_id = asset.id\n                    shot.updated_at = _utc_now()\n                    db.flush()\n            except Exception:\n                if uploaded_new_object and uploaded_bucket and uploaded_key:\n                    try:\n                        storage.delete_object(uploaded_bucket, uploaded_key)\n                    except Exception:\n                        pass\n                raise\n            return asset\n        except Exception as exc:\n            if isinstance(exc, VideoMaterializationError):\n                raise\n            raise VideoMaterializationError("Completed provider video could not be durably materialized") from exc\n'''
if text.count(old) != 1:
    raise RuntimeError("video_materialization persistence block mismatch")
write(rel, text.replace(old, new, 1))

# Keep raw completed-job metrics, but derive production readiness only from durable output lineage.
rel = "backend/app/services/production_orchestrator.py"
old = '''            completed_job_shot_ids = set(\n                s_id for (s_id,) in (\n                    db.query(GenerationJob.shot_id)\n                    .filter(\n                        GenerationJob.shot_id.in_(active_shot_ids),\n                        GenerationJob.imported_historical.isnot(True),\n                        func.coalesce(GenerationJob.job_type, "VIDEO") == "VIDEO",\n                        GenerationJob.status == "COMPLETED",\n                    )\n                    .distinct()\n                    .all()\n                )\n            )\n'''
new = old + '''            materialized_completed_job_shot_ids = set(\n                s_id for (s_id,) in (\n                    db.query(GenerationJob.shot_id)\n                    .filter(\n                        GenerationJob.shot_id.in_(active_shot_ids),\n                        GenerationJob.imported_historical.isnot(True),\n                        func.coalesce(GenerationJob.job_type, "VIDEO") == "VIDEO",\n                        GenerationJob.status == "COMPLETED",\n                        GenerationJob.output_asset_id.isnot(None),\n                    )\n                    .distinct()\n                    .all()\n                )\n            )\n'''
repl(rel, old, new)
repl(
    rel,
    '''            completed_job_shot_ids = set()\n\n        active_jobs =''',
    '''            completed_job_shot_ids = set()\n            materialized_completed_job_shot_ids = set()\n\n        active_jobs =''',
)
repl(
    rel,
    '''            if (s.id in completed_job_shot_ids) or (\n''',
    '''            if (s.id in materialized_completed_job_shot_ids and s.source_asset_id is not None) or (\n''',
)

# Generation queue unit suite mocks the new downstream persistence boundary;
# focused materialization/E2E suites exercise it for real with zero-billing storage.
rel = "backend/tests/test_generation_queue.py"
repl(
    rel,
    '''from app.services.generation_worker import run_once\n''',
    '''from app.services.generation_worker import run_once\nfrom app.services.video_materialization import VideoMaterializationService\n''',
)
repl(
    rel,
    '''    monkeypatch.setattr(httpx.AsyncClient, "send", denied)\n''',
    '''    monkeypatch.setattr(httpx.AsyncClient, "send", denied)\n\n    async def materialized_by_focused_suite(*args, **kwargs):\n        return None\n\n    monkeypatch.setattr(\n        VideoMaterializationService,\n        "materialize_completed_result",\n        materialized_by_focused_suite,\n    )\n''',
)

# Existing orchestrator regressions now encode the durable-output invariant.
rel = "backend/tests/test_production_orchestrator.py"
repl(
    rel,
    '''    job = GenerationJob(id=uuid.uuid4(), shot_id=sh.id, provider_name="vidu", status="COMPLETED")\n''',
    '''    job = GenerationJob(\n        id=uuid.uuid4(), shot_id=sh.id, provider_name="vidu", status="COMPLETED", output_asset_id=asset.id\n    )\n''',
)
repl(
    rel,
    '''    assert summary["production_ready_shots"] == 1\n\n    # Transition to final review MUST be rejected: only 1 of 2 shots is production ready!\n''',
    '''    assert summary["production_ready_shots"] == 0\n\n    # Raw provider completion without durable output must not make either shot production-ready.\n''',
)
repl(
    rel,
    '''    assert "only 1/2 shots are production-ready" in res_trans.json()["detail"]\n''',
    '''    assert "only 0/2 shots are production-ready" in res_trans.json()["detail"]\n''',
)
repl(
    rel,
    '''    # Shot 2: AI_GENERATED with COMPLETED job\n    sh2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED", status="PENDING")\n''',
    '''    # Shot 2: AI_GENERATED with materialized COMPLETED job\n    sh2 = Shot(\n        scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED", status="COMPLETED", source_asset_id=ast.id\n    )\n''',
)
repl(
    rel,
    '''    job2 = GenerationJob(id=uuid.uuid4(), shot_id=sh2.id, provider_name="vidu", status="COMPLETED")\n''',
    '''    job2 = GenerationJob(\n        id=uuid.uuid4(), shot_id=sh2.id, provider_name="vidu", status="COMPLETED", output_asset_id=ast.id\n    )\n''',
)

# Manifest public shape stores package_type under archive_options.
rel = "backend/tests/test_wp020a_zero_billing_e2e.py"
repl(
    rel,
    '''        assert manifest["package_type"] == "FULL_SELF_CONTAINED"\n''',
    '''        assert manifest["archive_options"]["package_type"] == "FULL_SELF_CONTAINED"\n''',
)

print("Applied WP020-A-R1 CI corrective #2")
