"""Opt-in, same-origin, direct-loopback developer diagnostics boundary."""
from collections import deque
from ipaddress import ip_address
from time import monotonic
from threading import Lock

from fastapi import HTTPException, Request
from app.config import get_config

_calls: deque[float] = deque()
_calls_lock = Lock()


def require_developer_access(request: Request) -> None:
    if not get_config().server.developer_dashboard_enabled:
        raise HTTPException(404, "Not found")
    peer = request.client.host if request.client else ""
    try:
        local_peer = ip_address(peer).is_loopback
    except ValueError:
        local_peer = False
    host = request.url.hostname
    if not local_peer or host not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(403, "Direct loopback access required")
    # Do not trust forwarded addresses; reverse proxy access is unsupported.
    if any(key in request.headers for key in ("forwarded", "x-forwarded-for", "x-forwarded-host")):
        raise HTTPException(403, "Proxy access is disabled")
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Same-origin access required")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Same-origin access required")


def limit_developer_calls(request: Request) -> None:
    require_developer_access(request)
    now = monotonic()
    with _calls_lock:
        while _calls and _calls[0] <= now - 60:
            _calls.popleft()
        if len(_calls) >= 20:
            raise HTTPException(429, "Developer request limit reached; retry after one minute")
        _calls.append(now)
