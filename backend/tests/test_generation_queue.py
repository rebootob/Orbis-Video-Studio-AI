"""WP007 contract tests: mocked HTTP only; real independent DB sessions for races."""
import asyncio
import os
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.generation_job import GenerationJob as Job
from app.providers.base import ProviderJobResult, VideoGenerationParams, ReferenceImageInput
from app.providers.vidu import ViduProviderAdapter
from app.providers.factory import ProviderFactory
from app.services.job_dispatch import JobDispatchService as Queue, LEASE_SECONDS, POLL_SECONDS
from app.services.generation_worker import run_once

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def deny_live_http(monkeypatch):
    async def denied(*args, **kwargs):
        raise AssertionError("Unmocked HTTP is forbidden in WP007 tests")
    monkeypatch.setattr(httpx.AsyncClient, "send", denied)


def make_shot(db):
    project = Project(id=uuid.uuid4(), title="Queue test")
    story = Story(id=uuid.uuid4(), project_id=project.id, logline="Test")
    scene = Scene(id=uuid.uuid4(), story_id=story.id, scene_number=1, heading="EXT. PARK")
    shot = Shot(id=uuid.uuid4(), scene_id=scene.id, shot_number=1, shot_type="AI_GENERATED",
                video_prompt="A tree in the wind", duration_seconds=5)
    db.add_all([project, story, scene, shot])
    db.commit()
    return shot


@pytest.fixture
def sample_shot(db_session):
    return make_shot(db_session)


@pytest.fixture
def durable_db(tmp_path):
    postgres_url = os.environ.get("WP007_TEST_DATABASE_URL")
    schema = "wp007_" + uuid.uuid4().hex
    if postgres_url:
        admin = create_engine(postgres_url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(postgres_url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(f"sqlite:///{tmp_path / 'queue.db'}", connect_args={"timeout": 30})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        shot_id = make_shot(db).id
    yield factory, shot_id
    engine.dispose()
    if postgres_url:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()



@pytest.fixture
def provider():
    adapter = AsyncMock()
    adapter.validate_config = lambda config: True
    adapter.submit_generation_job.return_value = ProviderJobResult(provider_job_id="task-1", status="QUEUED")
    adapter.check_job_status.return_value = ProviderJobResult(provider_job_id="task-1", status="PROCESSING")
    adapter.cancel_job.return_value = True
    with patch.object(ProviderFactory, "get_provider", return_value=adapter):
        yield adapter


def create(db, shot, **kwargs):
    return Queue.create_and_dispatch_job(db, shot.id, **kwargs)


def claim(db, job, now=NOW):
    return Queue.claim_next_job(db, "test-worker", now=now, job_id=job.id)


def transport_response(data=None, status=200):
    return httpx.Response(status, json=data or {}, request=httpx.Request("POST", "https://mock.invalid"))


@pytest.mark.anyio
@pytest.mark.parametrize("references", [False, True])
async def test_official_submit_mapping(references):
    adapter = ViduProviderAdapter(api_key="fake-provider-key", model="viduq2")
    params = VideoGenerationParams(shot_id="shot", prompt="Tree", duration_seconds=5, seed=42,
        reference_images=[ReferenceImageInput(type="character", url="https://example.com/ref.png")] if references else None)
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as request:
        request.return_value = transport_response({"task_id": "task-42", "state": "created"})
        result = await adapter.submit_generation_job(params)
        assert result.status == "QUEUED"
        assert result.provider_job_id == "task-42"
        args, kwargs = request.call_args
        assert args == ("POST", "https://api.vidu.com/ent/v2/" + ("reference2video" if references else "text2video"))
        assert kwargs["headers"]["Authorization"] == "Token fake-provider-key"
        assert kwargs["json"]["model"] == "viduq2"
        assert kwargs["json"]["duration"] == 5
        assert kwargs["json"]["seed"] == 42
        assert kwargs["json"]["aspect_ratio"] == "16:9"
        assert ("images" in kwargs["json"]) == references
        assert result.raw_response is None


@pytest.mark.anyio
async def test_status_cancel_and_nested_response_safety(caplog):
    adapter = ViduProviderAdapter(api_key="fake-provider-key")
    data = {"id": "task-1", "state": "success", "error_message": {"secret": "LEAK"},
            "raw": {"authorization": "LEAK"}, "creations": [{"url": "https://example.com/movie.mp4", "token": "LEAK"}]}
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=transport_response(data)) as request:
        result = await adapter.check_job_status("task-1")
        assert request.call_args.args == ("GET", "https://api.vidu.com/ent/v2/tasks/task-1/creations")
        assert result.video_url == "https://example.com/movie.mp4"
        assert "LEAK" not in result.model_dump_json()
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=transport_response()) as post:
        assert await adapter.cancel_job("task-1")
        assert post.call_args.args[0].endswith("/tasks/task-1/cancel")
    with patch.object(httpx.AsyncClient, "post", side_effect=RuntimeError("password=LEAK")):
        assert not await adapter.cancel_job("task-1")
    assert "LEAK" not in caplog.text


@pytest.mark.anyio
@pytest.mark.parametrize("code,transient,ambiguous", [(400,False,False),(401,False,False),(403,False,False),
    (429,True,False),(500,True,True),(502,True,True),(503,True,True),(504,True,True),(501,False,True)])
async def test_http_failure_classification(code, transient, ambiguous):
    adapter = ViduProviderAdapter(api_key="fake-provider-key")
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=transport_response({"error": {"password": "LEAK"}}, code)):
        params = VideoGenerationParams(shot_id="shot", prompt="Tree", duration_seconds=5)
        submit = await adapter.submit_generation_job(params)
        poll = await adapter.check_job_status("task-1")
        assert submit.retryable is transient
        assert submit.submission_uncertain is ambiguous
        assert poll.retryable is transient
        assert not poll.submission_uncertain
        assert "LEAK" not in submit.model_dump_json()


@pytest.mark.anyio
@pytest.mark.parametrize("exc,ambiguous", [(httpx.ConnectTimeout("LEAK"),False), (httpx.ConnectError("LEAK"),False),
    (httpx.ReadTimeout("LEAK"),True), (httpx.WriteError("LEAK"),True)])
async def test_transport_failure_classification(exc, ambiguous):
    adapter = ViduProviderAdapter(api_key="fake-provider-key")
    with patch.object(httpx.AsyncClient, "request", side_effect=exc):
        res = await adapter.submit_generation_job(VideoGenerationParams(shot_id="shot", prompt="Tree"))
        assert res.retryable
        assert res.submission_uncertain is ambiguous
        assert "LEAK" not in res.model_dump_json()


@pytest.mark.anyio
async def test_configuration_validation_and_rejection():
    for kwargs in ({"api_key":""}, {"base_url":"http://insecure.invalid"}, {"timeout_seconds":0}, {"timeout_seconds":121}):
        adapter = ViduProviderAdapter(**({"api_key":"fake-provider-key"} | kwargs))
        assert not adapter.validate_config({})
    adapter = ViduProviderAdapter(api_key="fake-provider-key", model="unsupported")
    res = await adapter.submit_generation_job(VideoGenerationParams(shot_id="shot", prompt="Tree"))
    assert res.status == "FAILED" and not res.retryable
    adapter = ViduProviderAdapter(api_key="fake-provider-key")
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock,
                      return_value=transport_response({"state":"failed", "error_message":{"secret":"LEAK"}})):
        res = await adapter.submit_generation_job(VideoGenerationParams(shot_id="shot", prompt="Tree"))
        assert res.error_code == "PROVIDER_REJECTED" and not res.retryable and not res.submission_uncertain


@pytest.mark.anyio
async def test_claim_required_and_wrong_expired_tokens(db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    with pytest.raises(HTTPException):
        await Queue.process_job(db_session, job.id, now=NOW)
    claimed = claim(db_session, job)
    token = claimed.claim_token
    with pytest.raises(HTTPException):
        await Queue.process_job(db_session, job.id, claim_token="wrong", now=NOW)
    with pytest.raises(HTTPException):
        await Queue.process_job(db_session, job.id, claim_token=token, now=NOW+timedelta(seconds=LEASE_SECONDS))
    assert provider.submit_generation_job.await_count == 0
    assert Queue.recover_pending_jobs(db_session, now=NOW) == 0
    assert Queue.recover_pending_jobs(db_session, now=NOW+timedelta(seconds=LEASE_SECONDS)) == 1
    fresh = claim(db_session, job, NOW+timedelta(seconds=LEASE_SECONDS))
    assert fresh.claim_token != token


def test_real_concurrent_claim_and_dispatch(durable_db, provider):
    factory, shot_id = durable_db
    with factory() as db:
        job_id = Queue.create_and_dispatch_job(db, shot_id).id
    barrier = Barrier(2)
    def compete():
        with factory() as db:
            barrier.wait()
            job = Queue.claim_next_job(db, now=NOW)
            return (job.id, job.claim_token) if job else None
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: compete(), range(2)))
    winners = [r for r in results if r]
    assert len(winners) == 1
    token = winners[0][1]
    barrier = Barrier(2)
    def dispatch():
        with factory() as db:
            barrier.wait()
            try:
                return asyncio.run(Queue.process_job(db, job_id, claim_token=token, now=NOW)).status
            except HTTPException as exc:
                assert exc.status_code == 409
                return "CONFLICT"
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: dispatch(), range(2)))
    assert provider.submit_generation_job.await_count == 1


def test_real_concurrent_idempotency(durable_db):
    factory, shot_id = durable_db
    barrier = Barrier(2)
    def create_race():
        with factory() as db:
            barrier.wait()
            return Queue.create_and_dispatch_job(db, shot_id, idempotency_key="same-request").id
    with ThreadPoolExecutor(2) as pool:
        ids = list(pool.map(lambda _: create_race(), range(2)))
    assert ids[0] == ids[1]
    with factory() as db:
        assert db.query(Job).count() == 1


@pytest.mark.anyio
async def test_crash_after_provider_acceptance_before_persistence(durable_db, provider):
    factory, shot_id = durable_db
    class ProcessDeath(BaseException):
        pass
    async def accepted_then_crash(params):
        with factory() as other:
            stored = other.query(Job).one()
            assert stored.status == "SUBMITTING" and stored.submission_attempt_id
        raise ProcessDeath()
    provider.submit_generation_job.side_effect = accepted_then_crash
    with factory() as db:
        job = Queue.create_and_dispatch_job(db, shot_id)
        job_id = job.id
        token = claim(db, job).claim_token
        with pytest.raises(ProcessDeath):
            await Queue.process_job(db, job_id, claim_token=token, now=NOW)
    with factory() as restarted:
        assert Queue.recover_pending_jobs(restarted, now=NOW+timedelta(seconds=LEASE_SECONDS)) == 1
        stored = restarted.get(Job, job_id)
        assert stored.status == "RECONCILIATION_REQUIRED"
        assert Queue.claim_next_job(restarted, now=NOW+timedelta(days=1)) is None
        await Queue.process_job(restarted, job_id, claim_token=token, now=NOW+timedelta(days=1))
    assert provider.submit_generation_job.await_count == 1


@pytest.mark.anyio
async def test_ambiguous_result_quarantined(db_session, sample_shot, provider):
    provider.submit_generation_job.return_value = ProviderJobResult(provider_job_id="", status="FAILED", retryable=True, submission_uncertain=True)
    job = create(db_session, sample_shot)
    token = claim(db_session, job).claim_token
    result = await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    assert result.status == "RECONCILIATION_REQUIRED"
    assert Queue.claim_next_job(db_session, now=NOW+timedelta(days=1)) is None


@pytest.mark.anyio
async def test_bounded_retry_and_durable_eligibility(db_session, sample_shot, provider):
    provider.submit_generation_job.return_value = ProviderJobResult(provider_job_id="", status="FAILED", retryable=True, status_code=429)
    job = create(db_session, sample_shot, max_retries=3)
    for attempt, seconds in enumerate((0,5,15), 1):
        now = NOW+timedelta(seconds=seconds)
        token = claim(db_session, job, now).claim_token
        result = await Queue.process_job(db_session, job.id, claim_token=token, now=now)
        assert result.retry_count == attempt
        if attempt < 3:
            assert result.status == "PENDING"
            assert claim(db_session, job, now+timedelta(seconds=4 if attempt == 1 else 9)) is None
        else:
            assert result.status == "FAILED"
    await Queue.process_job(db_session, job.id, claim_token=token, now=NOW+timedelta(days=1))
    assert provider.submit_generation_job.await_count == 3


@pytest.mark.anyio
@pytest.mark.parametrize("code", [400,401,403,None])
async def test_permanent_failures_never_resubmit(db_session, sample_shot, provider, code):
    provider.submit_generation_job.return_value = ProviderJobResult(provider_job_id="", status="FAILED", status_code=code,
        error_message="network timeout 429 secret=LEAK", raw_response={"retryable":True})
    job = create(db_session, sample_shot)
    token = claim(db_session, job).claim_token
    result = await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    assert result.status == "FAILED" and result.retry_count == 0
    await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    assert provider.submit_generation_job.await_count == 1
    assert "LEAK" not in str(result.result) + str(result.error_message)


@pytest.mark.anyio
async def test_poll_schedule_output_and_terminal_noop(db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    token = claim(db_session, job).claim_token
    await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=9))
    assert provider.check_job_status.await_count == 0
    await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=10))
    await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=10))
    assert provider.check_job_status.await_count == 1
    provider.check_job_status.return_value = ProviderJobResult(provider_job_id="task-1", status="COMPLETED",
        video_url="https://example.com/movie.mp4", raw_response={"secret":"LEAK"})
    result = await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=20))
    assert result.status == "COMPLETED" and result.output_asset_id is None
    assert result.result["video_url"] == "https://example.com/movie.mp4"
    assert db_session.query(Asset).count() == 0
    assert "LEAK" not in str(result.result)
    await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(days=1))
    assert provider.check_job_status.await_count == 2


@pytest.mark.anyio
@pytest.mark.parametrize("code", [429,500,502,503,504])
async def test_poll_transient_backoff_and_bound(db_session, sample_shot, provider, code):
    job = create(db_session, sample_shot, max_retries=2)
    token = claim(db_session, job).claim_token
    await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    provider.check_job_status.return_value = ProviderJobResult(provider_job_id="task-1", status="FAILED", retryable=True, status_code=code)
    result = await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=10))
    assert result.status == "PROCESSING"
    await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=19))
    assert provider.check_job_status.await_count == 1
    result = await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=20))
    assert result.status == "FAILED"
    assert provider.submit_generation_job.await_count == 1


@pytest.mark.anyio
async def test_cancel_api_and_terminal_noop(client, db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    response = client.post(f"/api/v1/jobs/{job.id}/cancel")
    assert response.json()["status"] == "CANCELLED"
    assert provider.cancel_job.await_count == 0
    active = create(db_session, sample_shot)
    token = claim(db_session, active).claim_token
    await Queue.process_job(db_session, active.id, claim_token=token, now=NOW)
    response = client.post(f"/api/v1/jobs/{active.id}/cancel")
    assert response.json()["status"] == "CANCELLED"
    client.post(f"/api/v1/jobs/{active.id}/cancel")
    assert provider.cancel_job.await_count == 1
    assert "claim_token" not in response.json()


@pytest.mark.anyio
async def test_cancel_failures_and_submitting_noop(db_session, sample_shot, provider, caplog):
    job = create(db_session, sample_shot)
    job.status = "SUBMITTING"
    db_session.commit()
    await Queue.cancel_job(db_session, job.id, now=NOW)
    assert provider.cancel_job.await_count == 0
    job.status = "PROCESSING"
    job.provider_job_id = "task-1"
    db_session.commit()
    provider.cancel_job.side_effect = RuntimeError('Authorization: token=LEAK')
    result = await Queue.cancel_job(db_session, job.id, now=NOW)
    assert result.status == "PROCESSING"
    assert "LEAK" not in str(result.error_message) + caplog.text
    await Queue.cancel_job(db_session, job.id, now=NOW)
    assert provider.cancel_job.await_count == 1


@pytest.mark.parametrize("key", ["api_key", "AUTHORIZATION", "access_token", "secret", "password", "credential"])
def test_nested_secret_params_rejected_without_echo(client, db_session, sample_shot, key):
    response = client.post("/api/v1/jobs", json={"shot_id":str(sample_shot.id), "custom_params":{"nested":[{key:"NEVER_PERSIST"}]}})
    assert response.status_code == 400
    assert "NEVER_PERSIST" not in response.text
    assert db_session.query(Job).count() == 0


def test_worker_restarts_and_recovers_due_jobs(durable_db, provider):
    factory, shot_id = durable_db
    with factory() as db:
        job_id = Queue.create_and_dispatch_job(db, shot_id).id
    asyncio.run(run_once(factory))
    asyncio.run(run_once(factory))
    with factory() as db:
        assert db.get(Job, job_id).provider_job_id == "task-1"
    assert provider.submit_generation_job.await_count == 1


def test_concurrent_polls_make_one_provider_call(durable_db, provider):
    factory, shot_id = durable_db
    with factory() as db:
        job = Queue.create_and_dispatch_job(db, shot_id)
        job_id = job.id
        token = claim(db, job).claim_token
        asyncio.run(Queue.process_job(db, job_id, claim_token=token, now=NOW))
    barrier = Barrier(4)
    def poll():
        with factory() as db:
            barrier.wait()
            return asyncio.run(Queue.poll_job_status(db, job_id, now=NOW+timedelta(seconds=10))).status
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda _: poll(), range(4)))
    assert provider.check_job_status.await_count == 1
    with factory() as db:
        assert db.get(Job, job_id).poll_count == 1


def test_concurrent_cancels_make_one_provider_call(durable_db, provider):
    factory, shot_id = durable_db
    with factory() as db:
        job = Queue.create_and_dispatch_job(db, shot_id)
        job_id = job.id
        token = claim(db, job).claim_token
        asyncio.run(Queue.process_job(db, job_id, claim_token=token, now=NOW))
    barrier = Barrier(4)
    def cancel():
        with factory() as db:
            barrier.wait()
            return asyncio.run(Queue.cancel_job(db, job_id, now=NOW)).status
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda _: cancel(), range(4)))
    assert provider.cancel_job.await_count == 1
    with factory() as db:
        assert db.get(Job, job_id).status == "CANCELLED"


@pytest.mark.anyio
async def test_live_submission_lease_and_stale_completion_fence(durable_db, provider):
    factory, shot_id = durable_db
    async def recover_during_submission(params):
        with factory() as other:
            assert Queue.recover_pending_jobs(other, now=NOW+timedelta(seconds=1)) == 0
            assert Queue.recover_pending_jobs(other, now=NOW+timedelta(seconds=LEASE_SECONDS)) == 1
        return ProviderJobResult(provider_job_id="accepted-task", status="QUEUED")
    provider.submit_generation_job.side_effect = recover_during_submission
    with factory() as db:
        job = Queue.create_and_dispatch_job(db, shot_id)
        token = claim(db, job).claim_token
        result = await Queue.process_job(db, job.id, claim_token=token, now=NOW)
        assert result.status == "RECONCILIATION_REQUIRED"
        assert result.provider_job_id is None
    assert provider.submit_generation_job.await_count == 1


@pytest.mark.anyio
async def test_persisted_poll_bound_requires_reconciliation(db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    job.max_polls = 1
    db_session.commit()
    token = claim(db_session, job).claim_token
    await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=10))
    result = await Queue.poll_job_status(db_session, job.id, now=NOW+timedelta(seconds=20))
    assert result.status == "RECONCILIATION_REQUIRED"
    assert provider.check_job_status.await_count == 1


@pytest.mark.anyio
async def test_schedule_starts_after_response(db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    token = claim(db_session, job).claim_token
    provider.submit_generation_job.return_value = ProviderJobResult(provider_job_id="", status="FAILED", retryable=True)
    with patch("app.services.job_dispatch.utc_now", side_effect=[NOW, NOW+timedelta(seconds=30)]):
        result = await Queue.process_job(db_session, job.id, claim_token=token)
    assert result.next_retry_at.replace(tzinfo=timezone.utc) == NOW+timedelta(seconds=35)


def test_api_claim_token_dispatch_and_no_secret_output(client, db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    claimed = client.post("/api/v1/queue/claim").json()
    assert claimed["id"] == str(job.id) and claimed["claim_token"]
    provider.submit_generation_job.return_value = ProviderJobResult(provider_job_id="", status="FAILED",
        error_message='unlabelled LEAK', raw_response={"details":[{"credential":"LEAK"}]})
    response = client.post(f"/api/v1/jobs/{job.id}/dispatch", json={"claim_token":claimed["claim_token"]})
    assert response.status_code == 200 and response.json()["status"] == "FAILED"
    assert "LEAK" not in response.text
    assert claimed["claim_token"] not in response.text
    assert "LEAK" not in client.get(f"/api/v1/jobs/{job.id}").text


def test_configured_secret_value_rejected(client, sample_shot, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "VIDU_API_KEY", "unlabelled-sensitive-value")
    response = client.post("/api/v1/jobs", json={"shot_id":str(sample_shot.id), "custom_params":{"resolution":"unlabelled-sensitive-value"}})
    assert response.status_code == 400
    assert "unlabelled-sensitive-value" not in response.text


@pytest.mark.anyio
async def test_long_safe_prompt_is_preserved(db_session, sample_shot, provider):
    sample_shot.video_prompt = "A tree in the wind. " * 100
    db_session.commit()
    job = create(db_session, sample_shot)
    assert job.payload["prompt"] == sample_shot.video_prompt


@pytest.mark.anyio
async def test_service_discards_unlabelled_cancel_exception(client, db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    token = claim(db_session, job).claim_token
    await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    provider.cancel_job.side_effect = RuntimeError("unlabelled LEAK")
    response = client.post(f"/api/v1/jobs/{job.id}/cancel")
    assert "LEAK" not in response.text


@pytest.mark.anyio
async def test_unsupported_and_unconfigured_providers_do_not_submit(db_session, sample_shot, provider):
    job = create(db_session, sample_shot)
    token = claim(db_session, job).claim_token
    provider.validate_config = lambda config: False
    result = await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    assert result.status == "FAILED" and provider.submit_generation_job.await_count == 0
    other = create(db_session, sample_shot, provider_name="unsupported")
    token = claim(db_session, other).claim_token
    with patch.object(ProviderFactory, "get_provider", side_effect=ValueError("LEAK")):
        result = await Queue.process_job(db_session, other.id, claim_token=token, now=NOW)
        assert result.status == "FAILED" and "LEAK" not in result.error_message


@pytest.mark.anyio
async def test_transient_result_with_provider_identity_never_resubmits(db_session, sample_shot, provider):
    provider.submit_generation_job.return_value = ProviderJobResult(provider_job_id="accepted-task", status="FAILED", retryable=True)
    job = create(db_session, sample_shot)
    token = claim(db_session, job).claim_token
    result = await Queue.process_job(db_session, job.id, claim_token=token, now=NOW)
    assert result.status == "PROCESSING" and result.provider_job_id == "accepted-task"
    assert Queue.claim_next_job(db_session, now=NOW+timedelta(days=1)) is None
    await Queue.process_job(db_session, job.id, claim_token=token, now=NOW+timedelta(days=1))
    assert provider.submit_generation_job.await_count == 1
