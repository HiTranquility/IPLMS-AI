#!/bin/sh
# Siết quyền user DB cho process inference (IPLMS ADR-0051 §Hệ quả).
# Process inference (gRPC server) chỉ được phép:
# 1. Ghi/đọc bảng kênh A2 (vision_sample, vision_crop, vision_import_cursor, vision_import_error)
# 2. Đọc bảng accept_policy (DatasetService.GetAcceptPolicy)
# KHÔNG được cấp quyền trên console_member, console_session, audit_event, copilot_turn_review.
set -eu

if [ -z "${AI_CONSOLE_DB_PASSWORD:-}" ]; then
  echo "AI_CONSOLE_DB_PASSWORD trống — bỏ qua phân quyền DB ai_console."
  exit 0
fi

INFERENCE_PW="${AI_INFERENCE_DB_PASSWORD:-$AI_CONSOLE_DB_PASSWORD}"

psql -v ON_ERROR_STOP=1 -v pw="$INFERENCE_PW" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ai_inference') THEN
    CREATE ROLE ai_inference LOGIN PASSWORD :'pw';
  ELSE
    ALTER ROLE ai_inference WITH PASSWORD :'pw';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE ai_console TO ai_inference;
SQL

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "ai_console" <<'SQL'
GRANT USAGE ON SCHEMA public TO ai_inference;

-- Cấp quyền bảng kênh A2 và accept_policy nếu bảng đã tồn tại
DO $$
DECLARE
  tbl text;
  a2_tables text[] := ARRAY['vision_sample', 'vision_crop', 'vision_import_cursor', 'vision_import_error'];
BEGIN
  FOREACH tbl IN ARRAY a2_tables LOOP
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
      EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO ai_inference', tbl);
    END IF;
  END LOOP;

  IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'accept_policy') THEN
    EXECUTE 'GRANT SELECT ON TABLE accept_policy TO ai_inference';
  END IF;
END
$$;

-- Thu hồi toàn bộ quyền trên bảng nhạy cảm (ADR-0048 / ADR-0051)
DO $$
DECLARE
  tbl text;
  sensitive_tables text[] := ARRAY['console_member', 'console_member_role', 'console_session', 'console_auth_flow', 'audit_event', 'copilot_turn_review'];
BEGIN
  FOREACH tbl IN ARRAY sensitive_tables LOOP
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
      EXECUTE format('REVOKE ALL ON TABLE %I FROM ai_inference', tbl);
    END IF;
  END LOOP;
END
$$;
SQL
