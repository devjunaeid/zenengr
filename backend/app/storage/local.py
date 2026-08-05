"""Local filesystem storage backend (FEAT-012, FR-12.1).

Writes objects under a root directory. `public/` keys are exposed through the
static `/uploads` mount; everything else is private and served through the
auth-gated content endpoint. All blocking IO runs in worker threads.
"""

from __future__ import annotations

import asyncio
from pathlib import Path


class LocalStorageBackend:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _resolve(self, key: str) -> Path:
        """Validate a key and resolve it under the root. Rejects traversal."""
        if not key:
            raise ValueError("storage key must not be empty")
        if key.startswith("/"):
            raise ValueError("storage key must be relative")
        parts = Path(key).parts
        if ".." in parts:
            raise ValueError("storage key must not contain '..' segments")
        return self._root / key

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        target = self._resolve(key)
        await asyncio.to_thread(self._write, target, data)

    def _write(self, target: Path, data: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    async def get(self, key: str) -> bytes | None:
        target = self._resolve(key)
        return await asyncio.to_thread(self._read, target)

    def _read(self, target: Path) -> bytes | None:
        if not target.is_file():
            return None
        return target.read_bytes()

    async def delete(self, key: str) -> None:
        target = self._resolve(key)
        await asyncio.to_thread(self._unlink, target)

    def _unlink(self, target: Path) -> None:
        target.unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        target = self._resolve(key)
        return await asyncio.to_thread(target.is_file)

    def url(
        self,
        key: str,
        *,
        download: bool = False,
        expires_seconds: int = 900,
    ) -> str | None:
        self._resolve(key)
        if key.startswith("public/"):
            return f"/uploads/{key[len('public/') :]}"
        return None
