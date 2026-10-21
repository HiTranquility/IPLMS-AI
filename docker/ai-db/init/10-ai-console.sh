#!/bin/sh
# Tạo database + user RIÊNG cho AI Console (ADR-0048 §3) — không dùng chung tài
# khoản với knowledge_*. Postgres chỉ chạy thư mục init khi volume ai-db còn trống;
# volume đã có dữ liệu thì chạy tay theo ai/DESIGN.md §AI Console.
set -eu

if [ -z "${AI_CONSOLE_DB_PASSWORD:-}" ]; then
  echo "AI_CONSOLE_DB_PASSWORD trống — bỏ qua tạo DB ai_console (console không bật)."
  exit 0
fi

psql -v ON_ERROR_STOP=1 -v pw="$AI_CONSOLE_DB_PASSWORD" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE ai_console LOGIN PASSWORD :'pw';
CREATE DATABASE ai_console OWNER ai_console;
SQL
