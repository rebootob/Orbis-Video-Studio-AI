"""Registry and factory for Audio Generation Providers."""
from typing import Dict, Type, Optional, List
from app.providers.audio.base import IAudioProviderAdapter
from app.providers.audio.mock_adapter import MockAudioProviderAdapter


class AudioProviderFactory:
    _registry: Dict[str, Type[IAudioProviderAdapter]] = {
        "mock_audio": MockAudioProviderAdapter,
    }
    _instances: Dict[str, IAudioProviderAdapter] = {}
    _default_provider_name: str = "mock_audio"

    @classmethod
    def register_provider(cls, name: str, adapter_cls: Type[IAudioProviderAdapter]) -> None:
        cls._registry[name] = adapter_cls

    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> IAudioProviderAdapter:
        provider_name = name or cls._default_provider_name
        if provider_name not in cls._instances:
            if provider_name not in cls._registry:
                raise ValueError(f"Unknown audio provider adapter '{provider_name}'. Registered: {list(cls._registry.keys())}")
            cls._instances[provider_name] = cls._registry[provider_name]()
        return cls._instances[provider_name]

    @classmethod
    def get_default_provider_name(cls) -> str:
        return cls._default_provider_name

    @classmethod
    def set_default_provider_name(cls, name: str) -> None:
        if name not in cls._registry:
            raise ValueError(f"Cannot set default: Unknown audio provider '{name}'")
        cls._default_provider_name = name

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._registry.keys())
