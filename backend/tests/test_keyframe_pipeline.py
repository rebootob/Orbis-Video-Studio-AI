import uuid
import asyncio
import pytest
from datetime import datetime, timezone
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger
from app.models.asset import Asset
from app.models.asset_lock import AssetLock
from app.providers.image.mock_adapter import MockImageProviderAdapter
from app.providers.image.base import ImageGenerationParams, ReferenceImageInput
from app.providers.image.factory import ImageProviderFactory
from app.services.image_generation.continuity_mapper import ContinuityMapper
from app.services.keyframe_generation import KeyframeGenerationService
from app.services.production_orchestrator import ProductionOrchestrator
from app.services.creative_generation.fake_provider import FakeCreativeGenerationProvider
from app.services.creative_generation.factory import get_creative_provider
from app.services.pricing import CostStatus
from app.services.budget import BudgetService
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# 1. Provider Adapter Tests
# ---------------------------------------------------------------------------
def test_mock_image_adapter_deterministic_svg():
    adapter = MockImageProviderAdapter()
    params = ImageGenerationParams(
        shot_id=str(uuid.uuid4()),
        prompt="A neon cybernetic detective standing in rain",
        aspect_ratio="16:9",
        seed=42,
        negative_prompt="blurry, low quality",
        reference_images=[
            ReferenceImageInput(type="character", url="https://mock/hero.png")
        ]
    )

    result = asyncio.run(adapter.generate_image(params))
    assert result.status == "COMPLETED"
    assert result.content_type == "image/svg+xml"
    assert result.image_data is not None
    assert len(result.image_data) > 0
    svg_str = result.image_data.decode("utf-8")
    assert "<svg" in svg_str
    assert "1280" in svg_str
    assert "720" in svg_str


def test_mock_image_adapter_simulated_failure_and_reconciliation():
    adapter = MockImageProviderAdapter()

    # Test failure
    fail_params = ImageGenerationParams(
        shot_id=str(uuid.uuid4()),
        prompt="A failed render",
        provider_specific_params={"simulate_failure": True}
    )
    fail_result = asyncio.run(adapter.generate_image(fail_params))
    assert fail_result.status == "FAILED"
    assert fail_result.error_code == "PROVIDER_ERROR"
    assert fail_result.retryable is True

    # Test reconciliation
    recon_params = ImageGenerationParams(
        shot_id=str(uuid.uuid4()),
        prompt="An uncertain render",
        provider_specific_params={"simulate_reconciliation": True}
    )
    recon_result = asyncio.run(adapter.generate_image(recon_params))
    assert recon_result.submission_uncertain is True
    assert recon_result.error_code == "SUBMISSION_UNCERTAIN"


# ---------------------------------------------------------------------------
# 2. Continuity Mapper Tests
# ---------------------------------------------------------------------------
def test_continuity_mapper_extracts_references(db_session):
    p = Project(title="Continuity Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1, heading="INT. LAB - NIGHT", setting="High-tech lab")
    db_session.add(sc)
    db_session.commit()

    shot = Shot(
        scene_id=sc.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="Scientist inspecting glowing vial",
        camera="Close-up",
        subject="Dr. Aris",
        action="Examining sample",
    )
    db_session.add(shot)
    db_session.commit()

    image_params = ContinuityMapper.map_shot_to_image_params(
        db=db_session,
        project_id=p.id,
        shot=shot,
    )

    assert "Scientist inspecting glowing vial" in image_params.prompt
    assert image_params.aspect_ratio == "16:9"


# ---------------------------------------------------------------------------
# 3. Single Shot Keyframe Generation & Lineage
# ---------------------------------------------------------------------------
def test_generate_shot_keyframe_success(db_session):
    p = Project(title="Single Shot Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1, heading="EXT. DESERT - DAY")
    db_session.add(sc)
    db_session.commit()

    shot = Shot(
        scene_id=sc.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="Endless sand dunes under harsh sun",
    )
    db_session.add(shot)
    db_session.commit()

    asset, job = KeyframeGenerationService.generate_shot_keyframe(
        db=db_session,
        shot_id=shot.id,
        project_id=p.id,
    )

    assert asset is not None
    assert asset.asset_type == "KEYFRAME"
    assert asset.project_id == p.id
    assert job is not None
    assert job.job_type == "IMAGE"
    assert job.status == "COMPLETED"

    db_session.refresh(shot)
    assert shot.keyframe_asset_id == asset.id

    # Verify UsageLedger record
    ledger = db_session.query(UsageLedger).filter(UsageLedger.job_id == job.id).first()
    assert ledger is not None
    assert ledger.operation == "IMAGE_GENERATION"
    assert ledger.project_id == p.id


def test_generate_shot_keyframe_blocks_on_active_job(db_session):
    p = Project(title="Active Job Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    shot = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="A shot")
    db_session.add(shot)
    db_session.commit()

    # Insert an active GenerationJob
    active_job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        job_type="IMAGE",
        provider_name="mock_image",
        status="PROCESSING",
    )
    db_session.add(active_job)
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        KeyframeGenerationService.generate_shot_keyframe(
            db=db_session,
            shot_id=shot.id,
            project_id=p.id,
        )
    assert "already has an active generation job" in str(exc_info.value)


def test_generate_shot_keyframe_respects_locks(db_session):
    p = Project(title="Locked Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    shot = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", is_locked=True)
    db_session.add(shot)
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        KeyframeGenerationService.generate_shot_keyframe(
            db=db_session,
            shot_id=shot.id,
            project_id=p.id,
        )
    assert "locked" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 4. Batch Operations (CONTINUE_INCOMPLETE, GENERATE_SELECTED, RETRY_FAILED)
# ---------------------------------------------------------------------------
def test_execute_keyframe_batch_continue_incomplete(db_session):
    p = Project(title="Batch Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    s1 = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="Shot 1")
    s2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED", visual_prompt="Shot 2")
    db_session.add_all([s1, s2])
    db_session.commit()

    batch_run, jobs = KeyframeGenerationService.execute_keyframe_batch(
        db=db_session,
        project_id=p.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    assert batch_run.completed_count == 2
    assert batch_run.failed_count == 0
    assert batch_run.skipped_count == 0
    assert len(jobs) == 2

    db_session.refresh(s1)
    db_session.refresh(s2)
    assert s1.keyframe_asset_id is not None
    assert s2.keyframe_asset_id is not None

    # Verify project stage advanced to IMAGES_GENERATED
    db_session.refresh(p)
    assert p.status == "IMAGES_GENERATED"


def test_execute_keyframe_batch_selected_shots(db_session):
    p = Project(title="Selected Batch Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    s1 = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="Shot 1")
    s2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED", visual_prompt="Shot 2")
    db_session.add_all([s1, s2])
    db_session.commit()

    # Generate only shot 1
    batch_run, jobs = KeyframeGenerationService.execute_keyframe_batch(
        db=db_session,
        project_id=p.id,
        operation_type="GENERATE_SELECTED",
        shot_ids=[s1.id],
    )

    assert batch_run.completed_count == 1
    assert len(jobs) == 1

    db_session.refresh(s1)
    db_session.refresh(s2)
    assert s1.keyframe_asset_id is not None
    assert s2.keyframe_asset_id is None

    # Project should not advance to IMAGES_GENERATED because s2 still lacks a keyframe
    db_session.refresh(p)
    assert p.status == "SHOT_PLAN_APPROVED"


# ---------------------------------------------------------------------------
# 5. Full Orchestrator Integration & AUTO Mode Cost Gate
# ---------------------------------------------------------------------------
def test_orchestration_api_keyframe_flow(client, db_session):
    fake_provider = FakeCreativeGenerationProvider()
    client.app.dependency_overrides[get_creative_provider] = lambda: fake_provider

    p = Project(title="API Test Project", video_mode="SHORT", status="DRAFT", automation_mode="MANUAL")
    db_session.add(p)
    db_session.commit()
    p_id = str(p.id)

    # 1. Generate Storyboard
    client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_STORYBOARD"})
    client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "STORYBOARD_GENERATED"})

    # 2. Generate Shot Plan
    client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "GENERATE_SHOT_PLAN"})
    client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "SHOT_PLAN_GENERATED"})

    # 3. Inspect state at SHOT_PLAN_APPROVED -> recommends START_KEYFRAME_GENERATION
    st = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st["current_stage"] == "SHOT_PLAN_APPROVED"
    assert st["recommended_action"]["action"] == "START_KEYFRAME_GENERATION"
    assert st["recommended_action"]["is_chargeable"] is True

    # 4. Execute START_KEYFRAME_GENERATION
    kf_res = client.post(f"/api/v1/projects/{p_id}/orchestration/execute", json={"action": "START_KEYFRAME_GENERATION"}).json()
    assert kf_res["success"] is True
    assert kf_res["to_stage"] == "IMAGES_GENERATED"

    # 5. Inspect state at IMAGES_GENERATED -> recommends APPROVE_IMAGES
    st2 = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st2["current_stage"] == "IMAGES_GENERATED"
    assert st2["recommended_action"]["action"] == "APPROVE_IMAGES"

    # 6. Approve images -> transitions to IMAGES_APPROVED
    appr_res = client.post(f"/api/v1/projects/{p_id}/orchestration/approve", json={"stage": "IMAGES_GENERATED"}).json()
    assert appr_res["to_stage"] == "IMAGES_APPROVED"

    # 7. At IMAGES_APPROVED, recommends START_VIDEO_GENERATION
    st3 = client.get(f"/api/v1/projects/{p_id}/orchestration").json()
    assert st3["current_stage"] == "IMAGES_APPROVED"
    assert st3["recommended_action"]["action"] == "START_VIDEO_GENERATION"


def test_shots_endpoint_returns_keyframe_url(client, db_session):
    p = Project(title="Shot API Keyframe Project", video_mode="SHORT", status="IMAGES_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    shot = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="A prompt")
    db_session.add(shot)
    db_session.commit()

    # Generate keyframe for shot
    asset, _ = KeyframeGenerationService.generate_shot_keyframe(db=db_session, shot_id=shot.id, project_id=p.id)

    # Call GET /shots/{shot_id}
    res = client.get(f"/api/v1/shots/{shot.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["keyframe_asset_id"] == str(asset.id)
    assert data["keyframe_url"] is not None
    assert str(asset.id)[:8] in data["keyframe_url"]

    # Call GET /scenes/{scene_id}/shots
    list_res = client.get(f"/api/v1/scenes/{sc.id}/shots")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data) == 1
    assert list_data[0]["keyframe_asset_id"] == str(asset.id)
    assert list_data[0]["keyframe_url"] is not None


# ---------------------------------------------------------------------------
# 6. Correctives: Async Lifecycle, Cost Auth, GENERATE_SHOT_KEYFRAME & Bounded Batch
# ---------------------------------------------------------------------------
def test_async_image_provider_lifecycle_and_polling(client, db_session):
    """
    ASYNC IMAGE PROVIDER LIFECYCLE:
    - QUEUED/PROCESSING must NOT create a fake completed Asset.
    - Persist IMAGE GenerationJob with truthful status.
    - Poll through durable provider job lifecycle.
    - Create/link keyframe Asset only after verified COMPLETED result.
    """
    from app.services.job_dispatch import JobDispatchService

    p = Project(title="Async Image Test Project", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    shot = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="A futuristic flying car")
    db_session.add(shot)
    db_session.commit()

    # 1. Dispatch generation with simulated async
    asset, job = KeyframeGenerationService.generate_shot_keyframe(
        db=db_session,
        project_id=p.id,
        shot_id=shot.id,
        provider_specific_params={"simulate_async": True},
    )

    # Asset must NOT be fabricated
    assert asset is None
    assert job is not None
    assert job.status == "QUEUED"
    assert job.job_type == "IMAGE"
    assert job.output_asset_id is None

    db_session.refresh(shot)
    assert shot.keyframe_asset_id is None

    db_session.refresh(p)
    assert p.status == "IMAGES_IN_PROGRESS"

    # 2. Poll job status via JobDispatchService
    polled_job = asyncio.run(JobDispatchService.poll_job_status(db=db_session, job_id=job.id))
    assert polled_job.status == "COMPLETED"
    assert polled_job.output_asset_id is not None

    db_session.refresh(shot)
    assert shot.keyframe_asset_id == polled_job.output_asset_id

    created_asset = db_session.get(Asset, polled_job.output_asset_id)
    assert created_asset is not None
    assert created_asset.asset_type == "KEYFRAME"
    assert created_asset.file_size_bytes > 0

    # Project stage should advance to IMAGES_GENERATED
    db_session.refresh(p)
    assert p.status == "IMAGES_GENERATED"


def test_auto_mode_keyframe_cost_authorization_gates(client, db_session):
    """
    COST AUTHORIZATION:
    - In AUTO mode, SHOT_PLAN_APPROVED without cost authorization must STOP.
    - AUTO must not silently incur image generation cost.
    - Explicit cost authorization allows cascade to START_KEYFRAME_GENERATION.
    - Hard budget checks remain mandatory.
    """
    p = Project(
        title="Auto Keyframe Cost Test",
        video_mode="SHORT",
        status="SHOT_PLAN_GENERATED",
        automation_mode="AUTO",
    )
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    shot = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="A prompt")
    db_session.add(shot)
    db_session.commit()
    p_id = str(p.id)

    # 1. Approve SHOT_PLAN_GENERATED WITHOUT cost authorization
    resp = client.post(
        f"/api/v1/projects/{p_id}/orchestration/approve",
        json={"stage": "SHOT_PLAN_GENERATED", "cost_authorized": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["to_stage"] == "SHOT_PLAN_APPROVED"
    assert "cost authorization" in data["message"].lower()

    # Shot must not have a keyframe generated silently
    db_session.refresh(shot)
    assert shot.keyframe_asset_id is None

    # State must recommend START_KEYFRAME_GENERATION
    st = data["orchestration_state"]
    assert st["recommended_action"]["action"] == "START_KEYFRAME_GENERATION"
    assert st["recommended_action"]["is_chargeable"] is True

    # 2. Directly executing START_KEYFRAME_GENERATION as AUTO without cost authorization must fail 402
    with pytest.raises(Exception) as exc_info:
        ProductionOrchestrator.execute_action(
            db=db_session,
            project_id=p.id,
            action="START_KEYFRAME_GENERATION",
            actor="AUTO",
            parameters={"cost_authorized": False},
        )
    assert "402" in str(exc_info.value) or "authorization" in str(exc_info.value).lower()

    # 3. Hard budget exceeded must block even with cost_authorized=True
    p.budget_limit = 0.01
    db_session.commit()
    ledger = UsageLedger(
        project_id=p.id,
        provider="mock_image",
        operation="IMAGE_GENERATION",
        actual_cost=1.0,
        cost_status="COMMITTED",
    )
    db_session.add(ledger)
    db_session.commit()

    with pytest.raises(Exception) as exc_info2:
        ProductionOrchestrator.execute_action(
            db=db_session,
            project_id=p.id,
            action="START_KEYFRAME_GENERATION",
            actor="AUTO",
            parameters={"cost_authorized": True},
        )
    assert "hard budget limit" in str(exc_info2.value).lower() or "409" in str(exc_info2.value)

    # 4. Clear hard budget and execute with cost_authorized=True -> succeeds
    p.budget_limit = 100.0
    db_session.commit()

    exec_res = ProductionOrchestrator.execute_action(
        db=db_session,
        project_id=p.id,
        action="START_KEYFRAME_GENERATION",
        actor="AUTO",
        parameters={"cost_authorized": True},
    )
    assert exec_res.success is True
    assert exec_res.to_stage == "IMAGES_GENERATED"
    db_session.refresh(shot)
    assert shot.keyframe_asset_id is not None


def test_canonical_generate_shot_keyframe_orchestrator_action_and_safety(client, db_session):
    """
    GENERATE_SHOT_KEYFRAME:
    - Canonical action executes successfully with project_id and shot_id.
    - Unsupported force arg removed; locks cannot be bypassed.
    - Hard budget limits cannot be bypassed.
    """
    p = Project(title="Single Shot Action Test", video_mode="SHORT", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    shot = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="Hero looking at horizon")
    db_session.add(shot)
    db_session.commit()
    p_id = str(p.id)

    # 1. Missing shot_id parameter -> 400
    res_missing = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_SHOT_KEYFRAME", "parameters": {}},
    )
    assert res_missing.status_code == 400
    assert "shot_id" in res_missing.json()["detail"]

    # 2. Canonical call with shot_id succeeds
    res_success = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_SHOT_KEYFRAME", "parameters": {"shot_id": str(shot.id)}},
    )
    assert res_success.status_code == 200
    db_session.refresh(shot)
    assert shot.keyframe_asset_id is not None

    # 3. Locked shot cannot be bypassed
    shot.is_locked = True
    db_session.commit()

    res_locked = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_SHOT_KEYFRAME", "parameters": {"shot_id": str(shot.id), "force": True}},
    )
    assert res_locked.status_code == 423
    assert "locked" in res_locked.json()["detail"].lower()

    # 4. Hard budget limit cannot be bypassed
    shot.is_locked = False
    p.budget_limit = 0.05
    ledger = UsageLedger(project_id=p.id, provider="mock_image", operation="IMAGE_GENERATION", actual_cost=10.0, cost_status="COMMITTED")
    db_session.add(ledger)
    db_session.commit()

    res_budget = client.post(
        f"/api/v1/projects/{p_id}/orchestration/execute",
        json={"action": "GENERATE_SHOT_KEYFRAME", "parameters": {"shot_id": str(shot.id)}},
    )
    assert res_budget.status_code in (402, 409)
    assert "budget" in res_budget.json()["detail"].lower()


def test_bounded_no_n_plus_one_batch_keyframe_generation(db_session):
    """
    BOUNDED / NO-N+1 BATCH:
    - Bounded keyset/chunk processing.
    - Set-based eligibility without per-shot GenerationJob queries.
    - Deduplicates active jobs, skips completed shots, handles locks and reconciliation.
    """
    p = Project(title="Bounded Batch Test", video_mode="STORY", status="SHOT_PLAN_APPROVED")
    db_session.add(p)
    db_session.commit()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.commit()

    # Shot 1: Normal eligible
    s1 = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="Shot 1")
    # Shot 2: Locked
    s2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED", visual_prompt="Shot 2", is_locked=True)
    # Shot 3: Has active job
    s3 = Shot(scene_id=sc.id, shot_number=3, shot_type="AI_GENERATED", visual_prompt="Shot 3")
    # Shot 4: Already completed keyframe
    asset_mock = Asset(
        id=uuid.uuid4(),
        project_id=p.id,
        name="Existing Keyframe",
        original_filename="kf.png",
        asset_type="KEYFRAME",
        content_type="image/png",
        file_size_bytes=100,
        checksum_sha256="abc",
        storage_bucket="mock",
        storage_key="k.png",
    )
    db_session.add(asset_mock)
    db_session.flush()
    s4 = Shot(scene_id=sc.id, shot_number=4, shot_type="AI_GENERATED", visual_prompt="Shot 4", keyframe_asset_id=asset_mock.id)

    db_session.add_all([s1, s2, s3, s4])
    db_session.commit()

    # Add active job for s3
    active_job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=s3.id,
        job_type="IMAGE",
        provider_name="mock_image",
        status="PROCESSING",
    )
    db_session.add(active_job)
    db_session.commit()

    # Estimate keyframe batch: 4 total evaluated, only s1 eligible, 3 skipped
    est = KeyframeGenerationService.estimate_keyframe_batch(
        db=db_session,
        project_id=p.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert est["shot_count"] == 1
    assert est["skipped_count"] == 3
    assert est["total_evaluated"] == 4

    # Execute keyframe batch
    batch_run, jobs = KeyframeGenerationService.execute_keyframe_batch(
        db=db_session,
        project_id=p.id,
        operation_type="CONTINUE_INCOMPLETE",
    )

    assert batch_run.requested_count == 4
    assert batch_run.eligible_count == 1
    assert batch_run.completed_count == 1
    assert batch_run.skipped_count == 3
    assert len(jobs) == 1
    assert jobs[0].shot_id == s1.id

    db_session.refresh(s1)
    assert s1.keyframe_asset_id is not None

    # Idempotent repeat: running again skips all (s1 now completed)
    batch_run2, jobs2 = KeyframeGenerationService.execute_keyframe_batch(
        db=db_session,
        project_id=p.id,
        operation_type="CONTINUE_INCOMPLETE",
    )
    assert batch_run2.eligible_count == 0
    assert batch_run2.completed_count == 0
    assert batch_run2.skipped_count == 4
    assert len(jobs2) == 0


def test_async_image_cost_ledger_and_budget_reservation(db_session):
    """
    ASYNC IMAGE COST LEDGER / BUDGET RESERVATION:
    - Queued async image job immediately participates in budget/ledger with ESTIMATED cost.
    - Second submission is blocked when the in-flight reservation would exhaust the budget.
    - Completion reconciles actual cost without duplicate ledger rows or double counting.
    - Repeated polling is idempotent.
    """
    # 1. Setup project with budget limit of $0.05
    p = Project(
        title="Async Budget Reservation Test",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
        budget_limit=0.05,
        budget_currency="USD",
    )
    db_session.add(p)
    db_session.flush()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.flush()

    s1 = Shot(scene_id=sc.id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="A cyberpunk city skyline at night")
    s2 = Shot(scene_id=sc.id, shot_number=2, shot_type="AI_GENERATED", visual_prompt="A flying car zooming across skyscrapers")
    db_session.add_all([s1, s2])
    db_session.commit()

    mock_prov = MockImageProviderAdapter()

    # 2. Dispatch first async keyframe (estimated cost = 0.04)
    asset1, job1 = KeyframeGenerationService.generate_shot_keyframe(
        db=db_session,
        project_id=p.id,
        shot_id=s1.id,
        cost_authorized=True,
        provider_specific_params={"simulate_async": True},
    )
    assert asset1 is None
    assert job1.status == "QUEUED"

    # Queued async image job immediately participates in budget/ledger
    ledger_entries = db_session.query(UsageLedger).filter(UsageLedger.project_id == p.id).all()
    assert len(ledger_entries) == 1
    entry1 = ledger_entries[0]
    assert entry1.job_id == job1.id
    assert entry1.cost_status == CostStatus.ESTIMATED
    assert entry1.estimated_cost == 0.04

    committed_cost = BudgetService.get_project_committed_cost(db_session, p.id)
    assert committed_cost == 0.04

    # 3. Second submission must be blocked because in-flight reservation (0.04) + next (0.04) = 0.08 > limit (0.05)
    with pytest.raises(HTTPException) as exc_info:
        KeyframeGenerationService.generate_shot_keyframe(
            db=db_session,
            project_id=p.id,
            shot_id=s2.id,
            cost_authorized=True,
            provider_specific_params={"simulate_async": True},
        )
    assert exc_info.value.status_code == 402
    assert "budget limit exceeded" in exc_info.value.detail.lower()

    # 4. Completion does not double count cost and does not duplicate ledger rows
    res_completed = asyncio.run(mock_prov.check_job_status(job1.provider_job_id))
    assert res_completed.status == "COMPLETED"

    asset_completed = KeyframeGenerationService.complete_async_keyframe_job(
        db=db_session,
        job_id=job1.id,
        result=res_completed,
    )
    assert asset_completed is not None

    db_session.refresh(job1)
    assert job1.status == "COMPLETED"
    assert job1.output_asset_id == asset_completed.id

    ledger_entries_after = db_session.query(UsageLedger).filter(UsageLedger.project_id == p.id).all()
    assert len(ledger_entries_after) == 1
    assert ledger_entries_after[0].id == entry1.id
    assert ledger_entries_after[0].cost_status == CostStatus.CONFIRMED
    assert ledger_entries_after[0].actual_cost == 0.04

    committed_after = BudgetService.get_project_committed_cost(db_session, p.id)
    assert committed_after == 0.04  # Still 0.04, no double-counting!

    # 5. Repeated polling is idempotent
    second_completion = KeyframeGenerationService.complete_async_keyframe_job(
        db=db_session,
        job_id=job1.id,
        result=res_completed,
    )
    assert second_completion is None  # Already completed
    ledger_entries_idempotent = db_session.query(UsageLedger).filter(UsageLedger.project_id == p.id).all()
    assert len(ledger_entries_idempotent) == 1
    assert BudgetService.get_project_committed_cost(db_session, p.id) == 0.04


def test_batch_keyframe_no_per_shot_generation_job_queries(db_session):
    """
    REMOVE REMAINING PER-SHOT GENERATION_JOB QUERY IN BATCH:
    Demonstrates GenerationJob eligibility queries do not scale linearly with shot count for batch execution.
    """
    p = Project(
        title="Batch Query Count Test",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
    )
    db_session.add(p)
    db_session.flush()

    sc = Scene(project_id=p.id, scene_number=1)
    db_session.add(sc)
    db_session.flush()

    # Create 10 shots in the scene
    shots = [
        Shot(scene_id=sc.id, shot_number=i, shot_type="AI_GENERATED", visual_prompt=f"Shot visual prompt {i}")
        for i in range(1, 11)
    ]
    db_session.add_all(shots)
    db_session.commit()

    from sqlalchemy import event
    engine = db_session.get_bind()

    job_select_queries = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        stmt_clean = statement.lower().strip()
        if "generation_jobs" in stmt_clean and stmt_clean.startswith("select"):
            job_select_queries.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        batch_run, jobs = KeyframeGenerationService.execute_keyframe_batch(
            db=db_session,
            project_id=p.id,
            operation_type="CONTINUE_INCOMPLETE",
            cost_authorized=True,
        )
        assert batch_run.eligible_count == 10
        assert batch_run.completed_count == 10

        # With 10 eligible shots in a single chunk (chunk size 50),
        # only the 1 chunk prefilter query touches generation_jobs.
        # There are NO per-shot generation_jobs queries!
        assert len(job_select_queries) == 1
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def test_concurrent_shot_keyframe_claims_invoke_provider_at_most_once(tmp_path):
    """
    CONCURRENCY / ATOMIC PRE-PROVIDER CLAIM:
    - Two concurrent submissions for the same shot atomically compete for SUBMITTING claim.
    - Provider is invoked AT MOST ONCE (the winner).
    - The losing caller receives 409 Conflict.
    - Exactly one GenerationJob exists for the shot.
    - Exactly one UsageLedger entry exists for the shot.
    """
    import threading
    from unittest.mock import patch
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base_class import Base

    db_file = tmp_path / "concurrent_keyframe_claim.db"
    file_engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 30})
    Base.metadata.create_all(file_engine)
    FileSessionLocal = sessionmaker(bind=file_engine, expire_on_commit=False)

    project_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    with FileSessionLocal() as init_db:
        p = Project(id=project_id, title="Conc Keyframe Test", status="SHOT_PLAN_APPROVED", video_mode="STORY")
        sc = Scene(id=scene_id, project_id=project_id, scene_number=1)
        sh = Shot(id=shot_id, scene_id=scene_id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="A heroic cyberpunk cat")
        init_db.add_all([p, sc, sh])
        init_db.commit()

    provider_calls = []
    original_generate_image = MockImageProviderAdapter.generate_image

    async def tracked_generate_image(self, params):
        provider_calls.append(params)
        await asyncio.sleep(0.05)
        return await original_generate_image(self, params)

    barrier = threading.Barrier(2)
    results = []
    exceptions = []

    def worker():
        with FileSessionLocal() as session:
            try:
                barrier.wait()
                asset, job = KeyframeGenerationService.generate_shot_keyframe(
                    db=session,
                    project_id=project_id,
                    shot_id=shot_id,
                    cost_authorized=True,
                )
                results.append((asset, job))
            except HTTPException as e:
                exceptions.append(e)
            except Exception as e:
                exceptions.append(e)

    with patch.object(MockImageProviderAdapter, "generate_image", tracked_generate_image):
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    # 1. Exactly one worker succeeded and one failed with 409 Conflict
    assert len(results) == 1
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], HTTPException)
    assert exceptions[0].status_code == 409
    assert "already has an active generation job" in exceptions[0].detail.lower()

    # 2. Provider was invoked AT MOST ONCE (exactly once)
    assert len(provider_calls) == 1

    # 3. Only one GenerationJob exists in DB
    with FileSessionLocal() as verify_db:
        jobs = verify_db.query(GenerationJob).filter(GenerationJob.shot_id == shot_id).all()
        assert len(jobs) == 1
        assert jobs[0].status == "COMPLETED"

        # 4. Only one UsageLedger entry exists in DB
        ledger_entries = verify_db.query(UsageLedger).filter(UsageLedger.shot_id == shot_id).all()
        assert len(ledger_entries) == 1
        assert ledger_entries[0].cost_status == CostStatus.CONFIRMED

    file_engine.dispose()


def test_concurrent_submissions_near_hard_budget_cannot_overspend(tmp_path):
    """
    BUDGET RACE / OVERSPEND PREVENTION:
    - Pre-provider reservation in UsageLedger prevents concurrent submissions near budget limit from overspending.
    - When budget allows only 1 shot ($0.05 limit, $0.04 per shot), racing two different shots:
      - The first claim reserves $0.04 immediately.
      - The second claim detects in-flight reservation and is rejected (402 Budget limit exceeded).
      - Provider is invoked at most once.
      - Total committed cost never exceeds the hard budget limit.
    """
    import threading
    from unittest.mock import patch
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base_class import Base

    db_file = tmp_path / "concurrent_budget_race.db"
    file_engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 30})
    Base.metadata.create_all(file_engine)
    FileSessionLocal = sessionmaker(bind=file_engine, expire_on_commit=False)

    project_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    shot1_id = uuid.uuid4()
    shot2_id = uuid.uuid4()

    with FileSessionLocal() as init_db:
        p = Project(
            id=project_id,
            title="Budget Race Test",
            status="SHOT_PLAN_APPROVED",
            video_mode="STORY",
            budget_limit=0.05,
            budget_currency="USD",
        )
        sc = Scene(id=scene_id, project_id=project_id, scene_number=1)
        s1 = Shot(id=shot1_id, scene_id=scene_id, shot_number=1, shot_type="AI_GENERATED", visual_prompt="Shot 1")
        s2 = Shot(id=shot2_id, scene_id=scene_id, shot_number=2, shot_type="AI_GENERATED", visual_prompt="Shot 2")
        init_db.add_all([p, sc, s1, s2])
        init_db.commit()

    provider_calls = []
    original_generate_image = MockImageProviderAdapter.generate_image

    async def tracked_generate_image(self, params):
        provider_calls.append(params)
        return await original_generate_image(self, params)

    barrier = threading.Barrier(2)
    results = []
    exceptions = []

    def worker(target_shot_id):
        with FileSessionLocal() as session:
            try:
                barrier.wait()
                asset, job = KeyframeGenerationService.generate_shot_keyframe(
                    db=session,
                    project_id=project_id,
                    shot_id=target_shot_id,
                    cost_authorized=True,
                )
                results.append((target_shot_id, asset, job))
            except HTTPException as e:
                exceptions.append((target_shot_id, e))
            except Exception as e:
                exceptions.append((target_shot_id, e))

    with patch.object(MockImageProviderAdapter, "generate_image", tracked_generate_image):
        t1 = threading.Thread(target=worker, args=(shot1_id,))
        t2 = threading.Thread(target=worker, args=(shot2_id,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    # Exactly one succeeded and one was blocked by budget limit
    assert len(results) == 1
    assert len(exceptions) == 1
    assert isinstance(exceptions[0][1], HTTPException)
    assert exceptions[0][1].status_code == 402
    assert "budget limit exceeded" in exceptions[0][1].detail.lower()

    # Provider was invoked exactly once
    assert len(provider_calls) == 1

    # Budget in DB was never overspent
    with FileSessionLocal() as verify_db:
        committed_cost = BudgetService.get_project_committed_cost(verify_db, project_id)
        assert committed_cost == 0.04
        assert committed_cost <= 0.05

        ledger_entries = verify_db.query(UsageLedger).filter(UsageLedger.project_id == project_id).all()
        assert len(ledger_entries) == 1

    file_engine.dispose()
