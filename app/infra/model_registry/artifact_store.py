"""Phân giải model artifact từ local path hoặc object storage vào cache runtime."""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import get_config
from app.infra.storage.object_store import (
    ObjectDownloadRequest,
    ObjectDownloadError,
    SignedUrlObjectStore,
    sha256_file,
)


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


class ArtifactResolutionError(RuntimeError):
    """Model artifact không có, sai checksum hoặc có định danh không an toàn."""


@dataclass(frozen=True)
class ModelArtifactSpec:
    name: str
    version: str
    file_name: str
    local_path: str = ""
    source_url: str = ""
    sha256: str = ""


class ModelArtifactRegistry:
    def __init__(
        self,
        ai_root: Path,
        cache_dir: str,
        timeout_seconds: int,
        max_bytes: int,
        allow_insecure_http: bool,
    ) -> None:
        self._ai_root = ai_root.resolve()
        cache_path = Path(cache_dir)
        self._cache_root = (
            cache_path if cache_path.is_absolute() else self._ai_root / cache_path
        ).resolve()
        self._timeout_seconds = timeout_seconds
        self._max_bytes = max_bytes
        self._allow_insecure_http = allow_insecure_http
        self._object_store = SignedUrlObjectStore()
        self._lock = threading.Lock()

    def resolve(self, spec: ModelArtifactSpec) -> Path:
        """Ưu tiên remote URL được khai báo rõ; nếu không thì dùng local path."""
        self._validate_spec(spec)

        if not spec.source_url.strip():
            if not spec.local_path.strip():
                raise ArtifactResolutionError(
                    f"No source configured for model artifact '{spec.name}'"
                )
            local_path = Path(spec.local_path)
            if not local_path.is_absolute():
                local_path = self._ai_root / local_path
            local_path = local_path.resolve()
            if local_path.is_file():
                self._verify_optional_hash(local_path, spec.sha256)
                return local_path
            raise ArtifactResolutionError(f"Local model artifact not found: {local_path}")

        destination = self._cache_root / spec.name / spec.version / spec.file_name
        with self._lock:
            if destination.is_file() and self._hash_matches(destination, spec.sha256):
                return destination
            try:
                return self._object_store.download(
                    ObjectDownloadRequest(
                        url=spec.source_url,
                        destination=destination,
                        expected_sha256=spec.sha256,
                        timeout_seconds=self._timeout_seconds,
                        max_bytes=self._max_bytes,
                        allow_insecure_http=self._allow_insecure_http,
                    )
                )
            except ObjectDownloadError as exc:
                raise ArtifactResolutionError(str(exc)) from exc

    @staticmethod
    def _validate_spec(spec: ModelArtifactSpec) -> None:
        for label, value in (("name", spec.name), ("version", spec.version), ("file_name", spec.file_name)):
            if not _SAFE_SEGMENT.fullmatch(value):
                raise ArtifactResolutionError(f"Invalid model artifact {label}: {value!r}")

    @staticmethod
    def _hash_matches(path: Path, expected_sha256: str) -> bool:
        expected = expected_sha256.strip().lower()
        return bool(expected) and sha256_file(path) == expected

    @staticmethod
    def _verify_optional_hash(path: Path, expected_sha256: str) -> None:
        expected = expected_sha256.strip().lower()
        if expected and sha256_file(path) != expected:
            raise ArtifactResolutionError(f"Local model artifact failed SHA-256 verification: {path}")


@lru_cache
def get_model_artifact_registry() -> ModelArtifactRegistry:
    config = get_config()
    ai_root = Path(__file__).resolve().parents[3]
    return ModelArtifactRegistry(
        ai_root=ai_root,
        cache_dir=config.model_registry.cache_dir,
        timeout_seconds=config.object_storage.download_timeout_seconds,
        max_bytes=config.object_storage.max_artifact_bytes,
        allow_insecure_http=config.object_storage.allow_insecure_http,
    )
