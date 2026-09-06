import os
import pytest
from alembic.config import Config
from alembic import command
from app.core.config import settings


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
        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # 2. Downgrade one revision (008 -> 007)
        command.downgrade(alembic_cfg, "-1")

        # 3. Upgrade to head again (007 -> 008)
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

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'legacy_queue.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)
    command.upgrade(cfg, "006_vidu_queue")
    engine = create_engine(url)
    meta = MetaData()
    projects_tbl = Table("projects", meta, autoload_with=engine)
    projects_tbl.c.id.type = Uuid()
    stories_tbl = Table("stories", meta, autoload_with=engine)
    stories_tbl.c.id.type = Uuid()
    stories_tbl.c.project_id.type = Uuid()
    scenes_tbl = Table("scenes", meta, autoload_with=engine)
    scenes_tbl.c.id.type = Uuid()
    scenes_tbl.c.story_id.type = Uuid()
    shots_tbl = Table("shots", meta, autoload_with=engine)
    shots_tbl.c.id.type = Uuid()
    shots_tbl.c.scene_id.type = Uuid()
    project_id = uuid.uuid4()
    story_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    shot_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(projects_tbl.insert().values(id=project_id, title="Migration test", status="DRAFT", created_at=now, updated_at=now))
        connection.execute(stories_tbl.insert().values(id=story_id, project_id=project_id, logline="Test", status="DRAFT", is_locked=False, created_at=now, updated_at=now))
        connection.execute(scenes_tbl.insert().values(id=scene_id, story_id=story_id, scene_number=1, heading="Test", is_locked=False, created_at=now, updated_at=now))
        connection.execute(shots_tbl.insert().values(id=shot_id, scene_id=scene_id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0, is_locked=False, status="PENDING", created_at=now, updated_at=now))
    jobs = Table("generation_jobs", MetaData(), autoload_with=engine)
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


def test_008_hybrid_shot_locks_modes_lifecycle(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, Uuid

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'wp008_migration.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to 007
    command.upgrade(cfg, "007_queue_safety")
    engine = create_engine(url)
    meta = MetaData()
    projects = Table("projects", meta, autoload_with=engine)
    projects.c.id.type = Uuid()
    stories = Table("stories", meta, autoload_with=engine)
    stories.c.id.type = Uuid()
    stories.c.project_id.type = Uuid()
    scenes = Table("scenes", meta, autoload_with=engine)
    scenes.c.id.type = Uuid()
    scenes.c.story_id.type = Uuid()

    p_id = uuid.uuid4()
    s_id = uuid.uuid4()
    sc_id_1 = uuid.uuid4()
    sc_id_2 = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(projects.insert().values(id=p_id, title="Pre-WP008 Project", status="DRAFT", created_at=now, updated_at=now))
        conn.execute(stories.insert().values(id=s_id, project_id=p_id, logline="Test", status="DRAFT", is_locked=False, created_at=now, updated_at=now))
        conn.execute(scenes.insert().values(id=sc_id_1, story_id=s_id, scene_number=1, heading="Scene 1", is_locked=False, created_at=now, updated_at=now))
        conn.execute(scenes.insert().values(id=sc_id_2, story_id=s_id, scene_number=2, heading="Scene 2", is_locked=False, created_at=now, updated_at=now))

    # 2. Upgrade to 008 / head — verify deterministic backfill of scenes.project_id
    command.upgrade(cfg, "head")

    meta2 = MetaData()
    scenes2 = Table("scenes", meta2, autoload_with=engine)
    scenes2.c.id.type = Uuid()
    scenes2.c.story_id.type = Uuid()
    scenes2.c.project_id.type = Uuid()
    projects2 = Table("projects", meta2, autoload_with=engine)
    projects2.c.id.type = Uuid()
    locks = Table("asset_locks", meta2, autoload_with=engine)
    locks.c.id.type = Uuid()
    locks.c.project_id.type = Uuid()
    locks.c.entity_id.type = Uuid()

    with engine.connect() as conn:
        rows = conn.execute(select(scenes2).where(scenes2.c.story_id == s_id)).mappings().all()
        assert len(rows) == 2
        for r in rows:
            assert r["project_id"] == p_id
        p_row = conn.execute(select(projects2).where(projects2.c.id == p_id)).mappings().first()
        assert p_row["video_mode"] == "STORY"

    # 3. Downgrade to 007
    command.downgrade(cfg, "007_queue_safety")
    meta3 = MetaData()
    meta3.reflect(bind=engine)
    assert "asset_locks" not in meta3.tables

    # 4. Re-upgrade to head
    command.upgrade(cfg, "head")
    meta4 = MetaData()
    meta4.reflect(bind=engine)
    assert "asset_locks" in meta4.tables
    engine.dispose()


def test_008_downgrade_guarded_refusal_when_direct_scenes_exist(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, Uuid

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'wp008_downgrade_guard.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to head (008)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    meta = MetaData()
    projects = Table("projects", meta, autoload_with=engine)
    projects.c.id.type = Uuid()
    scenes = Table("scenes", meta, autoload_with=engine)
    scenes.c.id.type = Uuid()
    scenes.c.project_id.type = Uuid()
    scenes.c.story_id.type = Uuid()

    p_id = uuid.uuid4()
    sc_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(projects.insert().values(id=p_id, title="Direct Project", video_mode="SCENE", status="DRAFT", created_at=now, updated_at=now))
        # Direct scene without story (story_id=NULL)
        conn.execute(scenes.insert().values(id=sc_id, project_id=p_id, story_id=None, scene_number=1, is_locked=False, created_at=now, updated_at=now))

    # 2. Attempting to downgrade with direct scene must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        command.downgrade(cfg, "007_queue_safety")
    assert "Cannot downgrade migration 008" in str(exc_info.value)
    assert "direct Project->Scene row(s) exist with story_id=NULL" in str(exc_info.value)

    # 3. Clean up direct scene
    with engine.begin() as conn:
        conn.execute(scenes.delete().where(scenes.c.id == sc_id))

    # 4. Now downgrade succeeds cleanly without orphan rows
    command.downgrade(cfg, "007_queue_safety")
    meta_downgraded = MetaData()
    meta_downgraded.reflect(bind=engine)
    assert "asset_locks" not in meta_downgraded.tables
    engine.dispose()


def test_009_cost_ledger_and_budget_lifecycle(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, Uuid

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'wp009_migration.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to 008
    command.upgrade(cfg, "008_hybrid_shot_locks_modes")
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)
    assert "usage_ledger" not in meta.tables
    assert "ledger_adjustments" not in meta.tables

    # 2. Upgrade to 009 / head
    command.upgrade(cfg, "head")

    meta2 = MetaData()
    meta2.reflect(bind=engine)
    assert "usage_ledger" in meta2.tables
    assert "ledger_adjustments" in meta2.tables

    projects = Table("projects", meta2, autoload_with=engine)
    projects.c.id.type = Uuid()
    ledger = Table("usage_ledger", meta2, autoload_with=engine)
    ledger.c.id.type = Uuid()
    ledger.c.project_id.type = Uuid()
    adjustments = Table("ledger_adjustments", meta2, autoload_with=engine)
    adjustments.c.id.type = Uuid()
    adjustments.c.ledger_id.type = Uuid()

    p_id = uuid.uuid4()
    l_id = uuid.uuid4()
    a_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(
            projects.insert().values(
                id=p_id,
                title="WP009 Project",
                status="DRAFT",
                video_mode="SCENE",
                budget_limit=50.0,
                budget_currency="USD",
                budget_threshold_percentage=85.0,
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            ledger.insert().values(
                id=l_id,
                project_id=p_id,
                provider="vidu",
                operation="VIDEO_GENERATION",
                estimated_cost=0.20,
                currency="USD",
                cost_status="ESTIMATED",
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            adjustments.insert().values(
                id=a_id,
                ledger_id=l_id,
                actor="reviewer",
                reason="Audit discount",
                previous_cost=0.20,
                adjusted_cost=0.15,
                created_at=now,
            )
        )

    # Verify query
    with engine.connect() as conn:
        p_row = conn.execute(select(projects).where(projects.c.id == p_id)).mappings().first()
        assert p_row["budget_limit"] == 50.0
        assert p_row["budget_threshold_percentage"] == 85.0
        l_row = conn.execute(select(ledger).where(ledger.c.id == l_id)).mappings().first()
        assert l_row["estimated_cost"] == 0.20
        a_row = conn.execute(select(adjustments).where(adjustments.c.id == a_id)).mappings().first()
        assert a_row["adjusted_cost"] == 0.15

    # 3. Downgrade -1 (to 008)
    command.downgrade(cfg, "-1")
    meta3 = MetaData()
    meta3.reflect(bind=engine)
    assert "usage_ledger" not in meta3.tables
    assert "ledger_adjustments" not in meta3.tables

    # 4. Re-upgrade to head
    command.upgrade(cfg, "head")
    meta4 = MetaData()
    meta4.reflect(bind=engine)
    assert "usage_ledger" in meta4.tables
    assert "ledger_adjustments" in meta4.tables

    # 5. Verify DB-enforced uniqueness constraints and nullable semantics on re-upgraded head
    from sqlalchemy.exc import IntegrityError
    ledger4 = Table("usage_ledger", meta4, autoload_with=engine)
    ledger4.c.id.type = Uuid()
    ledger4.c.project_id.type = Uuid()
    if "job_id" in ledger4.c:
        ledger4.c.job_id.type = Uuid()

    p_id_2 = uuid.uuid4()
    with engine.begin() as conn:
        # Multiple NULL idempotency_keys allowed
        conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, provider="vidu", operation="OP1", idempotency_key=None, created_at=now, updated_at=now))
        conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, provider="vidu", operation="OP2", idempotency_key=None, created_at=now, updated_at=now))

        # First insert with non-null idempotency_key succeeds
        conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, provider="vidu", operation="OP3", idempotency_key="canon-key-1", created_at=now, updated_at=now))

        # Cross-project same idempotency_key succeeds
        conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id_2, provider="vidu", operation="OP3", idempotency_key="canon-key-1", created_at=now, updated_at=now))

    # Duplicate non-null idempotency_key within same project fails closed at DB level
    import pytest
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, provider="vidu", operation="OP4", idempotency_key="canon-key-1", created_at=now, updated_at=now))

    # Duplicate (job_id, operation) fails closed at DB level
    job_id_1 = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, job_id=job_id_1, provider="vidu", operation="GENERATE", created_at=now, updated_at=now))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, job_id=job_id_1, provider="vidu", operation="GENERATE", created_at=now, updated_at=now))

    # Duplicate (provider, provider_event_id) fails closed at DB level
    with engine.begin() as conn:
        conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, provider="vidu", operation="POLL", provider_event_id="evt-uniq-1", created_at=now, updated_at=now))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(ledger4.insert().values(id=uuid.uuid4(), project_id=p_id, provider="vidu", operation="POLL", provider_event_id="evt-uniq-1", created_at=now, updated_at=now))

    engine.dispose()
