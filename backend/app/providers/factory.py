from typing import Dict, Any, Type
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
    def get_provider(cls, provider_id: str = "vidu", **kwargs: Any) -> IVideoGenerationProviderAdapter:
        provider_id_clean = provider_id.lower()
        if provider_id_clean not in cls._registry:
            raise ValueError(f"Unsupported provider: '{provider_id}'. Available: {list(cls._registry.keys())}")
        adapter_cls = cls._registry[provider_id_clean]
        return adapter_cls(**kwargs)
