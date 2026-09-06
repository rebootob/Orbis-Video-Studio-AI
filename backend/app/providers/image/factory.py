"""Factory for resolving and instantiating Image Generation Provider Adapters."""
from typing import Dict, Any, Type, Optional
from app.providers.image.base import IImageGenerationProviderAdapter
from app.providers.image.mock_adapter import MockImageProviderAdapter


class ImageProviderFactory:
    _registry: Dict[str, Type[IImageGenerationProviderAdapter]] = {
        "mock_image": MockImageProviderAdapter,
        "default": MockImageProviderAdapter,
    }

    @classmethod
    def register(cls, provider_id: str, adapter_cls: Type[IImageGenerationProviderAdapter]) -> None:
        cls._registry[provider_id.lower()] = adapter_cls

    @classmethod
    def get_default_provider_name(cls) -> str:
        from app.core.config import settings
        return getattr(settings, "DEFAULT_IMAGE_PROVIDER", "mock_image")

    @classmethod
    def get_provider(
        cls, provider_id: Optional[str] = None, **kwargs: Any
    ) -> IImageGenerationProviderAdapter:
        target_provider = (provider_id or cls.get_default_provider_name()).lower()
        if target_provider not in cls._registry:
            raise ValueError(
                f"Unsupported image provider: '{target_provider}'. Available: {list(cls._registry.keys())}"
            )
        adapter_cls = cls._registry[target_provider]
        return adapter_cls(**kwargs)
