"""TOTP 6 số cho AI Console; secret mã hoá Fernet khi lưu DB.

`pyotp.TOTP.verify` không chặn dùng lại mã trong cùng cửa sổ 30 giây, nên
`match_step` trả về time-step đã khớp để store chỉ chấp nhận step mới hơn
step đã dùng lần trước.
"""
from __future__ import annotations

import hmac
import time

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from app.core.exceptions import ConsoleAuthError

_INTERVAL = 30
_DRIFT_STEPS = 1  # chấp nhận lệch đồng hồ ±30 giây


class TotpVault:
    def __init__(self, encryption_key: str, issuer: str) -> None:
        if not encryption_key:
            raise ConsoleAuthError("Chưa cấu hình khoá mã hoá TOTP cho console.", "NOT_CONFIGURED")
        try:
            self._fernet = Fernet(encryption_key.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise ConsoleAuthError("Khoá mã hoá TOTP không hợp lệ.", "NOT_CONFIGURED") from exc
        self._issuer = issuer

    @staticmethod
    def new_secret() -> str:
        return pyotp.random_base32()

    def encrypt(self, secret: str) -> str:
        return self._fernet.encrypt(secret.encode("ascii")).decode("ascii")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("ascii")
        except InvalidToken as exc:
            raise ConsoleAuthError("Không giải mã được secret TOTP.", "NOT_CONFIGURED") from exc

    def provisioning_uri(self, secret: str, email: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=self._issuer)

    @staticmethod
    def match_step(secret: str, code: str, now: float | None = None) -> int | None:
        """Trả time-step khớp với `code`, hoặc None nếu sai."""
        code = (code or "").strip()
        if len(code) != 6 or not (code.isascii() and code.isdigit()):
            return None
        moment = time.time() if now is None else now
        current = int(moment // _INTERVAL)
        totp = pyotp.TOTP(secret)
        for step in range(current - _DRIFT_STEPS, current + _DRIFT_STEPS + 1):
            if hmac.compare_digest(totp.at(step * _INTERVAL), code):
                return step
        return None
