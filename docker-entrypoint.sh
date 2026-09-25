#!/bin/bash
# Chạy CẢ HAI transport trong một container: gRPC (đường nóng backend gọi vào)
# và FastAPI REST (upload thủ công + endpoint /health cho probe của k8s).
#
# `wait -n` trả về ngay khi TIẾN TRÌNH ĐẦU TIÊN thoát, dù là cái nào. Nhờ vậy
# gRPC chết thì container cũng chết theo và k8s restart — thay vì để probe HTTP
# vẫn xanh trong khi cổng 50051 đã câm (lỗi im lặng khó lần nhất).
set -euo pipefail

# Nếu truyền tham số (ví dụ: pytest, bash, python...), thực thi lệnh đó thay vì khởi động server
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# The dev Compose file bind-mounts /app/app, which also overlays the stubs that
# were generated inside the image. Regenerate them with this image's pinned
# grpcio-tools/protobuf pair before importing either server.
if [ "${AI_COMPILE_PROTO_ON_START:-false}" = "true" ] || [ "${AI_COMPILE_PROTO_ON_START:-0}" = "1" ]; then
  echo "▶ Đồng bộ gRPC stubs bằng toolchain trong container..."
  python app/script/compile_proto.py
fi

term() {
  echo "▶ Nhận tín hiệu dừng, đóng cả hai tiến trình..."
  kill -TERM "${GRPC_PID:-}" "${REST_PID:-}" 2>/dev/null || true
  wait || true
  exit 0
}
trap term SIGTERM SIGINT

echo "▶ Khởi động gRPC server (cổng ${AI_GRPC_PORT:-50051})..."
python -m app.grpc_server &
GRPC_PID=$!

echo "▶ Khởi động FastAPI REST (cổng ${AI_FASTAPI_PORT:-8000})..."
if [ "${AI_RELOAD:-false}" = "true" ] || [ "${AI_RELOAD:-0}" = "1" ]; then
  uvicorn app.main:app --host 0.0.0.0 --port "${AI_FASTAPI_PORT:-8000}" --reload &
else
  uvicorn app.main:app --host 0.0.0.0 --port "${AI_FASTAPI_PORT:-8000}" &
fi
REST_PID=$!

# Tiến trình nào chết trước cũng kéo container xuống.
wait -n "$GRPC_PID" "$REST_PID"
EXIT_CODE=$?
echo "✖ Một tiến trình đã thoát (mã $EXIT_CODE) — dừng container để k8s khởi động lại."
kill -TERM "$GRPC_PID" "$REST_PID" 2>/dev/null || true
exit "$EXIT_CODE"
