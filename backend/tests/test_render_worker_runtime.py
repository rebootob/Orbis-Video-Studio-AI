from pathlib import Path

import pytest

from app.services.render.ffmpeg_executor import FFmpegRenderExecutor
from app.services.render_worker import _resolve_poll_seconds, run_forever, run_once


class FakeSession:
    def __init__(self):
        self.committed = 0
        self.rolled_back = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1


class FakeStopEvent:
    def __init__(self):
        self.stopped = False
        self.waits = []

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, seconds):
        self.waits.append(seconds)
        self.stopped = True
        return True


class IdleWorker:
    worker_id = "runtime-test-worker"

    def __init__(self):
        self.validated = 0
        self.processed = 0

    def validate_runtime(self):
        self.validated += 1

    def process_one_job(self, _db):
        self.processed += 1
        return False


def test_ffmpeg_runtime_validation_fails_when_binary_missing(monkeypatch):
    monkeypatch.setattr("app.services.render.ffmpeg_executor.shutil.which", lambda _path: None)

    with pytest.raises(RuntimeError, match="not found"):
        FFmpegRenderExecutor().validate_runtime()


def test_ffmpeg_runtime_validation_executes_version_probe(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = "ffmpeg version test"
        stderr = ""

    monkeypatch.setattr(
        "app.services.render.ffmpeg_executor.shutil.which",
        lambda _path: "/usr/bin/ffmpeg",
    )

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return Result()

    monkeypatch.setattr("app.services.render.ffmpeg_executor.subprocess.run", fake_run)

    resolved = FFmpegRenderExecutor().validate_runtime()

    assert resolved == "/usr/bin/ffmpeg"
    assert calls[0][0] == ["/usr/bin/ffmpeg", "-version"]
    assert calls[0][1]["timeout"] == 10


def test_render_worker_idle_loop_validates_commits_backs_off_and_stops():
    session = FakeSession()
    worker = IdleWorker()
    stop_event = FakeStopEvent()

    run_forever(
        worker=worker,
        session_factory=lambda: session,
        stop_event=stop_event,
        poll_seconds=0.25,
    )

    assert worker.validated == 1
    assert worker.processed == 1
    assert session.committed == 1
    assert session.rolled_back == 0
    assert stop_event.waits == [0.25]


def test_render_worker_run_once_rolls_back_on_unhandled_error():
    session = FakeSession()

    class ErrorWorker:
        def process_one_job(self, _db):
            raise RuntimeError("database/runtime failure")

    with pytest.raises(RuntimeError, match="database/runtime failure"):
        run_once(ErrorWorker(), session_factory=lambda: session)

    assert session.committed == 0
    assert session.rolled_back == 1


def test_render_worker_poll_interval_is_bounded(monkeypatch):
    monkeypatch.setenv("ORBIS_RENDER_WORKER_POLL_SECONDS", "0.5")
    assert _resolve_poll_seconds() == 0.5

    monkeypatch.setenv("ORBIS_RENDER_WORKER_POLL_SECONDS", "0.01")
    with pytest.raises(RuntimeError, match="between"):
        _resolve_poll_seconds()

    monkeypatch.setenv("ORBIS_RENDER_WORKER_POLL_SECONDS", "not-a-number")
    with pytest.raises(RuntimeError, match="must be a number"):
        _resolve_poll_seconds()


def test_container_and_compose_wire_operational_render_worker():
    repo_root = Path(__file__).resolve().parents[2]
    dockerfile = (repo_root / "backend" / "Dockerfile").read_text(encoding="utf-8")
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "ffmpeg" in dockerfile
    assert "render-worker:" in compose
    assert 'command: ["python", "-m", "app.services.render_worker"]' in compose
    assert "condition: service_healthy" in compose
    assert "ORBIS_RENDER_WORKER_POLL_SECONDS" in compose
    assert "${POSTGRES_PASSWORD}" in compose
    assert "${OBJECT_STORAGE_SECRET_KEY}" in compose
