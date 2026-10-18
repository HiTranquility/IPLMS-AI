"""Tạo tài khoản admin khẩn cấp của AI Console — chạy tay trên AI host (ADR-0048 §4).

    python -m app.script.console_admin --email admin@example.com --display-name "Admin"

Mật khẩu nhập qua getpass (không hiện, không vào lịch sử shell). URI TOTP in ra
ĐÚNG MỘT LẦN để thêm vào ứng dụng xác thực; mất thì phải tạo lại tài khoản.
Tài khoản này dùng khi Google/mạng không dùng được; mọi lần đăng nhập vẫn qua TOTP.
"""
import argparse
import asyncio
import getpass
import sys

from app.config import get_config
from app.core.console.engines import access_policy
from app.infra.database.console_store import console_store
from app.infra.identity.password import hash_password
from app.infra.identity.totp import TotpVault

_MIN_PASSWORD = 12


def main() -> int:
    parser = argparse.ArgumentParser(description="Tạo admin khẩn cấp cho AI Console")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Mật khẩu (≥ 12 ký tự): ")
    if len(password) < _MIN_PASSWORD or password != getpass.getpass("Nhập lại: "):
        print("Mật khẩu quá ngắn hoặc hai lần nhập không khớp.", file=sys.stderr)
        return 1

    cfg = get_config().console
    vault = TotpVault(cfg.totp_encryption_key, cfg.totp_issuer)
    secret = vault.new_secret()
    asyncio.run(console_store.create_emergency_admin(
        args.email.strip(), args.display_name.strip(), hash_password(password),
        vault.encrypt(secret), access_policy.CONSOLE_ADMIN,
    ))
    print("Đã tạo admin khẩn cấp. Thêm URI sau vào ứng dụng xác thực (chỉ hiện một lần):")
    print(vault.provisioning_uri(secret, args.email.strip()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
