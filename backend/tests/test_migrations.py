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
    shot_ids = [uuid.uuid4() for _ in range(3)]
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(projects_tbl.insert().values(id=project_id, title="Migration test", status="DRAFT", created_at=now, updated_at=now))
        connection.execute(stories_tbl.insert().values(id=story_id, project_id=project_id, logline="Test", status="DRAFT", is_locked=False, created_at=now, updated_at=now))
        connection.execute(scenes_tbl.insert().values(id=scene_id, story_id=story_id, scene_number=1, heading="Test", is_locked=False, created_at=now, updated_at=now))
        for index, s_id in enumerate(shot_ids):
            connection.execute(shots_tbl.insert().values(id=s_id, scene_id=scene_id, shot_number=index + 1, shot_type="AI_GENERATED", duration_seconds=4.0, is_locked=False, status="PENDING", created_at=now, updated_at=now))
    jobs = Table("generation_jobs", MetaData(), autoload_with=engine)
    jobs.c.id.type = Uuid()
    jobs.c.shot_id.type = Uuid()
    ids = [uuid.uuid4() for _ in range(3)]
    payload = {"prompt": "Clean prompt", "provider_specific_params": {"resolution": "720p"}}
    with engine.begin() as connection:
        for index, job_id in enumerate(ids):
            connection.execute(jobs.insert().values(id=job_id, shot_id=shot_ids[index], provider_name="vidu",
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

    # 3. Downgrade to 008
    command.downgrade(cfg, "008_hybrid_shot_locks_modes")
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


def test_010_story_version_history_lifecycle(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, Uuid

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'wp010_migration.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to 009
    command.upgrade(cfg, "009_cost_ledger_and_budget")
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)
    assert "story_versions" not in meta.tables

    # 2. Upgrade to head (010)
    command.upgrade(cfg, "head")
    meta2 = MetaData()
    meta2.reflect(bind=engine)
    assert "story_versions" in meta2.tables
    stories_tbl = Table("stories", meta2, autoload_with=engine)
    stories_tbl.c.id.type = Uuid()
    stories_tbl.c.project_id.type = Uuid()
    assert "version_number" in stories_tbl.c

    story_versions_tbl = Table("story_versions", meta2, autoload_with=engine)
    story_versions_tbl.c.id.type = Uuid()
    story_versions_tbl.c.story_id.type = Uuid()
    story_versions_tbl.c.project_id.type = Uuid()

    # Insert sample story version record
    now = datetime.now(timezone.utc)
    s_id = uuid.uuid4()
    p_id = uuid.uuid4()
    v_id = uuid.uuid4()

    projects_tbl = Table("projects", meta2, autoload_with=engine)
    projects_tbl.c.id.type = Uuid()

    with engine.begin() as conn:
        conn.execute(projects_tbl.insert().values(id=p_id, title="Test", status="DRAFT", created_at=now, updated_at=now))
        conn.execute(stories_tbl.insert().values(id=s_id, project_id=p_id, version_number=1, status="DRAFT", is_locked=False, created_at=now, updated_at=now))
        conn.execute(story_versions_tbl.insert().values(
            id=v_id,
            story_id=s_id,
            project_id=p_id,
            version_number=1,
            title="Initial Title",
            logline="Initial Logline",
            synopsis="Initial Synopsis",
            status="SUPERSEDED",
            created_at=now,
        ))

    with engine.connect() as conn:
        row = conn.execute(select(story_versions_tbl).where(story_versions_tbl.c.id == v_id)).mappings().first()
        assert row["title"] == "Initial Title"
        assert row["version_number"] == 1

    # 3. Downgrade to 009
    command.downgrade(cfg, "009_cost_ledger_and_budget")
    meta3 = MetaData()
    meta3.reflect(bind=engine)
    assert "story_versions" not in meta3.tables

    # 4. Re-upgrade to head
    command.upgrade(cfg, "head")
    meta4 = MetaData()
    meta4.reflect(bind=engine)
    assert "story_versions" in meta4.tables
    engine.dispose()


def test_011_batch_resume_runs_and_indexes_lifecycle(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, Uuid

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'wp011_migration.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to 010
    command.upgrade(cfg, "010_story_version_history")
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)
    assert "batch_runs" not in meta.tables
    assert "batch_run_items" not in meta.tables

    # 2. Upgrade to head (011)
    command.upgrade(cfg, "head")
    meta2 = MetaData()
    meta2.reflect(bind=engine)
    assert "batch_runs" in meta2.tables
    assert "batch_run_items" in meta2.tables

    projects_tbl = Table("projects", meta2, autoload_with=engine)
    projects_tbl.c.id.type = Uuid()
    scenes_tbl = Table("scenes", meta2, autoload_with=engine)
    scenes_tbl.c.id.type = Uuid()
    scenes_tbl.c.project_id.type = Uuid()
    shots_tbl = Table("shots", meta2, autoload_with=engine)
    shots_tbl.c.id.type = Uuid()
    shots_tbl.c.scene_id.type = Uuid()
    batch_runs_tbl = Table("batch_runs", meta2, autoload_with=engine)
    batch_runs_tbl.c.id.type = Uuid()
    batch_runs_tbl.c.project_id.type = Uuid()
    batch_run_items_tbl = Table("batch_run_items", meta2, autoload_with=engine)
    batch_run_items_tbl.c.id.type = Uuid()
    batch_run_items_tbl.c.batch_run_id.type = Uuid()
    batch_run_items_tbl.c.shot_id.type = Uuid()

    now = datetime.now(timezone.utc)
    p_id = uuid.uuid4()
    sc_id = uuid.uuid4()
    sh_id = uuid.uuid4()
    br_id = uuid.uuid4()
    bri_id = uuid.uuid4()

    with engine.begin() as conn:
        conn.execute(projects_tbl.insert().values(id=p_id, title="P1", status="SHOT_PLAN_APPROVED", created_at=now, updated_at=now))
        conn.execute(scenes_tbl.insert().values(id=sc_id, project_id=p_id, scene_number=1, is_locked=False, created_at=now, updated_at=now))
        conn.execute(shots_tbl.insert().values(id=sh_id, scene_id=sc_id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0, is_locked=False, status="PENDING", created_at=now, updated_at=now))
        conn.execute(batch_runs_tbl.insert().values(
            id=br_id,
            project_id=p_id,
            operation_type="CONTINUE_INCOMPLETE",
            status="COMPLETED",
            requested_count=1,
            eligible_count=1,
            queued_count=1,
            skipped_count=0,
            completed_count=0,
            failed_count=0,
            created_at=now,
            updated_at=now,
        ))
        conn.execute(batch_run_items_tbl.insert().values(
            id=bri_id,
            batch_run_id=br_id,
            shot_id=sh_id,
            decision="QUEUED",
            skip_reason=None,
            created_at=now,
        ))

    with engine.connect() as conn:
        r = conn.execute(select(batch_runs_tbl).where(batch_runs_tbl.c.id == br_id)).mappings().first()
        assert r["operation_type"] == "CONTINUE_INCOMPLETE"
        item = conn.execute(select(batch_run_items_tbl).where(batch_run_items_tbl.c.id == bri_id)).mappings().first()
        assert item["decision"] == "QUEUED"

    # 3. Downgrade to 010
    command.downgrade(cfg, "010_story_version_history")
    meta3 = MetaData()
    meta3.reflect(bind=engine)
    assert "batch_runs" not in meta3.tables
    assert "batch_run_items" not in meta3.tables

    # 4. Upgrade back to head
    command.upgrade(cfg, "head")
    meta4 = MetaData()
    meta4.reflect(bind=engine)
    assert "batch_runs" in meta4.tables
    assert "batch_run_items" in meta4.tables
    engine.dispose()


def test_012_production_orchestrator_and_staged_approvals_lifecycle(tmp_path, monkeypatch):
    """Test 012 migration lifecycle:
    1. Upgrade to 012 adds automation_mode to projects and creates orchestration_audits table with indexes.
    2. Downgrade to 011 removes orchestration_audits table and automation_mode column.
    3. Upgrade back to head re-establishes schema cleanly.
    """
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, Uuid

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))

    url = f"sqlite:///{tmp_path / 'orchestration_test.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to head
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)
    assert "orchestration_audits" in meta.tables
    assert "automation_mode" in meta.tables["projects"].c

    projects_tbl = Table("projects", meta, autoload_with=engine)
    projects_tbl.c.id.type = Uuid()
    audits_tbl = Table("orchestration_audits", meta, autoload_with=engine)
    audits_tbl.c.id.type = Uuid()
    audits_tbl.c.project_id.type = Uuid()

    p_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(projects_tbl.insert().values(
            id=p_id,
            title="Orchestration Test Project",
            status="DRAFT",
            automation_mode="MANUAL",
            created_at=now,
            updated_at=now,
        ))
        conn.execute(audits_tbl.insert().values(
            id=audit_id,
            project_id=p_id,
            from_state="DRAFT",
            to_state="STORY_GENERATED",
            action="GENERATE_STORY",
            actor="USER",
            result="APPLIED",
            reason_code="USER_ACTION",
            detail="Generated initial story",
            created_at=now,
        ))

    with engine.connect() as conn:
        p_row = conn.execute(select(projects_tbl).where(projects_tbl.c.id == p_id)).mappings().first()
        assert p_row["automation_mode"] == "MANUAL"
        audit_row = conn.execute(select(audits_tbl).where(audits_tbl.c.id == audit_id)).mappings().first()
        assert audit_row["action"] == "GENERATE_STORY"
        assert audit_row["result"] == "APPLIED"

    # 2. Downgrade to 011
    command.downgrade(cfg, "011_batch_resume_runs_and_indexes")
    meta_down = MetaData()
    meta_down.reflect(bind=engine)
    assert "orchestration_audits" not in meta_down.tables
    assert "automation_mode" not in meta_down.tables["projects"].c

    # 3. Upgrade back to head
    command.upgrade(cfg, "head")
    meta_head = MetaData()
    meta_head.reflect(bind=engine)
    assert "orchestration_audits" in meta_head.tables
    assert "automation_mode" in meta_head.tables["projects"].c
    engine.dispose()


def test_019_export_presets_and_variant_key_lifecycle(tmp_path, monkeypatch):
    """Test 019 migration lifecycle: upgrade, blocked downgrade on active variants, historical completed downgrade, and safe downgrade."""
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, text, Uuid

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))

    url = f"sqlite:///{tmp_path / 'wp019_migration_test.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to 018_cloud_render_workers
    command.upgrade(cfg, "018_cloud_render_workers")
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)
    assert "render_batches" not in meta.tables
    assert "render_variant_key" not in meta.tables["render_jobs"].c

    # Populate sample project, timeline, qc_run, approval, and WP017 render_job
    p_id = uuid.uuid4()
    t_id = uuid.uuid4()
    qc_id = uuid.uuid4()
    app_id = uuid.uuid4()
    rj_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    projects_tbl = meta.tables["projects"]
    projects_tbl.c.id.type = Uuid()
    timelines_tbl = meta.tables["assembly_timelines"]
    timelines_tbl.c.id.type = Uuid()
    timelines_tbl.c.project_id.type = Uuid()
    qc_runs_tbl = meta.tables["qc_runs"]
    qc_runs_tbl.c.id.type = Uuid()
    qc_runs_tbl.c.project_id.type = Uuid()
    qc_runs_tbl.c.timeline_id.type = Uuid()
    approvals_tbl = meta.tables["production_approvals"]
    approvals_tbl.c.id.type = Uuid()
    approvals_tbl.c.project_id.type = Uuid()
    approvals_tbl.c.timeline_id.type = Uuid()
    approvals_tbl.c.qc_run_id.type = Uuid()
    render_jobs_tbl = meta.tables["render_jobs"]
    render_jobs_tbl.c.id.type = Uuid()
    render_jobs_tbl.c.project_id.type = Uuid()
    render_jobs_tbl.c.timeline_id.type = Uuid()
    render_jobs_tbl.c.approval_id.type = Uuid()

    with engine.begin() as conn:
        conn.execute(projects_tbl.insert().values(id=p_id, title="P19", status="FINAL_REVIEW", created_at=now, updated_at=now))
        conn.execute(timelines_tbl.insert().values(id=t_id, project_id=p_id, version=1, status="APPROVED", created_at=now, updated_at=now))
        conn.execute(qc_runs_tbl.insert().values(id=qc_id, project_id=p_id, timeline_id=t_id, timeline_version=1, status="PASSED", created_at=now, updated_at=now))
        conn.execute(approvals_tbl.insert().values(id=app_id, project_id=p_id, timeline_id=t_id, timeline_version=1, qc_run_id=qc_id, status="APPROVED", approved_at=now))
        conn.execute(render_jobs_tbl.insert().values(
            id=rj_id,
            project_id=p_id,
            timeline_id=t_id,
            timeline_version=1,
            approval_id=app_id,
            render_profile="MASTER_HD",
            status="QUEUED",
            idempotency_key=f"render_{p_id}_1_MASTER_HD",
            progress=0.0,
            retry_count=0,
            max_retries=3,
            estimated_cost_usd=0.50,
            created_at=now,
            updated_at=now,
        ))

    # 2. A. UPGRADE to 019
    command.upgrade(cfg, "019_export_presets_and_variant_key")
    meta2 = MetaData()
    meta2.reflect(bind=engine)
    assert "render_batches" in meta2.tables
    render_jobs_tbl2 = meta2.tables["render_jobs"]
    render_jobs_tbl2.c.id.type = Uuid()
    render_jobs_tbl2.c.project_id.type = Uuid()
    render_jobs_tbl2.c.timeline_id.type = Uuid()
    render_jobs_tbl2.c.approval_id.type = Uuid()
    if "batch_id" in render_jobs_tbl2.c:
        render_jobs_tbl2.c.batch_id.type = Uuid()

    assert "render_variant_key" in render_jobs_tbl2.c
    assert "batch_id" in render_jobs_tbl2.c

    with engine.connect() as conn:
        row = conn.execute(select(render_jobs_tbl2).where(render_jobs_tbl2.c.id == rj_id)).mappings().first()
        assert row is not None
        assert row["render_variant_key"] == "MASTER"

    # 3. C. BLOCKED DOWNGRADE: Add a second active variant for the same timeline
    rj_id_2 = uuid.uuid4()
    rb_id = uuid.uuid4()
    render_batches_tbl2 = meta2.tables["render_batches"]
    render_batches_tbl2.c.id.type = Uuid()
    render_batches_tbl2.c.project_id.type = Uuid()
    render_batches_tbl2.c.timeline_id.type = Uuid()

    with engine.begin() as conn:
        conn.execute(render_batches_tbl2.insert().values(
            id=rb_id,
            project_id=p_id,
            timeline_id=t_id,
            timeline_version=1,
            status="PROCESSING",
            total_variants=1,
            created_at=now,
            updated_at=now,
        ))
        conn.execute(render_jobs_tbl2.insert().values(
            id=rj_id_2,
            project_id=p_id,
            timeline_id=t_id,
            timeline_version=1,
            approval_id=app_id,
            render_profile="YT_STANDARD_1080P",
            render_variant_key="YT_STANDARD_1080P",
            batch_id=rb_id,
            status="QUEUED",
            idempotency_key=f"render_{p_id}_1_YT_STANDARD_1080P",
            progress=0.0,
            retry_count=0,
            max_retries=3,
            estimated_cost_usd=0.50,
            created_at=now,
            updated_at=now,
        ))

    # Multiple active variants exist on same timeline -> downgrade MUST fail closed
    with pytest.raises(RuntimeError) as exc_info:
        command.downgrade(cfg, "018_cloud_render_workers")
    assert "Downgrade ABORTED" in str(exc_info.value)
    assert "multiple active/reconciliation export variants" in str(exc_info.value)

    # Verify rows & history remain intact
    with engine.connect() as conn:
        all_jobs = conn.execute(select(render_jobs_tbl2).where(render_jobs_tbl2.c.project_id == p_id)).mappings().all()
        assert len(all_jobs) == 2

    # 4. D. COMPLETED HISTORICAL VARIANTS: Mark variants as COMPLETED
    with engine.begin() as conn:
        conn.execute(text("UPDATE render_jobs SET status = 'COMPLETED'"))

    # Now multiple COMPLETED variants exist for same project/timeline
    # Downgrade to 018 SHOULD SUCCEED because COMPLETED is not in QUEUED/CLAIMED/RUNNING/RECONCILIATION_REQUIRED
    command.downgrade(cfg, "018_cloud_render_workers")
    meta3 = MetaData()
    meta3.reflect(bind=engine)
    assert "render_batches" not in meta3.tables
    assert "render_variant_key" not in meta3.tables["render_jobs"].c
    from sqlalchemy import inspect
    insp = inspect(engine)
    indexes = insp.get_indexes("render_jobs")
    active_idx = next((idx for idx in indexes if idx["name"] == "uq_render_jobs_active_timeline"), None)
    assert active_idx is not None, "uq_render_jobs_active_timeline index must be restored on downgrade"
    assert active_idx["column_names"] == ["project_id", "timeline_id"]

    # 5. B. SAFE DOWNGRADE & RE-UPGRADE
    command.upgrade(cfg, "019_export_presets_and_variant_key")
    meta4 = MetaData()
    meta4.reflect(bind=engine)
    assert "render_batches" in meta4.tables
    assert "render_variant_key" in meta4.tables["render_jobs"].c
    engine.dispose()


def test_020_project_archive_lineage_lifecycle(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, text, Uuid
    from sqlalchemy.exc import IntegrityError

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))

    url = f"sqlite:///{tmp_path / 'wp020_migration_test.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to 019
    command.upgrade(cfg, "019_export_presets_and_variant_key")
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)
    assert "source_project_id" not in meta.tables["projects"].c
    assert "imported_historical" not in meta.tables["render_jobs"].c

    # 2. Upgrade to 020
    command.upgrade(cfg, "020_project_archive_lineage")
    meta2 = MetaData()
    meta2.reflect(bind=engine)
    assert "source_project_id" in meta2.tables["projects"].c
    assert "source_archive_checksum" in meta2.tables["projects"].c
    assert "imported_at" in meta2.tables["projects"].c
    assert "imported_historical" in meta2.tables["render_jobs"].c
    assert "execution_disabled" in meta2.tables["render_jobs"].c
    assert "imported_historical" in meta2.tables["generation_jobs"].c
    assert "execution_disabled" in meta2.tables["generation_jobs"].c
    assert "imported_historical" in meta2.tables["usage_ledger"].c

    # Set up tables
    now = datetime.now(timezone.utc)
    p_id = uuid.uuid4()
    t_id = uuid.uuid4()
    s_id = uuid.uuid4()
    shot_id = uuid.uuid4()
    qc_id = uuid.uuid4()
    app_id = uuid.uuid4()

    projects_tbl = meta2.tables["projects"]
    projects_tbl.c.id.type = Uuid()
    timelines_tbl = meta2.tables["assembly_timelines"]
    timelines_tbl.c.id.type = Uuid()
    timelines_tbl.c.project_id.type = Uuid()
    scenes_tbl = meta2.tables["scenes"]
    scenes_tbl.c.id.type = Uuid()
    scenes_tbl.c.project_id.type = Uuid()
    shots_tbl = meta2.tables["shots"]
    shots_tbl.c.id.type = Uuid()
    shots_tbl.c.scene_id.type = Uuid()
    qc_runs_tbl = meta2.tables["qc_runs"]
    qc_runs_tbl.c.id.type = Uuid()
    qc_runs_tbl.c.project_id.type = Uuid()
    qc_runs_tbl.c.timeline_id.type = Uuid()
    approvals_tbl = meta2.tables["production_approvals"]
    approvals_tbl.c.id.type = Uuid()
    approvals_tbl.c.project_id.type = Uuid()
    approvals_tbl.c.timeline_id.type = Uuid()
    approvals_tbl.c.qc_run_id.type = Uuid()
    render_jobs_tbl = meta2.tables["render_jobs"]
    render_jobs_tbl.c.id.type = Uuid()
    render_jobs_tbl.c.project_id.type = Uuid()
    render_jobs_tbl.c.timeline_id.type = Uuid()
    render_jobs_tbl.c.approval_id.type = Uuid()
    generation_jobs_tbl = meta2.tables["generation_jobs"]
    generation_jobs_tbl.c.id.type = Uuid()
    generation_jobs_tbl.c.shot_id.type = Uuid()

    with engine.begin() as conn:
        conn.execute(projects_tbl.insert().values(id=p_id, title="P20", status="DRAFT", created_at=now, updated_at=now))
        conn.execute(timelines_tbl.insert().values(id=t_id, project_id=p_id, version=1, status="APPROVED", created_at=now, updated_at=now))
        conn.execute(scenes_tbl.insert().values(id=s_id, project_id=p_id, scene_number=1, created_at=now, updated_at=now))
        conn.execute(shots_tbl.insert().values(id=shot_id, scene_id=s_id, shot_number=1, shot_type="AI_GENERATED", status="DRAFT", created_at=now, updated_at=now))
        conn.execute(qc_runs_tbl.insert().values(id=qc_id, project_id=p_id, timeline_id=t_id, timeline_version=1, status="PASSED", created_at=now, updated_at=now))
        conn.execute(approvals_tbl.insert().values(id=app_id, project_id=p_id, timeline_id=t_id, timeline_version=1, qc_run_id=qc_id, status="APPROVED", approved_at=now))

    # 3. Test active uniqueness:
    # A historical active render job and a live active render job for the same variant can coexist!
    rj_hist = uuid.uuid4()
    rj_live = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(render_jobs_tbl.insert().values(
            id=rj_hist,
            project_id=p_id,
            timeline_id=t_id,
            timeline_version=1,
            approval_id=app_id,
            render_profile="MASTER_HD",
            render_variant_key="MASTER",
            status="QUEUED",
            imported_historical=True,
            execution_disabled=True,
            idempotency_key=f"hist_{rj_hist}",
            progress=0.0,
            retry_count=0,
            max_retries=3,
            estimated_cost_usd=0.50,
            created_at=now,
            updated_at=now,
        ))
        conn.execute(render_jobs_tbl.insert().values(
            id=rj_live,
            project_id=p_id,
            timeline_id=t_id,
            timeline_version=1,
            approval_id=app_id,
            render_profile="MASTER_HD",
            render_variant_key="MASTER",
            status="QUEUED",
            imported_historical=False,
            execution_disabled=False,
            idempotency_key=f"live_{rj_live}",
            progress=0.0,
            retry_count=0,
            max_retries=3,
            estimated_cost_usd=0.50,
            created_at=now,
            updated_at=now,
        ))

    # A second LIVE active render job for the SAME variant must be rejected
    rj_live_dup = uuid.uuid4()
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(render_jobs_tbl.insert().values(
                id=rj_live_dup,
                project_id=p_id,
                timeline_id=t_id,
                timeline_version=1,
                approval_id=app_id,
                render_profile="MASTER_HD",
                render_variant_key="MASTER",
                status="QUEUED",
                imported_historical=False,
                execution_disabled=False,
                idempotency_key=f"live_{rj_live_dup}",
                progress=0.0,
                retry_count=0,
                max_retries=3,
                estimated_cost_usd=0.50,
                created_at=now,
                updated_at=now,
            ))

    # 4. Fail-closed downgrade check:
    # Because rj_hist and rj_live coexist with active status on the same variant, downgrade MUST FAIL CLOSED
    with pytest.raises(RuntimeError) as exc_info:
        command.downgrade(cfg, "019_export_presets_and_variant_key")
    assert "Downgrade ABORTED" in str(exc_info.value)
    assert "active-status render jobs" in str(exc_info.value)

    # 5. Safe downgrade when duplicate live job is completed
    with engine.begin() as conn:
        conn.execute(render_jobs_tbl.update().where(render_jobs_tbl.c.id == rj_live).values(status="COMPLETED"))

    command.downgrade(cfg, "019_export_presets_and_variant_key")
    meta3 = MetaData()
    meta3.reflect(bind=engine)
    assert "source_project_id" not in meta3.tables["projects"].c
    assert "imported_historical" not in meta3.tables["render_jobs"].c
    engine.dispose()


def test_020_usage_ledger_coexistence_and_fail_closed_downgrade(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, MetaData, Table, select, Uuid
    from sqlalchemy.exc import IntegrityError

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    url = f"sqlite:///{tmp_path / 'wp020_ledger_downgrade.db'}"
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI_OVERRIDE", url)

    # 1. Upgrade to head (020)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)

    projects_tbl = Table("projects", meta, autoload_with=engine)
    projects_tbl.c.id.type = Uuid()
    usage_ledger_tbl = Table("usage_ledger", meta, autoload_with=engine)
    usage_ledger_tbl.c.id.type = Uuid()
    usage_ledger_tbl.c.project_id.type = Uuid()

    p_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(projects_tbl.insert().values(id=p_id, title="Ledger Downgrade Test", status="DRAFT", created_at=now, updated_at=now))

    # 2. Insert imported historical ledger + live ledger with the SAME (provider, provider_event_id)
    ul_hist_id = uuid.uuid4()
    ul_live_id = uuid.uuid4()
    provider_name = "vidu"
    event_id = "shared-event-evt-999"

    with engine.begin() as conn:
        # Imported historical ledger
        conn.execute(usage_ledger_tbl.insert().values(
            id=ul_hist_id,
            project_id=p_id,
            provider=provider_name,
            provider_event_id=event_id,
            operation="VIDEO_GENERATION",
            cost_status="CONFIRMED",
            imported_historical=True,
            created_at=now,
            updated_at=now,
        ))
        # Live ledger with the SAME provider_event_id
        conn.execute(usage_ledger_tbl.insert().values(
            id=ul_live_id,
            project_id=p_id,
            provider=provider_name,
            provider_event_id=event_id,
            operation="VIDEO_GENERATION",
            cost_status="CONFIRMED",
            imported_historical=False,
            created_at=now,
            updated_at=now,
        ))

    # Prove that a second LIVE ledger with the same provider_event_id is rejected by unique index
    ul_live_dup_id = uuid.uuid4()
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(usage_ledger_tbl.insert().values(
                id=ul_live_dup_id,
                project_id=p_id,
                provider=provider_name,
                provider_event_id=event_id,
                operation="VIDEO_GENERATION",
                cost_status="CONFIRMED",
                imported_historical=False,
                created_at=now,
                updated_at=now,
            ))

    # 3. Attempt downgrade: MUST fail closed due to duplicate (provider, provider_event_id)
    with pytest.raises(RuntimeError) as exc_info:
        command.downgrade(cfg, "019_export_presets_and_variant_key")
    assert "Downgrade ABORTED" in str(exc_info.value)
    assert "(provider, provider_event_id)" in str(exc_info.value)

    # 4. Verify ALL migration-020 columns/indexes remain intact (no partial downgrade occurred)
    meta_after = MetaData()
    meta_after.reflect(bind=engine)
    assert "source_project_id" in meta_after.tables["projects"].c
    assert "source_archive_checksum" in meta_after.tables["projects"].c
    assert "imported_historical" in meta_after.tables["usage_ledger"].c
    assert "imported_historical" in meta_after.tables["render_jobs"].c
    assert "execution_disabled" in meta_after.tables["render_jobs"].c
    assert "imported_historical" in meta_after.tables["generation_jobs"].c
    assert "execution_disabled" in meta_after.tables["generation_jobs"].c

    # 5. Verify records remain intact: no history deletion, no ledger mutation
    with engine.connect() as conn:
        hist_row = conn.execute(select(usage_ledger_tbl).where(usage_ledger_tbl.c.id == ul_hist_id)).mappings().first()
        live_row = conn.execute(select(usage_ledger_tbl).where(usage_ledger_tbl.c.id == ul_live_id)).mappings().first()
        assert hist_row is not None
        assert hist_row["provider_event_id"] == event_id
        assert hist_row["imported_historical"] is True
        assert live_row is not None
        assert live_row["provider_event_id"] == event_id
        assert live_row["imported_historical"] is False

    engine.dispose()
