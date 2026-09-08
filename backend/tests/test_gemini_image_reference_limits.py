import asyncio
import uuid

from app.providers.image.base import ImageGenerationParams, ReferenceImageInput
from app.providers.image.gemini_adapter import GeminiImageProviderAdapter


def _ref(kind: str) -> ReferenceImageInput:
    return ReferenceImageInput(
        type=kind,
        url=f"/assets/{uuid.uuid4()}/download",
        weight=1.0,
    )


def test_more_than_four_character_references_fail_before_materialization():
    calls = []

    def resolver(url):
        calls.append(url)
        return b"image", "image/png"

    adapter = GeminiImageProviderAdapter(api_key="test-key", reference_resolver=resolver)
    result = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(
                shot_id=str(uuid.uuid4()),
                prompt="Maintain character continuity",
                reference_images=[_ref("character") for _ in range(5)],
            )
        )
    )
    assert result.status == "FAILED"
    assert result.error_code == "CHARACTER_REFERENCE_COUNT_UNSUPPORTED"
    assert calls == []


def test_more_than_ten_location_references_fail_before_materialization():
    adapter = GeminiImageProviderAdapter(
        api_key="test-key",
        reference_resolver=lambda _url: (b"image", "image/png"),
    )
    result = asyncio.run(
        adapter.generate_image(
            ImageGenerationParams(
                shot_id=str(uuid.uuid4()),
                prompt="Maintain location continuity",
                reference_images=[_ref("location") for _ in range(11)],
            )
        )
    )
    assert result.status == "FAILED"
    assert result.error_code == "LOCATION_REFERENCE_COUNT_UNSUPPORTED"
