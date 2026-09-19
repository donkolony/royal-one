"""File storage behind a small interface. Buckets are private; users only ever get short-lived signed URLs."""
from __future__ import annotations

import re
import time
from typing import Dict, List, Protocol, Tuple

from app.core.errors import ApiError


class Storage(Protocol):
    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None: ...
    def signed_url(self, bucket: str, path: str, ttl_seconds: int) -> str: ...
    def signed_urls(self, bucket: str, paths: List[str], ttl_seconds: int) -> Dict[str, str]: ...
    def delete(self, bucket: str, paths: List[str]) -> None: ...


class MemoryStorage:
    """Tests and offline development. Signed URLs are not fetchable."""

    def __init__(self) -> None:
        self.files: Dict[Tuple[str, str], Tuple[bytes, str]] = {}

    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        self.files[(bucket, path)] = (data, content_type)

    def signed_url(self, bucket: str, path: str, ttl_seconds: int) -> str:
        return f"memory://{bucket}/{path}?expires={int(time.time()) + ttl_seconds}"

    def signed_urls(self, bucket: str, paths: List[str], ttl_seconds: int) -> Dict[str, str]:
        return {p: self.signed_url(bucket, p, ttl_seconds) for p in paths}

    def delete(self, bucket: str, paths: List[str]) -> None:
        for p in paths:
            self.files.pop((bucket, p), None)


class SupabaseStorage:
    def __init__(self, url: str, key: str):
        from supabase import create_client

        self._client = create_client(url, key)

    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        try:
            self._client.storage.from_(bucket).upload(path, data, {"content-type": content_type, "upsert": "true"})
        except Exception as e:
            raise ApiError(502, "upstream_error", "File storage is unavailable.") from e

    def signed_url(self, bucket: str, path: str, ttl_seconds: int) -> str:
        try:
            res = self._client.storage.from_(bucket).create_signed_url(path, ttl_seconds)
        except Exception as e:
            raise ApiError(502, "upstream_error", "File storage is unavailable.") from e
        url = res.get("signedURL") or res.get("signedUrl")
        if not url:
            raise ApiError(502, "upstream_error", "File storage returned no URL.")
        return url

    def signed_urls(self, bucket: str, paths: List[str], ttl_seconds: int) -> Dict[str, str]:
        if not paths:
            return {}
        try:
            res = self._client.storage.from_(bucket).create_signed_urls(paths, ttl_seconds)
        except Exception as e:
            raise ApiError(502, "upstream_error", "File storage is unavailable.") from e
        out: Dict[str, str] = {}
        for item in res:
            url = item.get("signedURL") or item.get("signedUrl")
            if item.get("error") or not url:
                raise ApiError(502, "upstream_error", "File storage could not sign a file URL.")
            out[item["path"]] = url
        return out

    def delete(self, bucket: str, paths: List[str]) -> None:
        try:
            self._client.storage.from_(bucket).remove(paths)
        except Exception as e:
            raise ApiError(502, "upstream_error", "File storage is unavailable.") from e


_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    """Filenames are display metadata only and are never used as paths; this keeps storage keys tame."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _UNSAFE.sub("_", base).strip("._") or "file"
    return cleaned[:100]
