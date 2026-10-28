"""Thử kết nối tới provider LLM: sống không, đúng key không, có model nào (REQ-020 F3).

Chống SSRF (IPLMS ADR-0061 §7): phân giải DNS một lần, đưa MỌI địa chỉ cho
`check_addresses` (luật ở core) rồi kết nối thẳng vào đúng IP vừa kiểm, nên tên
miền không thể đổi sang IP khác giữa lúc kiểm và lúc nối (DNS rebinding).
Không theo redirect; đọc tối đa 1 MiB; một deadline chung cho cả lượt thử.
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import ssl
import time
from typing import Any, Callable, Iterable
from urllib.parse import urlsplit

_MAX_BODY = 1024 * 1024
_MAX_MODELS = 200
_MAX_MODEL_NAME = 120

ERRORS = ("unreachable", "auth_failed", "timeout", "no_models", "blocked_host")


def _result(ok: bool, error: str, started: float | None, models: list[str] | None = None,
            detail: str = "") -> dict[str, Any]:
    latency = int((time.monotonic() - started) * 1000) if started is not None else None
    return {"ok": ok, "error": error, "latency_ms": latency, "models": models or [], "detail": detail}


def models_path(provider: str, base_path: str) -> str:
    """Ollama: `/api/tags`; llama-server và OpenAI: `/v1/models` (chuẩn OpenAI)."""
    path = base_path.rstrip("/")
    if provider == "ollama":
        return path.removesuffix("/v1") + "/api/tags"
    return (path if path.endswith("/v1") else path + "/v1") + "/models"


def parse_models(provider: str, body: bytes) -> list[str]:
    data = json.loads(body.decode("utf-8"))
    items = data.get("models") if provider == "ollama" else data.get("data")
    names: list[str] = []
    for item in items or []:
        name = item.get("name") if provider == "ollama" else item.get("id")
        if isinstance(name, str) and name:
            names.append(name[:_MAX_MODEL_NAME])
        if len(names) >= _MAX_MODELS:
            break
    return names


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Nối vào IP đã kiểm, nhưng SNI + kiểm chứng chỉ vẫn theo tên host gốc."""

    def __init__(self, host: str, ip: str, port: int, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self) -> None:
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, ip: str, port: int, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


def _resolve(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(info[4][0] for info in infos))


def probe(
    provider: str,
    base_url: str,
    secret_env_name: str,
    check_addresses: Callable[[Iterable[str]], None],
    timeout_seconds: float = 10.0,
    resolve: Callable[[str, int], list[str]] = _resolve,
) -> dict[str, Any]:
    """Không bao giờ ném lỗi mạng ra ngoài; luôn trả kết quả đã phân loại.

    `check_addresses` ném `ValueError` khi một IP bị cấm → `blocked_host`.
    """
    parts = urlsplit(base_url)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    deadline = time.monotonic() + timeout_seconds
    try:
        addresses = resolve(host, port)
    except OSError:
        return _result(False, "unreachable", None, detail="Không phân giải được host.")
    try:
        check_addresses(addresses)
    except ValueError as exc:
        return _result(False, "blocked_host", None, detail=str(exc))

    headers = {"Accept": "application/json", "User-Agent": "iplms-ai-console/connection-test"}
    if secret_env_name:
        key = os.environ.get(secret_env_name, "")
        if not key:
            return _result(False, "auth_failed", None,
                           detail=f"Biến {secret_env_name} chưa được đặt trên AI host.")
        headers["Authorization"] = f"Bearer {key}"

    cls = _PinnedHTTPSConnection if parts.scheme == "https" else _PinnedHTTPConnection
    started = time.monotonic()
    last_error = "unreachable"
    for ip in addresses:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return _result(False, "timeout", started)
        conn = cls(host, ip, port, remaining)
        try:
            conn.request("GET", models_path(provider, parts.path), headers=headers)
            response = conn.getresponse()
            body = response.read(_MAX_BODY + 1)
        except (socket.timeout, TimeoutError):
            return _result(False, "timeout", started)
        except (OSError, http.client.HTTPException):
            last_error = "unreachable"
            continue
        finally:
            conn.close()
        if response.status in (401, 403):
            return _result(False, "auth_failed", started, detail=f"HTTP {response.status}")
        if response.status != 200:
            # Gồm cả 3xx: không theo redirect vì đích mới chưa qua kiểm IP.
            return _result(False, "unreachable", started, detail=f"HTTP {response.status}")
        if len(body) > _MAX_BODY:
            return _result(False, "unreachable", started, detail="Phản hồi lớn quá 1 MiB.")
        try:
            models = parse_models(provider, body)
        except (ValueError, AttributeError, TypeError):
            return _result(False, "unreachable", started, detail="Phản hồi không phải danh sách model.")
        if not models:
            return _result(False, "no_models", started)
        return _result(True, "", started, models)
    return _result(False, last_error, started)
