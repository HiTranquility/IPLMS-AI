<#
.SYNOPSIS
    Dựng môi trường AI dev sau khi clone repo (Windows PowerShell).

.DESCRIPTION
    Chạy một lần trên máy mới:
        cd ai
        .\setup-dev.ps1

    Script này KHÔNG thay đổi code hay cấu hình — chỉ chuẩn bị để chạy được.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Write-Info  { param($msg) Write-Host "▶ $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "✖ $msg" -ForegroundColor Red }
function Write-Sep   { Write-Host "─────────────────────────────────────────────" -ForegroundColor Cyan }

# ── 1. Python venv ───────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 1/6: Tạo .venv & cài dependencies"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Ok "Đã tạo .venv"
} else {
    Write-Ok ".venv đã tồn tại, bỏ qua"
}

# Activate venv
& .\.venv\Scripts\Activate.ps1
Write-Ok "Đã activate venv"

pip install --upgrade pip -q 2>$null
pip install -r requirements.txt -q 2>$null
Write-Ok "Đã cài đặt dependencies (requirements.txt)"

# ── 2. gRPC stubs ────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 2/6: Sinh gRPC stubs từ proto/"

$StubDir = "app\api\grpc\generated"
if ((Test-Path $StubDir) -and (Get-ChildItem $StubDir -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
    Write-Ok "gRPC stubs đã tồn tại"
} else {
    python app\script\compile_proto.py
    Write-Ok "Đã sinh gRPC stubs"
}

# ── 3. YOLO weights ──────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 3/6: Kiểm tra YOLO weights (best.pt)"

$YoloPath = "model\artifacts\bootstrap\anpr\best.pt"
if (Test-Path $YoloPath) {
    $YoloSize = [math]::Round((Get-Item $YoloPath).Length / 1MB, 1)
    Write-Ok "best.pt tồn tại ($YoloSize MB)"
} else {
    Write-Warn "THIẾU best.pt tại $YoloPath"
    Write-Warn "ANPR sẽ chạy fallback không có detector (chỉ OCR toàn ảnh, kém chính xác)"
    Write-Warn "Nếu có file best.pt, copy vào: $YoloPath"
}

# ── 4. EasyOCR models ────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 4/6: Tải trước EasyOCR models (~113MB)"

# Gom model EasyOCR vào project thay vì rải ở ~/.EasyOCR/
$EasyOcrDir = if ($env:EASYOCR_MODULE_PATH) { $env:EASYOCR_MODULE_PATH } else { "$ScriptDir\var\easyocr-cache" }
$env:EASYOCR_MODULE_PATH = $EasyOcrDir

$EasyOcrModelDir = Join-Path $EasyOcrDir "model"
if ((Test-Path $EasyOcrModelDir) -and (Get-ChildItem $EasyOcrModelDir -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
    Write-Ok "EasyOCR models đã có tại $EasyOcrDir"
} else {
    Write-Info "Đang tải EasyOCR models (cần Internet, ~113MB)..."
    try {
        python -c @"
import os
os.environ['EASYOCR_MODULE_PATH'] = r'$EasyOcrDir'
import easyocr
reader = easyocr.Reader(['en','vi'], gpu=False)
print('EasyOCR models đã tải xong.')
"@
        Write-Ok "Đã tải EasyOCR models vào $EasyOcrDir"
    } catch {
        Write-Warn "Không tải được EasyOCR models (cần Internet) — sẽ thử tải lúc chạy request đầu"
    }
}

# ── 5. .env ──────────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 5/6: Kiểm tra .env"

if (Test-Path ".env") {
    Write-Ok ".env đã tồn tại"
} else {
    Copy-Item ".env.example" ".env"
    Write-Ok "Đã copy .env.example → .env (sửa theo máy nếu cần)"
}

# ── 6. Smoke test ────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 6/6: Smoke test"

try {
    python -c @"
from app.config import get_config
cfg = get_config()
print(f'  YOLO path:    {cfg.vision.yolo_model_path}')
print(f'  OCR langs:    {cfg.vision.ocr_language_list}')
print(f'  Device:       {cfg.vision.device}')
print(f'  gRPC port:    {cfg.server.grpc_port}')
"@
    Write-Ok "Config load thành công"
} catch {
    Write-Fail "Config load thất bại — kiểm tra lại .env"
}

# ── Tổng kết ─────────────────────────────────────────────────────────────────
Write-Sep
Write-Host ""
Write-Ok "Setup hoàn tất! Chạy service:"
Write-Host ""
Write-Host "  # REST (FastAPI)" -ForegroundColor DarkGray
Write-Host '  cd ai; .\.venv\Scripts\Activate.ps1'
Write-Host "  `$env:EASYOCR_MODULE_PATH='$EasyOcrDir'"
Write-Host '  uvicorn app.main:app --reload --port 8000'
Write-Host ""
Write-Host "  # gRPC" -ForegroundColor DarkGray
Write-Host "  `$env:EASYOCR_MODULE_PATH='$EasyOcrDir'"
Write-Host '  python -m app.grpc_server'
Write-Host ""
Write-Host "  # Hoặc cả hai (Docker)" -ForegroundColor DarkGray
Write-Host '  docker compose up --build'
Write-Host ""
