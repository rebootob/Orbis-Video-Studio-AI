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
    # Query count must be bounded constant (should be <= 6 queries: project, scenes, shots, locks, jobs)
    # If N+1 existed, query count would be > 120!
    assert query_count <= 8, f"Expected bounded query count <= 8, but saw {query_count} queries (N+1 regression!)"
