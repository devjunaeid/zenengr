"""S3-compatible storage backend (FEAT-012, FR-12.1).

Talks to AWS S3 or any S3-compatible service (MinIO etc.) via boto3.
The client is created lazily on first use so config problems surface only
when storage is actually touched. Keys are tenant-namespaced by callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError


class S3StorageBackend:
    def __init__(
        self,
        *,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        self._bucket = bucket
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._endpoint_url = endpoint_url
        self._region = region
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint_url,
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
                region_name=self._region,
            )
        return self._client

    def _validate_key(self, key: str) -> None:
        """Reject empty, absolute, and traversal keys (shared protocol rule)."""
        if not key:
            raise ValueError("storage key must not be empty")
        if key.startswith("/"):
            raise ValueError("storage key must be relative")
        if ".." in Path(key).parts:
            raise ValueError("storage key must not contain '..' segments")

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self._validate_key(key)
        self.client.put_object(
            Bucket=self._bucket,
            Body=data,
            Key=key,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes | None:
        self._validate_key(key)
        try:
            obj = self.client.get_object(Bucket=self._bucket, Key=key)
            data: bytes = obj["Body"].read()
            return data
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    async def delete(self, key: str) -> None:
        self._validate_key(key)
        try:
            self.client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "NoSuchKey":
                return
            raise

    async def exists(self, key: str) -> bool:
        self._validate_key(key)
        try:
            self.client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NotFound", "NoSuchKey"):
                return False
            raise

    def url(
        self,
        key: str,
        *,
        download: bool = False,
        expires_seconds: int = 900,
    ) -> str | None:
        self._validate_key(key)
        if not self._bucket:
            return None
        params: dict[str, Any] = {"Bucket": self._bucket, "Key": key}
        if download:
            params["ResponseContentDisposition"] = f'attachment; filename="{Path(key).name}"'
        presigned: str = self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_seconds,
        )
        return presigned
