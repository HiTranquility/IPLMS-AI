<#
.SYNOPSIS
    Dựng môi trường AI dev sau khi clone repo (Windows PowerShell).

.DESCRIPTION
    Chạy một lần trên máy mới:
        cd ai
        .\setup-dev.ps1

    Script này KHÔNG thay đổi code hay cấu hình — chỉ chuẩn bị để chạy được.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
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

$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$VenvPip    = Join-Path $ScriptDir ".venv\Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Info "Đang tạo .venv..."
    python -m venv .venv
    Write-Ok "Đã tạo .venv"
} else {
    Write-Ok ".venv đã tồn tại, bỏ qua"
}

# Activate venv trong session nếu có thể
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    try {
        & .\.venv\Scripts\Activate.ps1
        Write-Ok "Đã activate venv"
    } catch {
        Write-Warn "Bỏ qua dot-source Activate.ps1, dùng trực tiếp binary trong .venv"
    }
}

& $VenvPip install --upgrade pip -q

# Kiểm tra xem máy có GPU NVIDIA không
$hasNvidiaGpu = $false
try {
    $smi = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue
    if ($smi) {
        $gpuOut = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
        if ($LASTEXITCODE -eq 0 -and $gpuOut) {
            $hasNvidiaGpu = $true
            Write-Ok "Phát hiện GPU NVIDIA: $gpuOut"
        }
    }
} catch { }

if ($hasNvidiaGpu) {
    Write-Info "Đang cài đặt PyTorch với hỗ trợ CUDA 12.4..."
    & $VenvPip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 --index-url https://download.pytorch.org/whl/cu124 --default-timeout=1000 --retries=10
}

& $VenvPip install -r requirements.txt --default-timeout=1000 --retries=10
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Cài đặt dependencies thất bại!"
    exit $LASTEXITCODE
}
Write-Ok "Đã cài đặt dependencies (requirements.txt)"

# ── 2. gRPC stubs ────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 2/6: Sinh gRPC stubs từ proto/"

$StubDir = "app\api\grpc\generated"
if ((Test-Path $StubDir) -and (Get-ChildItem $StubDir -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
    Write-Ok "gRPC stubs đã tồn tại"
} else {
    & $VenvPython app\script\compile_proto.py
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
        & $VenvPython -c @"
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

# ── 5. .env.dev ──────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 5/6: Kiểm tra .env.dev"

if (Test-Path ".env.dev") {
    Write-Ok ".env.dev đã tồn tại"
} else {
    Copy-Item ".env.example" ".env.dev"
    Write-Ok "Đã copy .env.example → .env.dev (sửa theo máy nếu cần)"
}

# ── 6. Smoke test ────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 6/6: Smoke test"

try {
    & $VenvPython -c @"
from app.config import get_config
cfg = get_config()
print(f'  YOLO path:    {cfg.vision.yolo_model_path}')
print(f'  OCR langs:    {cfg.vision.ocr_language_list}')
print(f'  Device:       {cfg.vision.device}')
print(f'  gRPC port:    {cfg.server.grpc_port}')
"@
    Write-Ok "Config load thành công"
} catch {
    Write-Fail "Config load thất bại — kiểm tra lại .env.dev"
}

# ── Tổng kết ─────────────────────────────────────────────────────────────────
Write-Sep
Write-Host ""
Write-Ok "Setup hoàn tất! Chạy service:"
Write-Host ""
Write-Host "  # Chạy nhanh toàn bộ hệ thống (Recommended)" -ForegroundColor Green
Write-Host '  .\start-dev.ps1'
Write-Host ""
Write-Host "  # Hoặc chạy thủ công REST (FastAPI)" -ForegroundColor DarkGray
Write-Host '  .\.venv\Scripts\Activate.ps1'
Write-Host "  `$env:EASYOCR_MODULE_PATH='$EasyOcrDir'"
Write-Host '  uvicorn app.main:app --reload --port 8000'
Write-Host ""
Write-Host "  # gRPC" -ForegroundColor DarkGray
Write-Host "  `$env:EASYOCR_MODULE_PATH='$EasyOcrDir'"
Write-Host '  python -m app.grpc_server'
Write-Host ""
Write-Host "  # Hoặc cả hai (Docker)" -ForegroundColor DarkGray
Write-Host '  docker compose --env-file .env.dev up --build'
Write-Host ""