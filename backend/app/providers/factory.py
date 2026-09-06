from typing import Dict, Any, Type, Optional
from app.providers.base import IVideoGenerationProviderAdapter
from app.providers.vidu import ViduProviderAdapter


class ProviderFactory:
    _registry: Dict[str, Type[IVideoGenerationProviderAdapter]] = {
        "vidu": ViduProviderAdapter,
    }

    @classmethod
    def register(cls, provider_id: str, adapter_cls: Type[IVideoGenerationProviderAdapter]) -> None:
        cls._registry[provider_id.lower()] = adapter_cls

    @classmethod
    def get_default_provider_name(cls) -> str:
        from app.core.config import settings
        return getattr(settings, "DEFAULT_VIDEO_PROVIDER", "vidu")

    @classmethod
    def get_provider(cls, provider_id: Optional[str] = None, **kwargs: Any) -> IVideoGenerationProviderAdapter:
        target_provider = (provider_id or cls.get_default_provider_name()).lower()
        if target_provider not in cls._registry:
            raise ValueError(f"Unsupported provider: '{target_provider}'. Available: {list(cls._registry.keys())}")
        adapter_cls = cls._registry[target_provider]
        return adapter_cls(**kwargs)
