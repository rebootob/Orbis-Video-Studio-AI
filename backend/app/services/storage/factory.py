from typing import Optional
from app.core.config import settings
from app.services.storage.base import ObjectStorageProvider
from app.services.storage.s3 import S3CompatibleObjectStorageProvider
from app.services.storage.mock import InMemoryObjectStorageProvider

_storage_provider_override: Optional[ObjectStorageProvider] = None


def set_storage_provider_override(provider: Optional[ObjectStorageProvider]) -> None:
    global _storage_provider_override
    _storage_provider_override = provider


def get_storage_provider() -> ObjectStorageProvider:
    """Factory function returning active ObjectStorageProvider instance."""
    if _storage_provider_override is not None:
        return _storage_provider_override

    return S3CompatibleObjectStorageProvider(
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_KEY,
        region_name=settings.OBJECT_STORAGE_REGION,
        use_ssl=settings.OBJECT_STORAGE_SECURE,
    )
