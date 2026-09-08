from pathlib import Path


def replace_once(path: str, old: str, new: str, marker: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if marker in text:
        print(f"{path}: already patched")
        return
    if old not in text:
        raise SystemExit(f"Expected source block not found in {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"{path}: patched")


replace_once(
    "backend/app/services/audio_production.py",
    '''        scenes = (\n            db.query(Scene)\n            .filter(Scene.project_id == project_id)\n            .order_by(Scene.scene_number.asc())\n            .all()\n        )\n        scene_ids = [s.id for s in scenes]\n\n        shots: List[Shot] = []\n        if scene_ids:\n            shots = (\n                db.query(Shot)\n                .filter(Shot.scene_id.in_(scene_ids))\n                .order_by(Shot.shot_number.asc())\n                .all()\n            )\n''',
    '''        # Canonical project scene resolution must support both direct Project -> Scene\n        # lineage (SHORT/SCENE/LOOP) and STORY -> Scene lineage.  Generated STORY\n        # scenes intentionally carry story_id without duplicating project_id.\n        story = db.query(Story).filter(Story.project_id == project_id).first()\n        scene_query = db.query(Scene)\n        if story is not None:\n            scene_query = scene_query.filter(\n                (Scene.project_id == project_id) | (Scene.story_id == story.id)\n            )\n        else:\n            scene_query = scene_query.filter(Scene.project_id == project_id)\n\n        scenes = scene_query.order_by(Scene.scene_number.asc(), Scene.id.asc()).all()\n        scenes = [s for s in scenes if not (s.scene_config or {}).get("archived")]\n        scene_ids = [s.id for s in scenes]\n\n        shots: List[Shot] = []\n        if scene_ids:\n            shots = (\n                db.query(Shot)\n                .filter(\n                    Shot.scene_id.in_(scene_ids),\n                    Shot.status != "ARCHIVED",\n                )\n                .order_by(Shot.shot_number.asc(), Shot.id.asc())\n                .all()\n            )\n''',
    "Canonical project scene resolution must support both direct Project -> Scene",
)

# Add Story model import only when the production patch is needed.
p = Path("backend/app/services/audio_production.py")
text = p.read_text(encoding="utf-8")
if "from app.models.story import Story\n" not in text:
    anchor = "from app.models.project import Project\n"
    if anchor not in text:
        raise SystemExit("Project import anchor not found in audio_production.py")
    text = text.replace(anchor, anchor + "from app.models.story import Story\n", 1)
    p.write_text(text, encoding="utf-8")

replace_once(
    "backend/tests/test_wp020a_zero_billing_e2e.py",
    '''    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))\n    assert len(timeline.shot_placements) == len(shots)\n    assert all(p.source_type == "VIDEO" for p in timeline.shot_placements)\n    assert all(p.visual_asset_id is not None for p in timeline.shot_placements)\n''',
    '''    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))\n    assert len(timeline.shot_placements) == len(shots)\n    assert all(p.source_type == "VIDEO" for p in timeline.shot_placements)\n    assert all(p.visual_asset_id is not None for p in timeline.shot_placements)\n\n    # S1-LIVE-01 regression: the same canonical STORY-linked scenes/shots must\n    # continue into Core V1 AudioPlan without a noncanonical Scene.project_id fixture.\n    audio_plan = AudioProductionService.generate_audio_plan(db_session, project.id)\n    summary = audio_plan.plan_data["summary"]\n    tracks = audio_plan.plan_data["tracks"]\n    assert summary["total_scenes"] == len(story_scenes)\n    assert summary["total_shots"] == len(shots)\n    assert tracks["bgm_count"] == 1\n    assert tracks["ambience_count"] == len(story_scenes)\n    assert tracks["vo_count"] + tracks["dialogue_count"] >= 1\n''',
    "S1-LIVE-01 regression: the same canonical STORY-linked scenes/shots",
)
