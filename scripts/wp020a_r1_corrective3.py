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


# Archived-count regression is about exclusion semantics. Make its one live AI
# shot truthfully production-ready under the new durable-output invariant.
repl(
    "backend/tests/test_production_orchestrator.py",
    '''    j1 = GenerationJob(id=uuid.uuid4(), shot_id=sh1.id, provider_name="vidu", status="COMPLETED")\n    db_session.add(j1)\n    db_session.commit()\n''',
    '''    video_asset = Asset(\n        id=uuid.uuid4(),\n        project_id=p.id,\n        name="Archived count durable output",\n        original_filename="archived-count.mp4",\n        asset_type="VIDEO",\n        content_type="video/mp4",\n        file_size_bytes=32,\n        checksum_sha256="a" * 64,\n        storage_bucket="test",\n        storage_key=f"projects/{p.id}/archived-count.mp4",\n    )\n    db_session.add(video_asset)\n    db_session.flush()\n    sh1.source_asset_id = video_asset.id\n    j1 = GenerationJob(\n        id=uuid.uuid4(),\n        shot_id=sh1.id,\n        provider_name="vidu",\n        status="COMPLETED",\n        output_asset_id=video_asset.id,\n    )\n    db_session.add(j1)\n    db_session.commit()\n''',
)

# Archive importer must reconstruct the canonical OrchestrationAudit schema.
repl(
    "backend/app/services/archive/import_service.py",
    '''                    db.add(OrchestrationAudit(\n                        id=remap.get_or_create(parse_uuid(oa["id"]), "ORCHESTRATION_AUDIT"),\n                        project_id=new_project_id,\n                        from_stage=oa.get("from_stage"),\n                        to_stage=oa.get("to_stage", "DRAFT"),\n                        actor=oa.get("actor", "system"),\n                        event_type=oa.get("event_type", "STAGE_TRANSITION"),\n                        meta_info=oa.get("meta_info"),\n                        created_at=parse_datetime(oa.get("created_at")) or datetime.now(timezone.utc),\n                    ))\n''',
    '''                    db.add(OrchestrationAudit(\n                        id=remap.get_or_create(parse_uuid(oa["id"]), "ORCHESTRATION_AUDIT"),\n                        project_id=new_project_id,\n                        from_state=oa.get("from_state", oa.get("from_stage", "DRAFT")),\n                        to_state=oa.get("to_state", oa.get("to_stage")),\n                        action=oa.get("action", oa.get("event_type", "IMPORTED_EVENT")),\n                        actor=oa.get("actor", "SYSTEM"),\n                        result=oa.get("result", "APPLIED"),\n                        reason_code=oa.get("reason_code"),\n                        detail=oa.get("detail"),\n                        created_at=parse_datetime(oa.get("created_at")) or datetime.now(timezone.utc),\n                    ))\n''',
)

print("Applied WP020-A-R1 CI corrective #3")
