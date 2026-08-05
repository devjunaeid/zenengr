"""Storage backend protocol (FEAT-012, FR-12.1). All app code talks to this
interface only - switching local <-> S3 is a config change, never a code change."""

from typing import Protocol


class StorageBackend(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes | None: ...

    async def delete(self, key: str) -> None: ...

    async def exists(self, key: str) -> bool: ...

    def url(
        self,
        key: str,
        *,
        download: bool = False,
        expires_seconds: int = 900,
    ) -> str | None:
        """Return a browser-usable URL for the object.

        S3: presigned URL. Local: only for keys under the `public/` namespace
        served by the static mount; else None (content is served through the
        auth-gated content endpoint). Keys are tenant-namespaced by callers
        (`{tenant_id}/{scope}/...`); implementations reject traversal (`..`).
        """
        ...
