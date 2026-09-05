import io
from typing import BinaryIO, Union, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.services.storage.base import ObjectStorageProvider


class S3CompatibleObjectStorageProvider(ObjectStorageProvider):
    """S3-compatible implementation of ObjectStorageProvider (AWS S3, MinIO, Cloudflare R2, Backblaze B2)."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        use_ssl: bool = False,
    ):
        self.endpoint_url = endpoint_url
        self.region_name = region_name
        self.use_ssl = use_ssl

        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url if endpoint_url else None,
            aws_access_key_id=aws_access_key_id if aws_access_key_id else None,
            aws_secret_access_key=aws_secret_access_key if aws_secret_access_key else None,
            region_name=region_name,
            use_ssl=use_ssl,
            config=config,
        )

    def ensure_bucket_exists(self, bucket: str) -> None:
        try:
            self.client.head_bucket(Bucket=bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                try:
                    if self.region_name and self.region_name != "us-east-1":
                        self.client.create_bucket(
                            Bucket=bucket,
                            CreateBucketConfiguration={
                                "LocationConstraint": self.region_name
                            },
                        )
                    else:
                        self.client.create_bucket(Bucket=bucket)
                except ClientError as create_err:
                    # Bucket might have been created concurrently
                    pass
            else:
                raise

    def put_object(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
    ) -> str:
        self.ensure_bucket_exists(bucket)

        if isinstance(data, bytes):
            body = data
        else:
            body = data.read()

        self.client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
        return key

    def get_object(self, bucket: str, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchKey"):
                raise KeyError(f"Object '{key}' not found in bucket '{bucket}'.")
            raise

    def delete_object(self, bucket: str, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to delete object '{key}' from bucket '{bucket}': {e}")

    def object_exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchKey"):
                return False
            return False

    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        client_method: str = "get_object",
        expires_in: int = 3600,
    ) -> str:
        try:
            return self.client.generate_presigned_url(
                ClientMethod=client_method,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")
