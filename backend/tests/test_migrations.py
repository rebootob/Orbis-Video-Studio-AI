import os
import pytest
from alembic.config import Config
from alembic import command
from app.core.config import settings

# Test migration execution against SQLite or PostgreSQL database URL
def test_alembic_migration_lifecycle(tmp_path):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg_path = os.path.join(backend_dir, "alembic.ini")
    
    alembic_cfg = Config(alembic_cfg_path)
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    
    # Use isolated SQLite file db for migration lifecycle testing
    test_db_path = tmp_path / "test_migration.db"
    sqlite_url = f"sqlite:///{test_db_path}"
    
    # Override settings for migration runner test
    original_uri = settings.SQLALCHEMY_DATABASE_URI_OVERRIDE
    settings.SQLALCHEMY_DATABASE_URI_OVERRIDE = sqlite_url

    try:
        # 1. Upgrade to head (001 -> 002 -> 003)
        command.upgrade(alembic_cfg, "head")

        # 2. Downgrade one revision (003 -> 002)
        command.downgrade(alembic_cfg, "-1")

        # 3. Upgrade to head again (002 -> 003)
        command.upgrade(alembic_cfg, "head")
        
        # 4. Downgrade to base
        command.downgrade(alembic_cfg, "base")
        
        # 5. Upgrade to head again
        command.upgrade(alembic_cfg, "head")
    finally:
        settings.SQLALCHEMY_DATABASE_URI_OVERRIDE = original_uri



def test_queue_safety_upgrade_preserves_clean_requests_and_quarantines_legacy(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, Uuid
    from sqlalchemy.orm import Session
    from app.models.project import Project
    from app.models.story import Story
    from app.models.scene import Scene
    from app.models.shot import Shot

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'legacy_queue.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)
    command.upgrade(cfg, "006_vidu_queue")
    engine = create_engine(url)
    with Session(engine) as db:
        project = Project(id=uuid.uuid4(), title="Migration test")
        story = Story(id=uuid.uuid4(), project_id=project.id, logline="Test")
        scene = Scene(id=uuid.uuid4(), story_id=story.id, scene_number=1, heading="Test")
        shot = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED")
        db.add_all([project, story, scene, shot])
        db.commit()
        shot_id = shot.id
    jobs = Table("generation_jobs", MetaData(), autoload_with=engine)
    # SQLite reflects the legacy PostgreSQL UUID declaration as NUMERIC.
    jobs.c.id.type = Uuid()
    jobs.c.shot_id.type = Uuid()
    ids = [uuid.uuid4() for _ in range(3)]
    payload = {"prompt": "Clean prompt", "provider_specific_params": {"resolution": "720p"}}
    with engine.begin() as connection:
        for index, job_id in enumerate(ids):
            connection.execute(jobs.insert().values(id=job_id, shot_id=shot_id, provider_name="vidu",
                status="PROCESSING" if index == 1 else "PENDING",
                payload={"nested": [{"api_key": "LEAK"}]} if index == 2 else payload,
                result={"untrusted": {"secret": "LEAK"}}, error_message="LEAK",
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)))
    command.upgrade(cfg, "head")
    jobs = Table("generation_jobs", MetaData(), autoload_with=engine)
    # SQLite reflects the legacy PostgreSQL UUID declaration as NUMERIC.
    jobs.c.id.type = Uuid()
    jobs.c.shot_id.type = Uuid()
    with engine.connect() as connection:
        records = connection.execute(select(jobs)).mappings().all()
    by_id = {str(row["id"]): row for row in records}
    assert by_id[str(ids[0])]["status"] == "PENDING"
    assert by_id[str(ids[0])]["payload"] == payload
    assert by_id[str(ids[1])]["status"] == "RECONCILIATION_REQUIRED"
    assert by_id[str(ids[2])]["status"] == "RECONCILIATION_REQUIRED"
    assert by_id[str(ids[2])]["payload"] is None
    assert "LEAK" not in str(records)
    assert all(row["claim_token"] is None and row["poll_count"] == 0 for row in records)
    engine.dispose()
