import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.audio_clip import AudioClip, AudioGenerationMode, AudioScope, AudioSourceType, AudioType, DuckingRole
from app.models.project import Project
from app.models.usage_ledger import UsageLedger
from app.providers.audio.base import AudioGenerationParams, AudioJobResult, AudioProviderCapabilities, IAudioProviderAdapter
from app.providers.audio.elevenlabs_adapter import ElevenLabsAudioProviderAdapter
from app.providers.audio.factory import AudioProviderFactory
from app.services.audio_production import AudioProductionService


class _FakeResponse:
    def __init__(self, status_code=200, content=b"mp3-bytes", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"content-type": "audio/mpeg", "request-id": "req-123"}


class _FakeAsyncClient:
    def __init__(self, response, captured, **_kwargs):
        self._response = response
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers, params=None):
        self._captured.append({"url": url, "json": json, "headers": headers, "params": params})
        return self._response


def _patch_http(monkeypatch, response):
    captured = []

    def factory(**kwargs):
        return _FakeAsyncClient(response, captured, **kwargs)

    monkeypatch.setattr("app.providers.audio.elevenlabs_adapter.httpx.AsyncClient", factory)
    return captured


def _adapter(**kwargs):
    return ElevenLabsAudioProviderAdapter(api_key="test-key", default_voice_id="voice_123", **kwargs)


def test_factory_registers_production_and_mock_audio():
    assert "mock_audio" in AudioProviderFactory.list_providers()
    assert "elevenlabs_audio" in AudioProviderFactory.list_providers()
    direct = ElevenLabsAudioProviderAdapter(api_key="test-key")
    assert direct.provider_id == "elevenlabs_audio"
    caps = direct.get_capabilities()
    assert set(["VO", "DIALOGUE", "BGM", "SFX", "AMBIENCE"]).issubset(set(caps.supported_audio_types))
    assert caps.supports_voice_cloning is False


def test_missing_credentials_fail_before_http(monkeypatch):
    def forbidden_client(**_kwargs):
        raise AssertionError("HTTP must not open without valid config")

    monkeypatch.setattr("app.providers.audio.elevenlabs_adapter.httpx.AsyncClient", forbidden_client)
    adapter = ElevenLabsAudioProviderAdapter(api_key="", default_voice_id="voice_123")
    result = asyncio.run(
        adapter.generate_audio(
            AudioGenerationParams(clip_id="c1", audio_type="VO", prompt="hello", duration_seconds=2.0)
        )
    )
    assert result.status == "FAILED"
    assert result.error_code == "INVALID_CONFIG"
    assert result.submission_uncertain is False


def test_vo_routes_tts_and_reconciles_character_cost(monkeypatch):
    text = "สวัสดีจาก Orbis"
    headers = {
        "content-type": "audio/mpeg",
        "request-id": "req-tts-1",
        "character-cost": str(len(text)),
    }
    captured = _patch_http(monkeypatch, _FakeResponse(headers=headers))
    result = asyncio.run(
        _adapter().generate_audio(
            AudioGenerationParams(
                clip_id="voice-clip",
                audio_type="VO",
                prompt=text,
                duration_seconds=4.0,
                language="th",
            )
        )
    )

    assert result.status == "COMPLETED"
    assert result.audio_data == b"mp3-bytes"
    assert result.content_type == "audio/mpeg"
    assert result.provider_job_id == "req-tts-1"
    assert result.cost_usd == pytest.approx(len(text) / 1000 * settings.ELEVENLABS_TTS_COST_PER_1K_CHARS_USD)
    assert captured[0]["url"].endswith("/text-to-speech/voice_123")
    assert captured[0]["json"]["model_id"] == "eleven_v3"
    assert captured[0]["json"]["language_code"] == "th"
    assert captured[0]["params"]["output_format"] == "mp3_44100_128"
    assert captured[0]["headers"]["xi-api-key"] == "test-key"
    assert "test-key" not in str(result.raw_response)


def test_vo_missing_voice_fails_closed_without_http(monkeypatch):
    def forbidden_client(**_kwargs):
        raise AssertionError("HTTP must not open without voice")

    monkeypatch.setattr("app.providers.audio.elevenlabs_adapter.httpx.AsyncClient", forbidden_client)
    adapter = ElevenLabsAudioProviderAdapter(api_key="test-key", default_voice_id="")
    result = asyncio.run(
        adapter.generate_audio(
            AudioGenerationParams(clip_id="c2", audio_type="DIALOGUE", prompt="Hello", duration_seconds=2.0)
        )
    )
    assert result.error_code == "VOICE_ID_REQUIRED"
    assert result.cost_usd == 0.0


def test_bgm_routes_music_with_duration_and_cost(monkeypatch):
    captured = _patch_http(monkeypatch, _FakeResponse())
    params = AudioGenerationParams(
        clip_id="bgm-1",
        audio_type="BGM",
        prompt="Warm cinematic corporate score",
        duration_seconds=30.0,
    )
    adapter = _adapter()
    assert adapter.estimate_cost(params) == pytest.approx(0.075)
    result = asyncio.run(adapter.generate_audio(params))
    assert result.status == "COMPLETED"
    assert result.cost_usd == pytest.approx(0.075)
    assert result.duration_seconds == 30.0
    assert captured[0]["url"].endswith("/music")
    assert captured[0]["json"]["model_id"] == "music_v2"
    assert captured[0]["json"]["music_length_ms"] == 30000


def test_sfx_and_ambience_route_sound_generation(monkeypatch):
    captured = _patch_http(monkeypatch, _FakeResponse())
    adapter = _adapter()

    sfx = AudioGenerationParams(
        clip_id="sfx-1",
        audio_type="SFX",
        prompt="Metal door latch click",
        duration_seconds=4.0,
    )
    sfx_result = asyncio.run(adapter.generate_audio(sfx))
    assert sfx_result.cost_usd == pytest.approx(0.008)
    assert captured[-1]["url"].endswith("/sound-generation")
    assert captured[-1]["json"]["loop"] is False

    ambience = AudioGenerationParams(
        clip_id="amb-1",
        audio_type="AMBIENCE",
        prompt="Quiet factory ventilation room tone",
        duration_seconds=15.0,
    )
    amb_result = asyncio.run(adapter.generate_audio(ambience))
    assert amb_result.cost_usd == pytest.approx(0.03)
    assert captured[-1]["json"]["loop"] is True
    assert captured[-1]["json"]["model_id"] == "eleven_text_to_sound_v2"


def test_tts_missing_cost_header_requires_reconciliation(monkeypatch):
    headers = {"content-type": "audio/mpeg", "request-id": "req-no-cost"}
    _patch_http(monkeypatch, _FakeResponse(headers=headers))
    result = asyncio.run(
        _adapter().generate_audio(
            AudioGenerationParams(clip_id="c3", audio_type="VO", prompt="hello", duration_seconds=2.0)
        )
    )
    assert result.status == "COMPLETED"
    assert result.submission_uncertain is True
    assert result.error_code == "COST_EVIDENCE_MISSING"
    assert result.cost_usd is None


def test_http_503_is_retryable_and_uncertain(monkeypatch):
    _patch_http(monkeypatch, _FakeResponse(status_code=503, content=b"provider error"))
    result = asyncio.run(
        _adapter().generate_audio(
            AudioGenerationParams(clip_id="c4", audio_type="BGM", prompt="score", duration_seconds=10.0)
        )
    )
    assert result.status == "FAILED"
    assert result.error_code == "HTTP_ERROR"
    assert result.retryable is True
    assert result.submission_uncertain is True
    assert result.cost_usd is None
    assert result.raw_response is None


class _BudgetProbeAudioAdapter(IAudioProviderAdapter):
    calls = 0
    fail = False

    @property
    def provider_id(self):
        return "r4_budget_probe"

    def get_capabilities(self):
        return AudioProviderCapabilities(
            provider_id=self.provider_id,
            supported_audio_types=["BGM"],
            supports_tts=False,
            supports_music=True,
            supports_sfx=False,
            supported_formats=["audio/mpeg"],
        )

    def validate_config(self, config):
        return True

    def estimate_cost(self, params):
        return 0.075

    async def generate_audio(self, params):
        type(self).calls += 1
        if type(self).fail:
            return AudioJobResult(
                provider_job_id="probe-failed",
                status="FAILED",
                error_code="PROVIDER_REJECTED",
                error_message="PROVIDER_REJECTED",
                cost_usd=0.0,
            )
        return AudioJobResult(
            provider_job_id="probe-ok",
            status="COMPLETED",
            audio_data=b"fake-mp3",
            content_type="audio/mpeg",
            duration_seconds=params.duration_seconds,
            cost_usd=0.075,
            raw_response={"provider": self.provider_id},
        )

    async def check_job_status(self, provider_job_id):
        return AudioJobResult(provider_job_id=provider_job_id, status="FAILED", error_code="UNSUPPORTED")


def _bgm_clip(db_session, budget):
    project = Project(
        id=uuid.uuid4(),
        title="R4 Cost Project",
        video_mode="STORY",
        status="AUDIO_PLAN_APPROVED",
        budget_limit=budget,
    )
    db_session.add(project)
    db_session.flush()
    clip = AudioClip(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Main Theme",
        prompt="Corporate cinematic music",
        audio_type=AudioType.BGM.value,
        source_type=AudioSourceType.GENERATED_AUDIO.value,
        generation_mode=AudioGenerationMode.SEPARATE_AUDIO.value,
        scope=AudioScope.PROJECT.value,
        ducking_role=DuckingRole.BACKGROUND.value,
        duration_seconds=30.0,
        status="PENDING",
    )
    db_session.add(clip)
    db_session.commit()
    return project, clip


def test_service_uses_provider_estimate_before_paid_dispatch(db_session):
    AudioProviderFactory.register_provider("r4_budget_probe", _BudgetProbeAudioAdapter)
    _BudgetProbeAudioAdapter.calls = 0
    _BudgetProbeAudioAdapter.fail = False
    project, clip = _bgm_clip(db_session, budget=0.06)

    with pytest.raises(HTTPException) as exc:
        AudioProductionService.generate_clip_audio(
            db_session,
            project.id,
            clip.id,
            provider_name="r4_budget_probe",
            cost_authorized=True,
        )
    assert exc.value.status_code == 402
    assert _BudgetProbeAudioAdapter.calls == 0
    db_session.refresh(clip)
    assert clip.status == "PENDING"


def test_service_confirms_provider_cost_and_asset_lineage(db_session):
    AudioProviderFactory.register_provider("r4_budget_probe", _BudgetProbeAudioAdapter)
    _BudgetProbeAudioAdapter.calls = 0
    _BudgetProbeAudioAdapter.fail = False
    project, clip = _bgm_clip(db_session, budget=1.0)

    ready = AudioProductionService.generate_clip_audio(
        db_session,
        project.id,
        clip.id,
        provider_name="r4_budget_probe",
        cost_authorized=True,
    )
    assert ready.status == "READY"
    assert ready.asset_id is not None
    assert ready.provenance["provider"] == "r4_budget_probe"
    assert ready.provenance["cost_usd"] == pytest.approx(0.075)
    ledger = db_session.query(UsageLedger).filter(UsageLedger.project_id == project.id).first()
    assert ledger is not None
    assert ledger.estimated_cost == pytest.approx(0.075)
    assert ledger.actual_cost == pytest.approx(0.075)
    assert ledger.cost_status == "CONFIRMED"


def test_service_provider_failure_reconciles_zero_cost_without_invalid_status(db_session):
    AudioProviderFactory.register_provider("r4_budget_probe", _BudgetProbeAudioAdapter)
    _BudgetProbeAudioAdapter.calls = 0
    _BudgetProbeAudioAdapter.fail = True
    project, clip = _bgm_clip(db_session, budget=1.0)

    with pytest.raises(HTTPException) as exc:
        AudioProductionService.generate_clip_audio(
            db_session,
            project.id,
            clip.id,
            provider_name="r4_budget_probe",
            cost_authorized=True,
        )
    assert exc.value.status_code == 502
    db_session.refresh(clip)
    assert clip.status == "FAILED"
    ledger = db_session.query(UsageLedger).filter(UsageLedger.project_id == project.id).first()
    assert ledger is not None
    assert ledger.actual_cost == pytest.approx(0.0)
    assert ledger.cost_status == "CONFIRMED"
