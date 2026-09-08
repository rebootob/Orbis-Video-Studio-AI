"""P4-WP020-LIVE R2 no-paid preflight.

This script MUST NOT dispatch any external Creative/Image/Video/Audio provider
request. It validates only credential presence, production adapter configuration,
pricing/budget guards, database runtime, and S3-compatible object storage.

No secret values are printed. No EXECUTION_STARTED marker is written. No paid
execution fence is consumed by this script.
"""
from __future__ import annotations

import json
import os
import uuid

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.usage_ledger import UsageLedger
from app.providers.audio.base import AudioGenerationParams
from app.providers.audio.elevenlabs_adapter import ElevenLabsAudioProviderAdapter
from app.providers.image.gemini_adapter import GeminiImageProviderAdapter
from app.providers.vidu import ViduProviderAdapter
from app.services.creative_generation.openai_provider import OpenAICreativeGenerationProvider
from app.services.pricing import CostStatus, ProviderPricingService
from app.services.storage.factory import get_storage_provider

REQUIRED_SECRET_NAMES = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "VIDU_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_DEFAULT_VOICE_ID",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"PREFLIGHT_FAIL: {message}")


def main() -> None:
    missing = [name for name in REQUIRED_SECRET_NAMES if not os.environ.get(name, "").strip()]
    require(not missing, "missing required credential/config names: " + ", ".join(missing))

    require(settings.OPENAI_CREATIVE_MODEL == "gpt-4o", "OPENAI model drift")
    require(settings.OPENAI_MAX_RETRIES == 0, "OPENAI_MAX_RETRIES must be 0")
    require(settings.GEMINI_IMAGE_MODEL == "gemini-3.1-flash-image", "Gemini model drift")
    require(settings.GEMINI_IMAGE_SIZE == "1K", "Gemini image size must be 1K")
    require(settings.VIDU_DEFAULT_MODEL == "viduq2", "Vidu model drift")
    require(settings.DEFAULT_IMAGE_PROVIDER == "gemini_image", "image routing is not production Gemini")
    require(settings.DEFAULT_VIDEO_PROVIDER == "vidu", "video routing is not production Vidu")
    require(settings.DEFAULT_AUDIO_PROVIDER == "elevenlabs_audio", "audio routing is not production ElevenLabs")

    # Constructor/config validation only. Do not invoke generation methods.
    openai = OpenAICreativeGenerationProvider()
    gemini = GeminiImageProviderAdapter()
    vidu = ViduProviderAdapter()
    eleven = ElevenLabsAudioProviderAdapter()
    require(bool(getattr(openai, "api_key", "").strip()), "OpenAI adapter credential missing")
    require(gemini.validate_config({}), "Gemini production adapter config invalid")
    require(vidu.validate_config({}), "Vidu production adapter config invalid")
    require(eleven.validate_config({}), "ElevenLabs production adapter config invalid")

    ProviderPricingService.reset()
    openai_cost, currency, pricing_status = ProviderPricingService.estimate_cost(
        "openai",
        "STORY_GENERATION",
        "gpt-4o",
        {"prompt_tokens": 500, "completion_tokens": 1000},
    )
    require(
        pricing_status != CostStatus.UNKNOWN
        and currency == "USD"
        and openai_cost is not None
        and openai_cost > 0,
        "OpenAI pricing is UNKNOWN",
    )

    image_cost, currency, pricing_status = ProviderPricingService.estimate_cost(
        "gemini_image", "IMAGE_GENERATION", "gemini-3.1-flash-image", {}
    )
    require(
        pricing_status != CostStatus.UNKNOWN
        and currency == "USD"
        and image_cost is not None
        and 0 < image_cost <= 0.08,
        "Gemini pricing is UNKNOWN/outside 1K reservation",
    )

    vidu_cost, currency, pricing_status = ProviderPricingService.estimate_cost(
        "vidu", "VIDEO_GENERATION", "viduq2", {"duration_seconds": 4.0}
    )
    require(
        pricing_status != CostStatus.UNKNOWN
        and currency == "USD"
        and vidu_cost is not None
        and 0 < vidu_cost <= 0.15,
        "Vidu pricing is UNKNOWN/outside 4s 720P bound",
    )

    vo_cost = eleven.estimate_cost(
        AudioGenerationParams(
            clip_id="r2-preflight-vo",
            audio_type="VO",
            prompt="ทดสอบเสียงภาษาไทย",
            duration_seconds=3.0,
        )
    )
    bgm_cost = eleven.estimate_cost(
        AudioGenerationParams(
            clip_id="r2-preflight-bgm",
            audio_type="BGM",
            prompt="calm corporate instrumental",
            duration_seconds=10.0,
        )
    )
    ambience_cost = eleven.estimate_cost(
        AudioGenerationParams(
            clip_id="r2-preflight-ambience",
            audio_type="AMBIENCE",
            prompt="quiet office ambience",
            duration_seconds=3.0,
        )
    )
    require(
        all(value is not None and value > 0 for value in (vo_cost, bgm_cost, ambience_cost)),
        "ElevenLabs price estimator returned UNKNOWN",
    )

    storage = get_storage_provider()
    bucket = settings.OBJECT_STORAGE_BUCKET
    key = f"wp020-live-r2-preflight/{uuid.uuid4()}.txt"
    payload = b"orbis-live-r2-preflight"
    storage.put_object(bucket, key, payload, "text/plain")
    require(storage.object_exists(bucket, key), "UAT object storage write not visible")
    require(storage.get_object(bucket, key) == payload, "UAT object storage read-back mismatch")
    storage.delete_object(bucket, key)

    db = SessionLocal()
    try:
        project = Project(
            id=uuid.uuid4(),
            title="WP020 LIVE R2 Preflight",
            description="No-paid R2 preflight only",
            video_mode="STORY",
            status="DRAFT",
            automation_mode="MANUAL",
            target_duration_seconds=30.0,
            budget_limit=1.0,
            budget_currency="USD",
            budget_threshold_percentage=80.0,
        )
        db.add(project)
        db.commit()
        require(project.budget_limit == 1.0, "UAT budget limit mismatch")
        require(project.budget_currency == "USD", "UAT budget currency mismatch")
        require(project.budget_threshold_percentage == 80.0, "UAT budget threshold mismatch")

        ledger_count = db.query(UsageLedger).filter(UsageLedger.project_id == project.id).count()
        require(ledger_count == 0, "UAT project did not start at zero ledger events")
        require(db.query(GenerationJob).count() == 0, "ephemeral UAT database unexpectedly contains generation jobs")
    finally:
        db.close()

    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASS",
                "preflight_main_sha": os.environ.get("PREFLIGHT_MAIN_SHA", ""),
                "required_credentials_present": True,
                "provider_routing": {
                    "creative": "openai:gpt-4o",
                    "image": "gemini_image:gemini-3.1-flash-image:1K",
                    "video": "vidu:viduq2:720P:4s",
                    "audio": "elevenlabs_audio",
                },
                "pricing_estimates_usd": {
                    "openai_sample": openai_cost,
                    "gemini_1k_reservation": image_cost,
                    "vidu_4s_720p": vidu_cost,
                    "elevenlabs_vo_sample": vo_cost,
                    "elevenlabs_bgm_10s": bgm_cost,
                    "elevenlabs_ambience_3s": ambience_cost,
                },
                "budget_cap_usd": 1.0,
                "execution_fence_written": False,
                "paid_provider_calls": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
