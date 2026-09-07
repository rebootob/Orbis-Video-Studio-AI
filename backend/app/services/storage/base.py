from abc import ABC, abstractmethod
from typing import BinaryIO, Union, Optional


class ObjectStorageProvider(ABC):
    """Provider-neutral abstract interface for object storage operations."""

    @abstractmethod
    def put_object(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload an object into storage. Returns object storage key."""
        pass

    @abstractmethod
    def get_object(self, bucket: str, key: str) -> bytes:
        """Retrieve object payload bytes from storage."""
        pass

    @abstractmethod
    def delete_object(self, bucket: str, key: str) -> bool:
        """Delete an object from storage. Returns True if successfully deleted."""
        pass

    @abstractmethod
    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in storage."""
        pass

    @abstractmethod
    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        client_method: str = "get_object",
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL for secure access to the object."""
        pass

    @abstractmethod
    def upload_file_object(
        self,
        bucket: str,
        key: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file from disk into storage without loading the whole file into RAM."""
        pass

    @abstractmethod
    def download_file_object(self, bucket: str, key: str, target_file_path: str) -> None:
        """Download an object from storage directly to a file on disk."""
        pass

    @abstractmethod
    def ensure_bucket_exists(self, bucket: str) -> None:
        """Ensure target storage bucket exists."""
        pass
