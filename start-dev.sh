#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "\033[0;36m====================================================\033[0m"
echo -e "\033[0;36m   IPLMS AI Studio — Khởi Động Hệ Thống Dev (GPU)   \033[0m"
echo -e "\033[0;36m====================================================\033[0m"

# 1. Start pgvector db in docker
echo -e "\n\033[1;33m[1/3] Kiểm tra cơ sở dữ liệu Vector (PostgreSQL pgvector)...\033[0m"
docker compose --env-file .env.dev stop ai gateway 2>/dev/null || true
docker compose --env-file .env.dev up -d ai-db 2>/dev/null || true
echo -e "\033[0;32m  ✓ pgvector database đang chạy tại localhost:5435\033[0m"

# 2. Check Python venv and GPU
echo -e "\n\033[1;33m[2/3] Kiểm tra môi trường Python & Card đồ họa...\033[0m"
if [ ! -d ".venv" ]; then
    echo -e "\033[0;31m  ✖ Chưa tìm thấy .venv! Vui lòng chạy bash setup-dev.sh trước.\033[0m"
    exit 1
fi

source .venv/bin/activate
python3 -c "
import torch
cuda = torch.cuda.is_available()
name = torch.cuda.get_device_name(0) if cuda else 'CPU'
print(f'  ✓ PyTorch {torch.__version__} | CUDA: {cuda} | Device: {name}')
"

echo -e "\n\033[0;32m[3/3] Đang khởi chạy AI Studio tại http://localhost:8000/ ...\033[0m"
echo -e "\033[0;36m  - Web Dashboard UI:  http://localhost:8000/\033[0m"
echo -e "\033[0;36m  - API Swagger Docs:  http://localhost:8000/docs\033[0m"
echo -e "\033[0;36m  - Local LLM Engine:  llama-server (Qwen3.5-4B CUDA) tại port 8005\033[0m"
echo -e "  - Nhấn Ctrl+C để dừng server.\n"

uvicorn app.main:app --host 0.0.0.0 --port 8000
