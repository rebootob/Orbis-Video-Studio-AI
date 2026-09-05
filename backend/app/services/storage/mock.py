from typing import BinaryIO, Union, Dict, Tuple
from app.services.storage.base import ObjectStorageProvider


class InMemoryObjectStorageProvider(ObjectStorageProvider):
    """In-memory object storage provider for testing without external S3/MinIO service."""

    def __init__(self):
        # Key: (bucket, key) -> Value: (bytes, content_type)
        self._store: Dict[Tuple[str, str], Tuple[bytes, str]] = {}
        self._buckets: set = set()
        self.simulate_deletion_failure = False

    def ensure_bucket_exists(self, bucket: str) -> None:
        self._buckets.add(bucket)

    def put_object(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
    ) -> str:
        self.ensure_bucket_exists(bucket)

        if isinstance(data, bytes):
            payload = data
        else:
            payload = data.read()

        self._store[(bucket, key)] = (payload, content_type)
        return key

    def get_object(self, bucket: str, key: str) -> bytes:
        if (bucket, key) not in self._store:
            raise KeyError(f"Object '{key}' not found in bucket '{bucket}'.")
        return self._store[(bucket, key)][0]

    def delete_object(self, bucket: str, key: str) -> bool:
        if self.simulate_deletion_failure:
            raise RuntimeError("Simulated object storage deletion failure")

        if (bucket, key) in self._store:
            del self._store[(bucket, key)]
            return True
        return False

    def object_exists(self, bucket: str, key: str) -> bool:
        return (bucket, key) in self._store

    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        client_method: str = "get_object",
        expires_in: int = 3600,
    ) -> str:
        return f"https://mock-storage.local/{bucket}/{key}?token=presigned_mock_token&expires={expires_in}"
