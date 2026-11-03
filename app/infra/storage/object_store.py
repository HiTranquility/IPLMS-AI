"""Tải object bằng signed URL mà không phụ thuộc SDK của nhà cung cấp.

Backend hoặc hạ tầng tạo signed GET URL cho S3, MinIO hay R2. AI service chỉ
nhận URL ngắn hạn, tải theo luồng và kiểm SHA-256 trước khi công bố file.
"""
from __future__ import annotations

import hashlib
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class ObjectDownloadError(RuntimeError):
    """Object không tải được hoặc không vượt qua kiểm tra toàn vẹn."""


@dataclass(frozen=True)
class ObjectDownloadRequest:
    url: str
    destination: Path
    expected_sha256: str
    timeout_seconds: int
    max_bytes: int
    allow_insecure_http: bool = False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ObjectStore:
    """Adapter đọc object storage qua một signed HTTPS URL."""

    def download(self, request: ObjectDownloadRequest) -> Path:
        expected_hash = request.expected_sha256.strip().lower()
        if not _SHA256_PATTERN.fullmatch(expected_hash):
            raise ObjectDownloadError("Remote model artifact requires a valid SHA-256 digest")

        scheme = urlparse(request.url).scheme.lower()
        allowed_schemes = {"https"}
        if request.allow_insecure_http:
            allowed_schemes.add("http")
        if scheme not in allowed_schemes:
            raise ObjectDownloadError("Model artifact URL must use HTTPS")

        request.destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = request.destination.with_name(
            f".{request.destination.name}.{os.getpid()}.{threading.get_ident()}.part"
        )

        digest = hashlib.sha256()
        downloaded_bytes = 0
        try:
            http_request = Request(request.url, headers={"User-Agent": "iplms-ai-model-loader/1"})
            with urlopen(http_request, timeout=request.timeout_seconds) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > request.max_bytes:
                    raise ObjectDownloadError("Model artifact exceeds configured size limit")

                with temporary_path.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        downloaded_bytes += len(chunk)
                        if downloaded_bytes > request.max_bytes:
                            raise ObjectDownloadError("Model artifact exceeds configured size limit")
                        digest.update(chunk)
                        output.write(chunk)

            if digest.hexdigest() != expected_hash:
                raise ObjectDownloadError("Downloaded model artifact failed SHA-256 verification")

            os.replace(temporary_path, request.destination)
            return request.destination
        except ObjectDownloadError:
            raise
        except Exception as exc:
            # Signed URL có thể chứa credential; không đưa URL vào exception/log.
            raise ObjectDownloadError(f"Could not download model artifact: {type(exc).__name__}") from exc
        finally:
            temporary_path.unlink(missing_ok=True)
