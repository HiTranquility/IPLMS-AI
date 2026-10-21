#!/usr/bin/env bash
# ============================================================================
# setup-dev.sh — Dựng môi trường AI dev sau khi clone repo
#
# Chạy một lần trên máy mới:
#   cd <repo-root> && bash setup-dev.sh
#
# Script này KHÔNG thay đổi code hay cấu hình nào — chỉ chuẩn bị để chạy được.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Màu terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
fail()  { echo -e "${RED}✖${NC} $*"; }
sep()   { echo -e "${CYAN}─────────────────────────────────────────────${NC}"; }

# ── 1. Python venv ───────────────────────────────────────────────────────────
sep
info "Bước 1/7: Tạo .venv & cài dependencies"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Đã tạo .venv"
else
    ok ".venv đã tồn tại, bỏ qua"
fi

# Activate venv
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
ok "Đã activate venv"

pip install --upgrade pip -q

# CPU/default requirements only; CUDA setup is a separate explicit choice.
pip install -r requirements.txt -q
ok "Đã cài đặt dependencies (requirements.txt)"

# ── 2. gRPC stubs ────────────────────────────────────────────────────────────
sep
info "Bước 2/7: Sinh gRPC stubs từ proto/"

if [ -d "app/api/grpc/generated" ] && [ "$(ls -A app/api/grpc/generated 2>/dev/null)" ]; then
    ok "gRPC stubs đã tồn tại"
else
    python app/script/compile_proto.py
    ok "Đã sinh gRPC stubs"
fi

# ── 3. YOLO weights ──────────────────────────────────────────────────────────
sep
info "Bước 3/7: Kiểm tra YOLO weights (best.pt)"

YOLO_PATH="model/artifacts/bootstrap/anpr/best.pt"
if [ -f "$YOLO_PATH" ]; then
    YOLO_SIZE=$(stat -c%s "$YOLO_PATH" 2>/dev/null || stat -f%z "$YOLO_PATH" 2>/dev/null)
    ok "best.pt tồn tại ($(( YOLO_SIZE / 1024 / 1024 )) MB)"
else
    warn "THIẾU best.pt tại $YOLO_PATH"
    warn "ANPR sẽ chạy fallback không có detector (chỉ OCR toàn ảnh, kém chính xác)"
    warn "Nếu có file best.pt, copy vào: $YOLO_PATH"
fi

# ── 4. EasyOCR models ────────────────────────────────────────────────────────
sep
info "Bước 4/7: Tải trước EasyOCR models (~113MB)"

# Ưu tiên dùng thư mục local trong project để dễ chuyển máy
EASYOCR_DIR="${EASYOCR_MODULE_PATH:-$SCRIPT_DIR/var/easyocr-cache}"
export EASYOCR_MODULE_PATH="$EASYOCR_DIR"

if [ -d "$EASYOCR_DIR/model" ] && [ "$(ls -A "$EASYOCR_DIR/model" 2>/dev/null)" ]; then
    ok "EasyOCR models đã có tại $EASYOCR_DIR"
else
    info "Đang tải EasyOCR models (cần Internet, ~113MB)..."
    python -c "
import os
os.environ['EASYOCR_MODULE_PATH'] = '$EASYOCR_DIR'
import easyocr
reader = easyocr.Reader(['en','vi'], gpu=False)
print('EasyOCR models đã tải xong.')
" && ok "Đã tải EasyOCR models vào $EASYOCR_DIR" \
  || warn "Không tải được EasyOCR models (cần Internet) — sẽ thử tải lúc chạy request đầu"
fi

# ── 5. Local LLM & llama-server ──────────────────────────────────────────────
sep
info "Bước 5/7: Kiểm tra Local LLM (Qwen3.5-4B-GGUF ~2.55 GB) & llama-server"

# 5.1. Model GGUF
MODEL_DIR="model/checkpoint/llm"
MODEL_PATH="$MODEL_DIR/Qwen3.5-4B-Q4_K_M.gguf"
mkdir -p "$MODEL_DIR"

FILE_SIZE=0
if [ -f "$MODEL_PATH" ]; then
    FILE_SIZE=$(stat -c%s "$MODEL_PATH" 2>/dev/null || stat -f%z "$MODEL_PATH" 2>/dev/null || echo 0)
fi

if [ "$FILE_SIZE" -gt 2000000000 ]; then
    ok "Qwen3.5-4B-Q4_K_M.gguf đã tồn tại ($(( FILE_SIZE / 1024 / 1024 / 1024 )) GB)"
else
    info "Đang tải mô hình Qwen3.5-4B-Q4_K_M.gguf (~2.55 GB) từ HuggingFace..."
    info "URL: https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
    MODEL_URL="https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
    if curl -L -C - --progress-bar -o "$MODEL_PATH" "$MODEL_URL"; then
        ok "Tải xong Qwen3.5-4B-Q4_K_M.gguf"
    else
        warn "Không thể tự động tải Qwen3.5-4B-Q4_K_M.gguf — vui lòng tải thủ công và lưu vào $MODEL_PATH"
    fi
fi

# 5.2. Binary llama-server
LLAMA_DIR="var/bin/llama"
mkdir -p "$LLAMA_DIR"

if [ -f "$LLAMA_DIR/llama-server" ] || [ -f "$LLAMA_DIR/llama-server.exe" ]; then
    ok "llama-server đã có tại $LLAMA_DIR"
else
    info "Đang tải prebuilt llama.cpp binaries (b11681)..."
    OS_NAME=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH_NAME=$(uname -m)

    if [ "$OS_NAME" = "darwin" ]; then
        if [ "$ARCH_NAME" = "arm64" ]; then
            TAR_NAME="llama-b11681-bin-macos-arm64.tar.gz"
        else
            TAR_NAME="llama-b11681-bin-macos-x64.tar.gz"
        fi
    else
        # Linux
        if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
            TAR_NAME="llama-b11681-bin-ubuntu-cuda-12.8-x64.tar.gz"
        else
            TAR_NAME="llama-b11681-bin-ubuntu-x64.tar.gz"
        fi
    fi

    TAR_URL="https://github.com/ggml-org/llama.cpp/releases/download/b11681/$TAR_NAME"
    TMP_TAR="/tmp/$TAR_NAME"

    if curl -L -C - --progress-bar -o "$TMP_TAR" "$TAR_URL"; then
        tar -xzf "$TMP_TAR" -C "$LLAMA_DIR" 2>/dev/null || unzip -o -q "$TMP_TAR" -d "$LLAMA_DIR" 2>/dev/null || true
        chmod +x "$LLAMA_DIR/llama-server"* 2>/dev/null || true
        rm -f "$TMP_TAR"
        ok "Đã cài đặt llama-server vào $LLAMA_DIR"
    else
        warn "Không thể tự động tải llama-server — vui lòng tải prebuilt binary và đặt vào $LLAMA_DIR"
    fi
fi

# ── 6. .env.dev ──────────────────────────────────────────────────────────────
sep
info "Bước 6/7: Kiểm tra .env.dev"

if [ -f ".env.dev" ]; then
    ok ".env.dev đã tồn tại"
else
    cp .env.example .env.dev
    ok "Đã copy .env.example → .env.dev (sửa theo máy nếu cần)"
fi

# ── 7. Smoke test ────────────────────────────────────────────────────────────
sep
info "Bước 7/7: Smoke test"

python -c "
from app.config import get_config
cfg = get_config()
print(f'  YOLO path:    {cfg.vision.yolo_model_path}')
print(f'  OCR langs:    {cfg.vision.ocr_language_list}')
print(f'  Device:       {cfg.vision.device}')
print(f'  gRPC port:    {cfg.server.grpc_port}')
print(f'  LLM Provider: {cfg.llm.llm_provider}')
print(f'  LLM Model:    {cfg.llm.local_llm_model_path}')
" && ok "Config load thành công" \
  || fail "Config load thất bại — kiểm tra lại .env.dev"

# ── Tổng kết ─────────────────────────────────────────────────────────────────
sep
echo ""
ok "Setup hoàn tất! Chạy service:"
echo ""
echo "  # Chạy nhanh toàn bộ hệ thống (Recommended)"
echo "  bash start-dev.sh"
echo ""
echo "  # Hoặc chạy thủ công REST (FastAPI)"
echo "  source .venv/bin/activate"
echo "  EASYOCR_MODULE_PATH=$EASYOCR_DIR uvicorn app.main:app --reload --port 8000"
echo ""
echo "  # gRPC"
echo "  EASYOCR_MODULE_PATH=$EASYOCR_DIR python -m app.grpc_server"
echo ""
echo "  # Hoặc cả hai (Docker)"
echo "  docker compose --env-file .env.dev up --build"
echo ""
