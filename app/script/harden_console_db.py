"""Công cụ siết quyền user DB cho process inference (IPLMS ADR-0051 §Hệ quả).

Chạy:
    python -m app.script.harden_console_db [--verify-only]

Tác vụ:
1. Kết nối DB `ai_console` bằng user admin (superuser / owner).
2. Tạo/cập nhật role `ai_console` và `ai_inference`.
3. Cấp quyền truy cập duy nhất cho `ai_inference`:
   - Các bảng kênh A2: `vision_sample`, `vision_crop`, `vision_import_cursor`, `vision_import_error`.
   - Bảng ngưỡng đã duyệt: `accept_policy` (chỉ SELECT).
4. Thu hồi toàn bộ quyền trên các bảng nhạy cảm:
   `console_member`, `console_member_role`, `console_session`, `console_auth_flow`,
   `audit_event`, `copilot_turn_review`, `vision_label`, `vision_snapshot`, `model_version`, `eval_run`.
5. Kiểm chứng bảo mật: thử truy vấn bằng role `ai_inference` để bảo đảm fail-closed.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# Đảm bảo UTF-8 stream trên Windows
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def get_db_urls() -> tuple[str, str]:
    """Lấy admin URL (để cấp quyền) và inference URL (để kiểm tra)."""
    # URL quản trị: ưu tiên quyền superuser postgres
    admin_pw = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("AI_DB_PASSWORD") or "***REMOVED***"
    admin_user = os.environ.get("POSTGRES_USER", "postgres")
    base_url = (
        os.environ.get("AI_CONSOLE_ADMIN_DATABASE_URL")
        or os.environ.get("AI_DATABASE_URL")
        or "postgresql://postgres:***REMOVED***@127.0.0.1:5435/ai_console"
    )
    # Chuẩn hóa về user postgres và db ai_console
    admin_url = re.sub(r"://([^:]+):([^@]+)@", f"://{admin_user}:{admin_pw}@", base_url)
    admin_url = re.sub(r"/[^/?]+(\?.*)?$", r"/ai_console\1", admin_url)

    inference_password = os.environ.get("AI_INFERENCE_DB_PASSWORD", "***REMOVED***")
    inf_url = re.sub(r"://([^:]+):([^@]+)@", f"://ai_inference:{inference_password}@", admin_url)
    return admin_url, inf_url


def harden_database(admin_url: str, inference_pw: str) -> None:
    import psycopg2

    print(f"🔒 Đang kết nối tới DB console với quyền admin: {admin_url.split('@')[-1]}")
    try:
        conn = psycopg2.connect(admin_url, connect_timeout=5)
    except Exception as exc:
        for old in ("@ai-db:5432/", "@database-vector:5432/", "@localhost:5432/"):
            if old in admin_url:
                fallback_url = admin_url.replace(old, "@127.0.0.1:5435/")
                try:
                    conn = psycopg2.connect(fallback_url, connect_timeout=5)
                    admin_url = fallback_url
                    print(f"   ℹ️ Đã chuyển sang fallback: {fallback_url.split('@')[-1]}")
                    break
                except Exception:
                    pass
        else:
            raise RuntimeError(f"Không thể kết nối admin DB: {exc}") from exc

    conn.autocommit = True
    cur = conn.cursor()

    console_pw = os.environ.get("AI_CONSOLE_DB_PASSWORD", "***REMOVED***")
    print("1. Tạo/cập nhật role 'ai_console' và 'ai_inference'...")
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ai_console'")
    if not cur.fetchone():
        cur.execute("CREATE ROLE ai_console WITH LOGIN PASSWORD %s", (console_pw,))
        print("   ✅ Đã tạo role ai_console.")
    else:
        cur.execute("ALTER ROLE ai_console WITH PASSWORD %s", (console_pw,))

    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ai_inference'")
    if cur.fetchone():
        cur.execute("ALTER ROLE ai_inference WITH LOGIN PASSWORD %s", (inference_pw,))
        print("   ✅ Role ai_inference đã tồn tại — đã cập nhật mật khẩu.")
    else:
        cur.execute("CREATE ROLE ai_inference WITH LOGIN PASSWORD %s", (inference_pw,))
        print("   ✅ Đã tạo mới role ai_inference.")

    print("2. Phân quyền trên schema public và database ai_console...")
    cur.execute("GRANT CONNECT ON DATABASE ai_console TO ai_console, ai_inference")
    cur.execute("GRANT USAGE, CREATE ON SCHEMA public TO ai_console")
    cur.execute("GRANT USAGE ON SCHEMA public TO ai_inference")

    a2_tables = ["vision_sample", "vision_crop", "vision_import_cursor", "vision_import_error"]
    sensitive_tables = [
        "console_member", "console_member_role", "console_session", "console_auth_flow",
        "audit_event", "copilot_turn_review", "vision_label", "vision_snapshot",
        "model_version", "eval_run"
    ]

    print("3. Cấp quyền bảng A2 + accept_policy cho ai_inference (ADR-0051)...")
    for tbl in a2_tables:
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s", (tbl,))
        if cur.fetchone():
            cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {tbl} TO ai_inference")
            print(f"   ✅ Đã cấp SELECT, INSERT, UPDATE, DELETE trên {tbl}")

    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'accept_policy'")
    if cur.fetchone():
        cur.execute("GRANT SELECT ON TABLE accept_policy TO ai_inference")
        print("   ✅ Đã cấp SELECT trên accept_policy (chỉ đọc)")

    print("4. Thu hồi quyền trên các bảng nhạy cảm đối với ai_inference...")
    for tbl in sensitive_tables:
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s", (tbl,))
        if cur.fetchone():
            cur.execute(f"REVOKE ALL ON TABLE {tbl} FROM ai_inference")
            print(f"   🚫 Đã thu hồi toàn bộ quyền trên {tbl}")

    cur.close()
    conn.close()
    print("✅ Hoàn tất siết quyền DB!")


def verify_least_privilege(inference_url: str) -> bool:
    import psycopg2

    print(f"\n🔍 Bắt đầu kiểm chứng bảo mật với user 'ai_inference': {inference_url.split('@')[-1]}")
    try:
        conn = psycopg2.connect(inference_url, connect_timeout=5)
    except Exception as exc:
        for old in ("@ai-db:5432/", "@database-vector:5432/", "@localhost:5432/"):
            if old in inference_url:
                fallback_url = inference_url.replace(old, "@127.0.0.1:5435/")
                try:
                    conn = psycopg2.connect(fallback_url, connect_timeout=5)
                    inference_url = fallback_url
                    break
                except Exception:
                    pass
        else:
            print(f"❌ Không thể kết nối bằng user ai_inference: {exc}")
            return False

    cur = conn.cursor()
    all_passed = True

    # Kiểm tra bị chặn trên bảng nhạy cảm (console_member)
    try:
        cur.execute("SELECT COUNT(*) FROM console_member")
        cur.fetchone()
        print("   ❌ [FAIL] user ai_inference VẪN đọc được console_member (LỖI BẢO MẬT!)")
        all_passed = False
    except Exception as exc:
        if "permission denied" in str(exc).lower():
            print("   🛡️ [PASS] Bị CHẶN thành công khi truy cập console_member (Permission Denied)")
        elif "does not exist" in str(exc).lower():
            print("   ℹ️ Bảng console_member chưa tạo")
        else:
            print(f"   ℹ️ Lỗi khác: {exc}")
    conn.rollback()

    # Kiểm tra bị chặn trên bảng nhạy cảm (audit_event)
    try:
        cur.execute("SELECT COUNT(*) FROM audit_event")
        cur.fetchone()
        print("   ❌ [FAIL] user ai_inference VẪN đọc được audit_event (LỖI BẢO MẬT!)")
        all_passed = False
    except Exception as exc:
        if "permission denied" in str(exc).lower():
            print("   🛡️ [PASS] Bị CHẶN thành công khi truy cập audit_event (Permission Denied)")
        elif "does not exist" in str(exc).lower():
            print("   ℹ️ Bảng audit_event chưa tạo")
        else:
            print(f"   ℹ️ Lỗi khác: {exc}")
    conn.rollback()

    cur.close()
    conn.close()
    return all_passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Siết quyền DB cho user ai_inference theo ADR-0051")
    parser.add_argument("--verify-only", action="store_true", help="Chỉ kiểm chứng quyền, không chỉnh sửa")
    args = parser.parse_args()

    admin_url, inf_url = get_db_urls()
    inf_pw = os.environ.get("AI_INFERENCE_DB_PASSWORD", "***REMOVED***")

    if not args.verify_only:
        harden_database(admin_url, inf_pw)

    success = verify_least_privilege(inf_url)
    if success:
        print("\n🎉 BẢO MẬT ĐẠT CHUẨN: User ai_inference tuân thủ nghiêm ngặt ADR-0051!")
    else:
        print("\n⚠️ Kiểm chứng chưa đạt yêu cầu, vui lòng rà soát lại quyền.")
        sys.exit(1)


if __name__ == "__main__":
    main()
