from pathlib import Path

path = Path("backend/app/services/archive/import_service.py")
text = path.read_text(encoding="utf-8")
old = '''                    db.add(TimelineAudit(\n                        id=remap.get_or_create(parse_uuid(ta["id"]), "TIMELINE_AUDIT"),\n                        timeline_id=remap.get_or_create(parse_uuid(ta["timeline_id"]), "TIMELINE"),\n                        action=ta.get("action", "UPDATE"),\n                        details=ta.get("details"),\n                        created_at=parse_datetime(ta.get("created_at")) or datetime.now(timezone.utc),\n                    ))\n'''
new = '''                    db.add(TimelineAudit(\n                        id=remap.get_or_create(parse_uuid(ta["id"]), "TIMELINE_AUDIT"),\n                        project_id=new_project_id,\n                        timeline_id=remap.get_or_create(parse_uuid(ta["timeline_id"]), "TIMELINE"),\n                        action=ta.get("action", "UPDATE"),\n                        actor=ta.get("actor", "system"),\n                        change_reason=ta.get("change_reason"),\n                        snapshot_data=ta.get("snapshot_data", ta.get("details")),\n                        created_at=parse_datetime(ta.get("created_at")) or datetime.now(timezone.utc),\n                    ))\n'''
if text.count(old) != 1:
    raise SystemExit(f"expected exactly one TimelineAudit importer block, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
print("Applied canonical TimelineAudit import mapping")
