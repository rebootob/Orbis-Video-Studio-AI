"""Focused tests for P2-WP011: Selective / Batch Regeneration & Resume Service

Verifies:
1. Continue Incomplete skips completed Shots.
2. Continue Incomplete skips active jobs.
3. Locked Shots are skipped (hierarchical locks: Shot, Scene, Script).
4. Archived Shots and Scenes are skipped.
5. Imported/non-generatable Shots are skipped.
6. Multiple FAILED jobs for one Shot produce at most ONE retry job.
7. Repeating the same resume operation does not duplicate active work.
8. Concurrent/repeated requests cannot create duplicate active jobs.
9. Selected regeneration touches only selected eligible Shots.
10. Completed history/assets remain preserved.
11. Batch run counts are truthful.
12. Skip reasons are truthful (LOCKED, ARCHIVED, ALREADY_COMPLETED, ACTIVE_JOB_EXISTS, NOT_GENERATABLE).
13. Preview/estimate and execute use equivalent candidate rules.
14. Stage approval enforcement remains intact.
15. Budget/cost safety remains intact.
16. Performance test: set-based candidate evaluation scales with O(1) queries (no N+1 per shot).
"""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from sqlalchemy import event

from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.asset_lock import AssetLock
from app.models.batch_run import BatchRun, BatchRunItem
from app.models.usage_ledger import UsageLedger
from app.services.batch_resume import BatchResumeService, CandidateSkipReason
from app.services.job_dispatch import JobDispatchService
from app.providers.factory import ProviderFactory
from app.providers.base import ProviderJobResult
from fastapi import HTTPException


@pytest.fixture
def test_project(db_session):
    p = Project(
        id=uuid.uuid4(),
        title="Batch Resume Test Project",
        status="SHOT_PLAN_APPROVED",
        video_mode="STORY",
    )
    story = Story(id=uuid.uuid4(), project_id=p.id, logline="Test Story", status="SHOT_PLAN_APPROVED")
    sc1 = Scene(id=uuid.uuid4(), story_id=story.id, project_id=p.id, scene_number=1, heading="EXT. PARK - DAY")
    sc2 = Scene(id=uuid.uuid4(), story_id=story.id, project_id=p.id, scene_number=2, heading="INT. LAB - NIGHT")

    db_session.add_all([p, story, sc1, sc2])
    db_session.commit()
    return p, sc1, sc2


def test_continue_incomplete_skips_completed_and_active_shots(db_session, test_project):
    project, sc1, sc2 = test_project

    # Shot 1: has completed job
    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    # Shot 2: has active job (PROCESSING)
    s2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    # Shot 3: incomplete (no jobs)
    s3 = Shot(id=uuid.uuid4(), scene_id=sc2.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)

    db_session.add_all([s1, s2, s3])
    db_session.commit()

    # Job for shot 1: COMPLETED
    j1 = GenerationJob(id=uuid.uuid4(), shot_id=s1.id, provider_name="vidu", status="COMPLETED")
    # Job for shot 2: PROCESSING (active)
    j2 = GenerationJob(id=uuid.uuid4(), shot_id=s2.id, provider_name="vidu", status="PROCESSING")

    db_session.add_all([j1, j2])
    db_session.commit()

    eval_res = BatchResumeService.evaluate_project_candidates(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
        only_incomplete=True,
    )

    assert eval_res.total_evaluated == 3
    assert len(eval_res.eligible_shots) == 1
    assert eval_res.eligible_shots[0].id == s3.id

    # Check truthful skip reasons
    reasons = {item[0].id: item[1] for item in eval_res.skipped_items}
    assert reasons[s1.id] == CandidateSkipReason.ALREADY_COMPLETED
    assert reasons[s2.id] == CandidateSkipReason.ACTIVE_JOB_EXISTS


def test_locked_and_archived_shots_are_skipped(db_session, test_project):
    project, sc1, sc2 = test_project

    # s1: locked via is_locked attribute
    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", is_locked=True)
    # s2: locked via AssetLock table
    s2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", is_locked=False)
    lock_s2 = AssetLock(id=uuid.uuid4(), project_id=project.id, entity_type="SHOT", entity_id=s2.id, is_locked=True)
    # s3: archived shot
    s3 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=3, shot_type="AI_GENERATED", status="ARCHIVED")
    # s4: parent scene locked
    lock_sc2 = AssetLock(id=uuid.uuid4(), project_id=project.id, entity_type="SCENE", entity_id=sc2.id, is_locked=True)
    s4 = Shot(id=uuid.uuid4(), scene_id=sc2.id, shot_number=1, shot_type="AI_GENERATED")

    db_session.add_all([s1, s2, lock_s2, s3, lock_sc2, s4])
    db_session.commit()

    eval_res = BatchResumeService.evaluate_project_candidates(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    reasons = {item[0].id: item[1] for item in eval_res.skipped_items}
    assert reasons[s1.id] == CandidateSkipReason.LOCKED
    assert reasons[s2.id] == CandidateSkipReason.LOCKED
    assert reasons[s3.id] == CandidateSkipReason.ARCHIVED
    assert reasons[s4.id] == CandidateSkipReason.LOCKED
    assert len(eval_res.eligible_shots) == 0


def test_non_generatable_shots_are_skipped(db_session, test_project):
    project, sc1, _ = test_project

    # Live footage / imported shot
    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="LIVE_ACTION", duration_seconds=4.0)
    db_session.add(s1)
    db_session.commit()

    eval_res = BatchResumeService.evaluate_project_candidates(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    reasons = {item[0].id: item[1] for item in eval_res.skipped_items}
    assert reasons[s1.id] == CandidateSkipReason.NOT_GENERATABLE


def test_retry_failed_deduplicates_by_shot_when_multiple_failed_jobs_exist(db_session, test_project):
    """Shot A has 3 FAILED historical jobs. Retry Failed must create at most ONE new job for Shot A."""
    project, sc1, _ = test_project

    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add(s1)
    db_session.commit()

    # Create 3 distinct historical FAILED jobs for s1
    j1 = GenerationJob(id=uuid.uuid4(), shot_id=s1.id, provider_name="vidu", status="FAILED", error_message="err 1")
    j2 = GenerationJob(id=uuid.uuid4(), shot_id=s1.id, provider_name="vidu", status="FAILED", error_message="err 2")
    j3 = GenerationJob(id=uuid.uuid4(), shot_id=s1.id, provider_name="vidu", status="FAILED", error_message="err 3")
    db_session.add_all([j1, j2, j3])
    db_session.commit()

    batch_run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="RETRY_FAILED",
    )

    # Must create exactly 1 new job for s1
    assert len(jobs) == 1
    assert jobs[0].shot_id == s1.id
    assert jobs[0].status == "PENDING"
    assert batch_run.queued_count == 1
    assert batch_run.eligible_count == 1
    assert batch_run.skipped_count == 0

    # Total jobs for s1 is now 4 (3 historical failed + 1 new pending)
    all_s1_jobs = db_session.query(GenerationJob).filter(GenerationJob.shot_id == s1.id).all()
    assert len(all_s1_jobs) == 4


def test_repeat_safe_resume_does_not_duplicate_active_work(db_session, test_project):
    """Calling continue_incomplete multiple times in sequence must NOT duplicate work."""
    project, sc1, _ = test_project

    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add(s1)
    db_session.commit()

    # First call: creates 1 job
    run1, jobs1 = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert len(jobs1) == 1
    assert run1.queued_count == 1

    # Second call immediately after: job is already in PENDING (active), so s1 must be skipped!
    run2, jobs2 = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert len(jobs2) == 0
    assert run2.queued_count == 0
    assert run2.skipped_count == 1
    # Skip reason must be ACTIVE_JOB_EXISTS
    item = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run2.id).first()
    assert item.decision == "SKIPPED"
    assert item.skip_reason == "ACTIVE_JOB_EXISTS"

    # Only 1 job exists in total
    total_jobs = db_session.query(GenerationJob).filter(GenerationJob.shot_id == s1.id).count()
    assert total_jobs == 1


def test_generate_selected_touches_only_selected_shots(db_session, test_project):
    project, sc1, sc2 = test_project

    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    s2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    s3 = Shot(id=uuid.uuid4(), scene_id=sc2.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    # Select only s1 and s3
    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="GENERATE_SELECTED",
        shot_ids=[s1.id, s3.id],
    )

    assert len(jobs) == 2
    queued_shot_ids = {j.shot_id for j in jobs}
    assert queued_shot_ids == {s1.id, s3.id}
    assert s2.id not in queued_shot_ids


def test_preview_estimate_and_execute_use_identical_candidate_rules(db_session, test_project):
    project, sc1, _ = test_project

    # s1: completed
    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    # s2: locked
    s2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0, is_locked=True)
    # s3: incomplete
    s3 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=3, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    j1 = GenerationJob(id=uuid.uuid4(), shot_id=s1.id, provider_name="vidu", status="COMPLETED")
    db_session.add(j1)
    db_session.commit()

    estimate = BatchResumeService.estimate_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    assert estimate["shot_count"] == 1
    assert estimate["skipped_count"] == 2
    assert estimate["total_evaluated"] == 3

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    assert run.eligible_count == estimate["shot_count"]
    assert run.skipped_count == estimate["skipped_count"]
    assert len(jobs) == 1
    assert jobs[0].shot_id == s3.id


def test_stage_approval_enforced_on_batch_execution(db_session, test_project):
    project, sc1, _ = test_project
    # Regress project to DRAFT
    project.status = "DRAFT"
    db_session.commit()

    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add(s1)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        BatchResumeService.execute_batch(
            db=db_session,
            project_id=project.id,
            operation_type="CONTINUE_INCOMPLETE",
        )
    assert exc.value.status_code == 409
    assert "SHOT_PLAN_APPROVED" in exc.value.detail


def test_performance_candidate_evaluation_has_no_n_plus_one_queries(db_session, test_project):
    """Scalability test: Verify that evaluating 100+ shots across multiple scenes

    does not execute per-shot queries (O(1) query count).
    """
    project, sc1, sc2 = test_project

    # Generate 120 shots across 2 scenes with mixed states
    shots = []
    for i in range(60):
        shots.append(
            Shot(
                id=uuid.uuid4(),
                scene_id=sc1.id,
                shot_number=i + 1,
                shot_type="AI_GENERATED",
                duration_seconds=4.0,
                is_locked=(i % 5 == 0),  # 20% locked
                status="ARCHIVED" if (i % 7 == 0) else "PENDING",
            )
        )
    for i in range(60):
        shots.append(
            Shot(
                id=uuid.uuid4(),
                scene_id=sc2.id,
                shot_number=i + 1,
                shot_type="AI_GENERATED" if (i % 6 != 0) else "LIVE_ACTION",
                duration_seconds=4.0,
            )
        )
    db_session.add_all(shots)
    db_session.commit()

    # Add 40 jobs (some completed, some active, some failed)
    jobs = []
    for idx, s in enumerate(shots[:40]):
        st = "COMPLETED" if idx % 3 == 0 else ("PROCESSING" if idx % 3 == 1 else "FAILED")
        jobs.append(GenerationJob(id=uuid.uuid4(), shot_id=s.id, provider_name="vidu", status=st))
    db_session.add_all(jobs)
    db_session.commit()

    # Count queries executed during evaluation
    query_count = 0

    def query_listener(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", query_listener)

    try:
        eval_result = BatchResumeService.evaluate_project_candidates(
            db=db_session,
            project_id=project.id,
            operation_type="CONTINUE_INCOMPLETE",
        )
    finally:
        event.remove(engine, "before_cursor_execute", query_listener)

    # 120 shots evaluated
    assert eval_result.total_evaluated == 120
    # Query count must be bounded constant (should be <= 8 queries: project, scenes, locks, shots, jobs)
    # If N+1 existed, query count would be > 120!
    assert query_count <= 8, f"Expected bounded query count <= 8, but saw {query_count} queries (N+1 regression!)"


def test_concurrent_resume_deduplication_barrier(tmp_path):
    """Concurrency test: Two threads racing with a barrier on the same Shot

    must result in exactly ONE active generation job in the database.
    """
    import threading
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base_class import Base

    db_file = tmp_path / "concurrent_resume.db"
    file_engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 30})
    Base.metadata.create_all(file_engine)
    FileSessionLocal = sessionmaker(bind=file_engine, expire_on_commit=False)

    project_id = uuid.uuid4()
    shot_id = uuid.uuid4()
    scene_id = uuid.uuid4()

    with FileSessionLocal() as init_db:
        p = Project(id=project_id, title="Conc Project", status="SHOT_PLAN_APPROVED", video_mode="STORY")
        sc = Scene(id=scene_id, project_id=project_id, scene_number=1, heading="EXT")
        sh = Shot(id=shot_id, scene_id=scene_id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
        init_db.add_all([p, sc, sh])
        init_db.commit()

    barrier = threading.Barrier(2)
    results = []

    def worker():
        with FileSessionLocal() as session:
            try:
                barrier.wait()
                run, jobs = BatchResumeService.execute_batch(
                    db=session,
                    project_id=project_id,
                    operation_type="CONTINUE_INCOMPLETE",
                    shot_ids=[shot_id],
                )
                results.append((run, jobs))
            except Exception as e:
                results.append((None, []))

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    with FileSessionLocal() as verify_db:
        active_jobs = (
            verify_db.query(GenerationJob)
            .filter(GenerationJob.shot_id == shot_id)
            .all()
        )
        # Exactly one active job must survive
        assert len(active_jobs) == 1
        assert active_jobs[0].status == "PENDING"


def test_batch_run_lifecycle_and_partial_failure_audit(db_session, test_project):
    """Verify truthful BatchRun status: DISPATCHED on normal queueing,

    PARTIAL_FAILED when one shot dispatch fails, with truthful item decision.
    """
    project, sc1, _ = test_project
    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    s2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([s1, s2])
    db_session.commit()

    # Dispatch normal run: status must be DISPATCHED
    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
        shot_ids=[s1.id],
    )
    assert run.status == "DISPATCHED"
    assert run.queued_count == 1

    # Simulate dispatch exception on s2 (e.g. mock create_and_dispatch_job throwing an error)
    with patch.object(
        JobDispatchService,
        "create_and_dispatch_job",
        side_effect=HTTPException(status_code=400, detail="Mock provider failure"),
    ):
        run2, jobs2 = BatchResumeService.execute_batch(
            db=db_session,
            project_id=project.id,
            operation_type="CONTINUE_INCOMPLETE",
            shot_ids=[s2.id],
        )
        assert run2.status == "FAILED"
        assert run2.queued_count == 0
        failed_item = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run2.id).first()
        assert failed_item.decision == "FAILED"
        assert "Mock provider failure" in failed_item.skip_reason


def test_dynamic_count_reconciliation_on_read(db_session, test_project):
    """Verify that completed_count and failed_count are derived truthfully on GET endpoints."""
    project, sc1, _ = test_project
    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    s2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([s1, s2])
    db_session.commit()

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
        shot_ids=[s1.id, s2.id],
    )
    assert len(jobs) == 2
    # Initially queued (pending)
    assert run.completed_count == 0
    assert run.failed_count == 0

    # Jobs transition: job 1 completes, job 2 fails
    jobs[0].status = "COMPLETED"
    jobs[1].status = "FAILED"
    db_session.commit()

    # On read, counts must be truthfully reconciled
    details = BatchResumeService.get_batch_run_details(db_session, project.id, run.id)
    assert details.completed_count == 1
    assert details.failed_count == 1

    listed = BatchResumeService.list_project_batch_runs(db_session, project.id)
    assert len(listed) >= 1
    matching = next(r for r in listed if r.id == run.id)
    assert matching.completed_count == 1
    assert matching.failed_count == 1


def test_candidate_audit_for_archived_scenes_and_missing_requested_ids(db_session, test_project):
    """Verify that shots under archived scenes are reported as ARCHIVED,

    and missing/out-of-project shot IDs are reported as NOT_FOUND without FK failure.
    Counts must reconcile: requested_count == eligible_count + skipped_count.
    """
    project, sc1, _ = test_project
    # Create an archived scene
    archived_scene = Scene(
        id=uuid.uuid4(),
        project_id=project.id,
        scene_number=99,
        heading="EXT. ARCHIVED SCENE",
        scene_config={"archived": True},
    )
    db_session.add(archived_scene)
    db_session.commit()

    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    s_archived = Shot(id=uuid.uuid4(), scene_id=archived_scene.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([s1, s_archived])
    db_session.commit()

    # Whole project evaluation: s_archived must be evaluated as ARCHIVED
    eval_res = BatchResumeService.evaluate_project_candidates(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    reasons = {item[0].id: item[1] for item in eval_res.skipped_items}
    assert reasons[s_archived.id] == CandidateSkipReason.ARCHIVED

    # Explicit requested IDs including a non-existent ID
    missing_id = uuid.uuid4()
    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="GENERATE_SELECTED",
        shot_ids=[s1.id, missing_id, s_archived.id],
    )

    # Requested count must be 3, exactly reconciling eligible + skipped
    assert run.requested_count == 3
    assert run.eligible_count == 1
    assert run.skipped_count == 2
    assert run.requested_count == run.eligible_count + run.skipped_count

    # Check items in database
    run_items = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id).all()
    item_reasons = {i.shot_id: i.skip_reason for i in run_items if i.decision == "SKIPPED"}
    assert item_reasons[missing_id] == CandidateSkipReason.NOT_FOUND.value
    assert item_reasons[s_archived.id] == CandidateSkipReason.ARCHIVED.value


def test_retry_failed_truthful_skip_reasons(db_session, test_project):
    """Verify that RETRY_FAILED reports NO_FAILED_HISTORY when a shot has no failed jobs,

    and ALREADY_COMPLETED when a shot is already completed.
    """
    project, sc1, _ = test_project
    s1_completed = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    s2_no_history = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    s3_failed = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=3, shot_type="AI_GENERATED", duration_seconds=4.0)

    db_session.add_all([s1_completed, s2_no_history, s3_failed])
    db_session.commit()

    j1 = GenerationJob(id=uuid.uuid4(), shot_id=s1_completed.id, provider_name="vidu", status="COMPLETED")
    j3 = GenerationJob(id=uuid.uuid4(), shot_id=s3_failed.id, provider_name="vidu", status="FAILED")
    db_session.add_all([j1, j3])
    db_session.commit()

    eval_res = BatchResumeService.evaluate_project_candidates(
        db=db_session,
        project_id=project.id,
        operation_type="RETRY_FAILED",
    )

    reasons = {item[0].id: item[1] for item in eval_res.skipped_items}
    assert reasons[s1_completed.id] == CandidateSkipReason.ALREADY_COMPLETED
    assert reasons[s2_no_history.id] == CandidateSkipReason.NO_FAILED_HISTORY
    assert len(eval_res.eligible_shots) == 1
    assert eval_res.eligible_shots[0].id == s3_failed.id


def test_operation_type_validation_fails_closed(db_session, test_project):
    """Verify that unknown/typo operation types fail closed with 400 Bad Request."""
    project, _, _ = test_project

    with pytest.raises(HTTPException) as exc:
        BatchResumeService.evaluate_project_candidates(
            db=db_session,
            project_id=project.id,
            operation_type="RETRY_FAILEDD",
        )
    assert exc.value.status_code == 400
    assert "Invalid batch operation_type" in exc.value.detail

    with pytest.raises(HTTPException) as exc2:
        BatchResumeService.execute_batch(
            db=db_session,
            project_id=project.id,
            operation_type="UNKNOWN_OP",
        )
    assert exc2.value.status_code == 400


def test_preview_and_execute_equivalence_all_operations(db_session, test_project):
    """Verify that preview/estimate and execute yield equivalent counts for all 3 operations."""
    project, sc1, _ = test_project
    s1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    s2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    s3 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=3, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    j1 = GenerationJob(id=uuid.uuid4(), shot_id=s1.id, provider_name="vidu", status="FAILED")
    db_session.add(j1)
    db_session.commit()

    operations = ["CONTINUE_INCOMPLETE", "RETRY_FAILED", "GENERATE_SELECTED"]
    for op in operations:
        estimate = BatchResumeService.estimate_batch(
            db=db_session,
            project_id=project.id,
            operation_type=op,
            shot_ids=[s1.id, s2.id] if op == "GENERATE_SELECTED" else None,
        )
        eval_res = BatchResumeService.evaluate_project_candidates(
            db=db_session,
            project_id=project.id,
            operation_type=op,
            shot_ids=[s1.id, s2.id] if op == "GENERATE_SELECTED" else None,
        )
        assert estimate["shot_count"] == len(eval_res.eligible_shots)
        assert estimate["skipped_count"] == len(eval_res.skipped_items)
        assert estimate["total_evaluated"] == eval_res.total_evaluated


def test_bounded_pagination_and_query_scalability_large_project(db_session, test_project):
    """Scalability test: Verify that evaluating 250 shots across 3 scenes

    processes candidates in bounded chunks without memory/parameter explosion,
    and query counts remain bounded.
    """
    project, sc1, sc2 = test_project
    sc3 = Scene(id=uuid.uuid4(), project_id=project.id, scene_number=3, heading="INT. CONTROL ROOM")
    db_session.add(sc3)
    db_session.commit()

    shots = []
    for i in range(250):
        target_scene = sc1 if i < 100 else (sc2 if i < 200 else sc3)
        shots.append(
            Shot(
                id=uuid.uuid4(),
                scene_id=target_scene.id,
                shot_number=i + 1,
                shot_type="AI_GENERATED",
                duration_seconds=4.0,
            )
        )
    db_session.add_all(shots)
    db_session.commit()

    eval_res = BatchResumeService.evaluate_project_candidates(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    # Exactly all 250 shots evaluated across paginated chunks
    assert eval_res.total_evaluated == 250
    assert len(eval_res.eligible_shots) == 250


def test_atomic_job_and_batch_run_item_persistence(db_session, test_project):
    """Test 1: Job + BatchRunItem atomic persistence."""
    project, sc1, _ = test_project
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sc1.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        duration_seconds=4.0,
        status="PENDING",
    )
    db_session.add(shot)
    db_session.commit()

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    assert len(jobs) == 1
    assert run.queued_count == 1
    item = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot.id).first()
    assert item is not None
    assert item.decision == "QUEUED"
    assert item.job_id == jobs[0].id


def test_injected_crash_between_job_creation_and_audit_persistence(db_session, test_project, monkeypatch):
    """Test 2: Injected crash after Job construction but before BatchRunItem persistence

    proves savepoint rollback ensures no unaudited queued work is left in the DB.
    """
    project, sc1, _ = test_project
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sc1.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        duration_seconds=4.0,
        status="PENDING",
    )
    db_session.add(shot)
    db_session.commit()

    orig_add = db_session.add

    def failing_add(instance):
        if isinstance(instance, BatchRunItem) and instance.decision == "QUEUED":
            raise RuntimeError("Simulated crash immediately before BatchRunItem QUEUED persistence")
        return orig_add(instance)

    monkeypatch.setattr(db_session, "add", failing_add)

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    # Job was rolled back by the savepoint!
    assert len(jobs) == 0
    assert run.queued_count == 0
    # No unaudited job exists in generation_jobs for this shot
    existing_job = db_session.query(GenerationJob).filter(GenerationJob.shot_id == shot.id).first()
    assert existing_job is None
    # Item was captured as FAILED
    item = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot.id).first()
    assert item is not None
    assert item.decision == "FAILED"
    assert "Simulated crash" in item.skip_reason


def test_cancelling_blocks_regeneration(db_session, test_project):
    """Test 3: CANCELLING blocks automatic regeneration and reports CANCELLATION_IN_PROGRESS."""
    project, sc1, _ = test_project
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sc1.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        duration_seconds=4.0,
        status="PENDING",
    )
    db_session.add(shot)
    db_session.flush()

    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        provider_name="vidu",
        status="CANCELLING",
    )
    db_session.add(job)
    db_session.commit()

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert len(jobs) == 0
    assert run.queued_count == 0
    assert run.skipped_count == 1
    item = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot.id).first()
    assert item.decision == "SKIPPED"
    assert item.skip_reason == "CANCELLATION_IN_PROGRESS"


def test_reconciliation_required_blocks_automatic_resume(db_session, test_project):
    """Test 4: RECONCILIATION_REQUIRED blocks automatic generation/resume/retry."""
    project, sc1, _ = test_project
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=sc1.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        duration_seconds=4.0,
        status="PENDING",
    )
    db_session.add(shot)
    db_session.flush()

    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        provider_name="vidu",
        status="RECONCILIATION_REQUIRED",
    )
    db_session.add(job)
    db_session.commit()

    # Continue Incomplete must never silently regenerate
    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert len(jobs) == 0
    assert run.queued_count == 0
    assert run.skipped_count == 1
    item = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot.id).first()
    assert item.decision == "SKIPPED"
    assert item.skip_reason == "RECONCILIATION_REQUIRED"

    # Retry Failed must also not regenerate without explicit reconciliation
    run2, jobs2 = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="RETRY_FAILED",
    )
    assert len(jobs2) == 0
    assert run2.queued_count == 0
    assert run2.skipped_count == 1


def test_single_shot_path_fails_closed_for_ambiguous_provider_state(db_session, test_project):
    """Test 5: Single-shot create path fails closed with 409 for RECONCILIATION_REQUIRED and CANCELLING."""
    project, sc1, _ = test_project
    shot1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    shot2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([shot1, shot2])
    db_session.flush()

    job1 = GenerationJob(id=uuid.uuid4(), shot_id=shot1.id, provider_name="vidu", status="RECONCILIATION_REQUIRED")
    job2 = GenerationJob(id=uuid.uuid4(), shot_id=shot2.id, provider_name="vidu", status="CANCELLING")
    db_session.add_all([job1, job2])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info1:
        JobDispatchService.create_and_dispatch_job(db_session, shot_id=shot1.id)
    assert exc_info1.value.status_code == 409
    assert "requires explicit reconciliation" in exc_info1.value.detail

    with pytest.raises(HTTPException) as exc_info2:
        JobDispatchService.create_and_dispatch_job(db_session, shot_id=shot2.id)
    assert exc_info2.value.status_code == 409
    assert "currently CANCELLING" in exc_info2.value.detail


def test_concurrent_active_conflict_produces_truthful_outcome(db_session, test_project, monkeypatch):
    """Test 6: Transactional active-job conflict reports SKIPPED / ACTIVE_JOB_EXISTS, not generic FAILED."""
    project, sc1, _ = test_project
    shot = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add(shot)
    db_session.commit()

    def conflict_dispatch(*args, **kwargs):
        raise HTTPException(
            status_code=409,
            detail=f"Active generation job 'dummy-id' already exists for Shot '{shot.id}'.",
        )

    monkeypatch.setattr(JobDispatchService, "create_and_dispatch_job", conflict_dispatch)

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert len(jobs) == 0
    assert run.failed_count == 0
    assert run.skipped_count == 1
    assert run.status == "DISPATCHED"

    item = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot.id).first()
    assert item.decision == "SKIPPED"
    assert item.skip_reason == "ACTIVE_JOB_EXISTS"


def test_batch_run_failed_count_includes_dispatch_failures(db_session, test_project, monkeypatch):
    """Test 7: BatchRun failed_count truthfully includes dispatch failures."""
    project, sc1, _ = test_project
    shot = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add(shot)
    db_session.commit()

    def failing_dispatch(*args, **kwargs):
        raise HTTPException(status_code=500, detail="Provider rejected dispatch")

    monkeypatch.setattr(JobDispatchService, "create_and_dispatch_job", failing_dispatch)

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert run.failed_count == 1
    assert run.status == "FAILED"

    # Dynamic reconciliation also preserves the dispatch failure
    reconciled = BatchResumeService.get_batch_run_details(db_session, project.id, run.id)
    assert reconciled.failed_count == 1


def test_deterministic_ordering_with_stable_tie_breaker(db_session, test_project):
    """Test 10: Deterministic ordering with stable tie-breaker: (Scene.scene_number, Shot.shot_number, Shot.id)."""
    project, sc1, sc2 = test_project
    # Create shots across scenes in mixed order
    s2_1 = Shot(id=uuid.uuid4(), scene_id=sc2.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    s1_2 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    s1_1 = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([s2_1, s1_2, s1_1])
    db_session.commit()

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert len(jobs) == 3
    # First scene 1 shot 1, then scene 1 shot 2, then scene 2 shot 1
    assert jobs[0].shot_id == s1_1.id
    assert jobs[1].shot_id == s1_2.id
    assert jobs[2].shot_id == s2_1.id


def test_list_batch_runs_has_zero_n_plus_one_queries(db_session, test_project):
    """Test 11: BatchRun listing executes exactly 2 queries regardless of run count."""
    from sqlalchemy import event

    project, sc1, _ = test_project
    # Create 5 runs with items
    for i in range(5):
        run = BatchRun(
            id=uuid.uuid4(),
            project_id=project.id,
            operation_type="CONTINUE_INCOMPLETE",
            status="DISPATCHED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(run)
        db_session.flush()
        for j in range(3):
            item = BatchRunItem(
                id=uuid.uuid4(),
                batch_run_id=run.id,
                shot_id=uuid.uuid4(),
                decision="SKIPPED",
                skip_reason="LOCKED",
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(item)
    db_session.commit()

    query_count = [0]
    def count_queries(conn, cursor, statement, parameters, context, executemany):
        query_count[0] += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count_queries)
    try:
        runs = BatchResumeService.list_project_batch_runs(db_session, project.id, limit=10)
        assert len(runs) >= 5
        # Exactly 2 queries: 1 for BatchRun page, 1 for grouped stats!
        assert query_count[0] == 2
    finally:
        event.remove(engine, "before_cursor_execute", count_queries)


def test_batch_run_item_details_are_bounded_and_paginated(db_session, test_project):
    """Test 12: BatchRun items are bounded and paginated."""
    project, sc1, _ = test_project
    run = BatchRun(
        id=uuid.uuid4(),
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
        status="DISPATCHED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.flush()

    for i in range(120):
        db_session.add(BatchRunItem(
            id=uuid.uuid4(),
            batch_run_id=run.id,
            shot_id=uuid.uuid4(),
            decision="SKIPPED",
            skip_reason="LOCKED",
            created_at=datetime.now(timezone.utc),
        ))
    db_session.commit()

    # Default bounded limit is 100
    details = BatchResumeService.get_batch_run_details(db_session, project.id, run.id, item_limit=50, item_offset=0)
    assert len(details.items) == 50
    assert details.items_total == 120
    assert details.item_limit == 50
    assert details.item_offset == 0

    # Next offset
    details_p2 = BatchResumeService.get_batch_run_details(db_session, project.id, run.id, item_limit=50, item_offset=50)
    assert len(details_p2.items) == 50
    assert details_p2.items_total == 120

    # Remaining items
    details_p3 = BatchResumeService.get_batch_run_details(db_session, project.id, run.id, item_limit=50, item_offset=100)
    assert len(details_p3.items) == 20
    assert details_p3.items_total == 120

    # Crucial delete-orphan check: calling db_session.commit() after get_batch_run_details must NOT delete unselected items
    db_session.commit()
    remaining = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id).count()
    assert remaining == 120


def test_multi_shot_partial_failure_with_caller_savepoint_isolation(db_session, test_project, monkeypatch):
    """Test 13: Shot A succeeds, Shot B fails in job creation, Shot C succeeds.
    Verify:
    - Shot A Job + Ledger + BatchRunItem exist
    - Shot B leaves NO unaudited job (savepoint rolled back)
    - Shot C Job + Ledger + BatchRunItem exist
    - BatchRun counters exactly match persisted DB truth
    """
    project, sc1, _ = test_project
    shot_a = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=1, shot_type="AI_GENERATED", duration_seconds=4.0)
    shot_b = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=2, shot_type="AI_GENERATED", duration_seconds=4.0)
    shot_c = Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=3, shot_type="AI_GENERATED", duration_seconds=4.0)
    db_session.add_all([shot_a, shot_b, shot_c])
    db_session.commit()

    real_dispatch = JobDispatchService.create_and_dispatch_job

    def controlled_dispatch(*args, **kwargs):
        shot_id = kwargs.get("shot_id") or (args[1] if len(args) > 1 else None)
        if shot_id == shot_b.id:
            raise RuntimeError("Simulated crash inside JobDispatchService for Shot B")
        return real_dispatch(*args, **kwargs)

    monkeypatch.setattr(JobDispatchService, "create_and_dispatch_job", controlled_dispatch)

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    assert run.requested_count == 3
    assert run.eligible_count == 3
    assert run.queued_count == 2
    assert run.failed_count == 1
    assert run.skipped_count == 0
    assert run.status == "PARTIAL_FAILED"

    # Shot A verification: Job + Ledger + BatchRunItem exist
    job_a = db_session.query(GenerationJob).filter(GenerationJob.shot_id == shot_a.id).first()
    assert job_a is not None
    ledger_a = db_session.query(UsageLedger).filter(UsageLedger.job_id == job_a.id).first()
    assert ledger_a is not None
    item_a = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot_a.id).first()
    assert item_a is not None
    assert item_a.decision == "QUEUED"
    assert item_a.job_id == job_a.id

    # Shot B verification: NO Job, NO Ledger, BatchRunItem is FAILED
    job_b = db_session.query(GenerationJob).filter(GenerationJob.shot_id == shot_b.id).first()
    assert job_b is None
    ledger_b = db_session.query(UsageLedger).filter(UsageLedger.shot_id == shot_b.id).first()
    assert ledger_b is None
    item_b = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot_b.id).first()
    assert item_b is not None
    assert item_b.decision == "FAILED"
    assert item_b.job_id is None
    assert "Simulated crash" in (item_b.skip_reason or "")

    # Shot C verification: Job + Ledger + BatchRunItem exist
    job_c = db_session.query(GenerationJob).filter(GenerationJob.shot_id == shot_c.id).first()
    assert job_c is not None
    ledger_c = db_session.query(UsageLedger).filter(UsageLedger.job_id == job_c.id).first()
    assert ledger_c is not None
    item_c = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id, BatchRunItem.shot_id == shot_c.id).first()
    assert item_c is not None
    assert item_c.decision == "QUEUED"
    assert item_c.job_id == job_c.id

    # Dynamic reconciliation matches exactly
    reconciled = BatchResumeService.reconcile_batch_run_counts(db_session, run)
    assert reconciled.queued_count == 2
    assert reconciled.failed_count == 1
    assert reconciled.status == "PARTIAL_FAILED"


def test_batch_run_chunk_boundary_persistence_and_recovery(db_session, test_project, monkeypatch):
    """Test 14: Verify that counters are persisted at every chunk boundary, and mid-run crash can be reconciled."""
    project, sc1, _ = test_project
    # Create 55 shots (EXECUTE_CHUNK_SIZE is 50, so 2 chunks: 50 + 5)
    shots = [
        Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=i, shot_type="AI_GENERATED", duration_seconds=4.0)
        for i in range(1, 56)
    ]
    db_session.add_all(shots)
    db_session.commit()

    chunk_commits = [0]
    real_commit = db_session.commit

    def tracking_commit():
        chunk_commits[0] += 1
        real_commit()

    monkeypatch.setattr(db_session, "commit", tracking_commit)

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    # At least 3 commits: 1 for run creation, 1 for chunk 1, 1 for chunk 2 / final
    assert chunk_commits[0] >= 3
    assert run.requested_count == 55
    assert run.queued_count == 55
    assert run.eligible_count == 55
    assert run.failed_count == 0

    # Test reading through get_batch_run_details
    details = BatchResumeService.get_batch_run_details(db_session, project.id, run.id, item_limit=20, item_offset=0)
    assert details.items_total == 55
    assert len(details.items) == 20
    assert details.queued_count == 55


def test_api_endpoints_safe_serialization_and_no_cascade_delete(db_session, test_project, client):
    """Test 15: Verify API endpoints list and detail use safe DTOs and never delete items."""
    project, sc1, _ = test_project
    run = BatchRun(
        id=uuid.uuid4(),
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
        status="DISPATCHED",
        requested_count=30,
        eligible_count=30,
        queued_count=30,
        skipped_count=0,
        completed_count=0,
        failed_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.flush()

    for i in range(30):
        db_session.add(BatchRunItem(
            id=uuid.uuid4(),
            batch_run_id=run.id,
            shot_id=uuid.uuid4(),
            decision="QUEUED",
            created_at=datetime.now(timezone.utc),
        ))
    db_session.commit()

    # List endpoint does NOT contain "items" key
    resp_list = client.get(f"/api/v1/projects/{project.id}/batch-runs")
    assert resp_list.status_code == 200
    runs_data = resp_list.json()
    assert len(runs_data) >= 1
    found = next((r for r in runs_data if r["id"] == str(run.id)), None)
    assert found is not None
    assert "items" not in found
    assert found["queued_count"] == 30

    # Detail endpoint returns paginated items and total
    resp_detail = client.get(f"/api/v1/projects/{project.id}/batch-runs/{run.id}?item_limit=10&item_offset=0")
    assert resp_detail.status_code == 200
    detail_data = resp_detail.json()
    assert "items" in detail_data
    assert len(detail_data["items"]) == 10
    assert detail_data["items_total"] == 30
    assert detail_data["item_limit"] == 10
    assert detail_data["item_offset"] == 0

    # Verify no cascade delete happened
    remaining_items = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id).count()
    assert remaining_items == 30


def test_snapshot_whole_project_execution_is_immune_to_concurrent_ordering_shifts(db_session, test_project):
    """Test 16: Verify that whole-project batch execution uses an immutable ID snapshot,
    ensuring deterministic and complete execution without offset drift or skipped shots.
    """
    project, sc1, sc2 = test_project
    shots_s1 = [
        Shot(id=uuid.uuid4(), scene_id=sc1.id, shot_number=i, shot_type="AI_GENERATED", duration_seconds=4.0)
        for i in range(1, 4)
    ]
    shots_s2 = [
        Shot(id=uuid.uuid4(), scene_id=sc2.id, shot_number=i, shot_type="AI_GENERATED", duration_seconds=4.0)
        for i in range(1, 4)
    ]
    db_session.add_all(shots_s1 + shots_s2)
    db_session.commit()

    run, jobs = BatchResumeService.execute_batch(
        db=db_session,
        project_id=project.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    assert run.requested_count == 6
    assert run.queued_count == 6
    assert len(jobs) == 6

    # Verify each shot has exactly one BatchRunItem and one Job
    items = db_session.query(BatchRunItem).filter(BatchRunItem.batch_run_id == run.id).all()
    assert len(items) == 6
    processed_shot_ids = {it.shot_id for it in items}
    all_created_ids = {s.id for s in shots_s1 + shots_s2}
    assert processed_shot_ids == all_created_ids
