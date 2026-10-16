"""Google OIDC — Authorization Code + PKCE, kiểm id_token bằng `google-auth`.

`google-auth` cần một transport để tải khoá công khai của Google. Transport có
sẵn của thư viện đòi `requests`; repo không dùng `requests`, nên dùng một
transport nhỏ trên `urllib` của thư viện chuẩn.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from google.auth import exceptions as google_exceptions
from google.auth import transport
from google.oauth2 import id_token as google_id_token

from app.core.exceptions import ConsoleAuthError

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str


def new_pkce_pair() -> tuple[str, str]:
    """Trả (code_verifier, code_challenge S256)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class _UrllibResponse(transport.Response):
    def __init__(self, status: int, headers: dict, data: bytes) -> None:
        self._status, self._headers, self._data = status, headers, data

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> dict:
        return self._headers

    @property
    def data(self) -> bytes:
        return self._data


class _UrllibRequest(transport.Request):
    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):
        request = UrlRequest(url, data=body, method=method, headers=headers or {})
        try:
            with urlopen(request, timeout=timeout or _TIMEOUT_SECONDS) as response:
                return _UrllibResponse(response.status, dict(response.headers), response.read())
        except HTTPError as exc:
            return _UrllibResponse(exc.code, dict(exc.headers or {}), exc.read())
        except URLError as exc:
            raise google_exceptions.TransportError(str(exc.reason)) from exc


class GoogleOidcClient:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def _require_configured(self) -> None:
        if not (self._client_id and self._client_secret and self._redirect_uri):
            raise ConsoleAuthError("Chưa cấu hình đăng nhập Google cho console.", "NOT_CONFIGURED")

    def authorize_url(self, state: str, nonce: str, code_challenge: str) -> str:
        self._require_configured()
        return AUTHORIZE_URL + "?" + urlencode({
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        })

    def _exchange_code(self, code: str, code_verifier: str) -> str:
        body = urlencode({
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }).encode("ascii")
        request = UrlRequest(
            TOKEN_URL, data=body, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read())
        except (HTTPError, URLError, ValueError) as exc:
            # Không đưa body/URL vào lỗi: có thể chứa code hoặc secret.
            raise ConsoleAuthError("Google từ chối đổi mã đăng nhập.") from exc
        token = payload.get("id_token")
        if not isinstance(token, str) or not token:
            raise ConsoleAuthError("Google không trả id_token.")
        return token

    def _verify(self, token: str, nonce: str) -> GoogleIdentity:
        try:
            claims = google_id_token.verify_oauth2_token(token, _UrllibRequest(), self._client_id)
        except (ValueError, google_exceptions.GoogleAuthError) as exc:
            raise ConsoleAuthError("id_token Google không hợp lệ.") from exc
        if not secrets.compare_digest(str(claims.get("nonce", "")).encode("utf-8"), nonce.encode("utf-8")):
            raise ConsoleAuthError("id_token Google sai nonce.")
        if claims.get("email_verified") is not True or not claims.get("email") or not claims.get("sub"):
            raise ConsoleAuthError("Email Google chưa được xác minh.")
        return GoogleIdentity(sub=str(claims["sub"]), email=str(claims["email"]))

    def login(self, code: str, code_verifier: str, nonce: str) -> GoogleIdentity:
        self._require_configured()
        return self._verify(self._exchange_code(code, code_verifier), nonce)
