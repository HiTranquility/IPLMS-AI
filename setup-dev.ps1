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
Write-Info "Bước 1/7: Tạo .venv & cài dependencies"

$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$VenvPip    = Join-Path $ScriptDir ".venv\Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Info "Đang tạo .venv..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
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
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# CPU/default requirements only. CUDA is a separate, explicitly chosen setup.
& $VenvPip install -r requirements.txt --default-timeout=1000 --retries=10
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Cài đặt dependencies thất bại!"
    exit $LASTEXITCODE
}
Write-Ok "Đã cài đặt dependencies (requirements.txt)"

# ── 2. gRPC stubs ────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 2/7: Sinh gRPC stubs từ proto/"

$StubDir = "app\api\grpc\generated"
if ((Test-Path $StubDir) -and (Get-ChildItem $StubDir -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
    Write-Ok "gRPC stubs đã tồn tại"
} else {
    & $VenvPython app\script\compile_proto.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Ok "Đã sinh gRPC stubs"
}

# ── 3. YOLO weights ──────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 3/7: Kiểm tra YOLO weights (best.pt)"

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
Write-Info "Bước 4/7: Tải trước EasyOCR models (~113MB)"

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

# ── 5. Local LLM & llama-server ──────────────────────────────────────────────
Write-Sep
Write-Info "Bước 5/7: Tải Local LLM (Qwen3.5-4B-GGUF ~2.55 GB) & llama-server"

# 5.1. Mô hình GGUF
$ModelDir = Join-Path $ScriptDir "model\checkpoint\llm"
$ModelPath = Join-Path $ModelDir "Qwen3.5-4B-Q4_K_M.gguf"
if (-not (Test-Path $ModelDir)) {
    New-Item -ItemType Directory -Path $ModelDir -Force | Out-Null
}

if ((Test-Path $ModelPath) -and ((Get-Item $ModelPath).Length -gt 2000000000)) {
    $ModelSize = [math]::Round((Get-Item $ModelPath).Length / 1GB, 2)
    Write-Ok "Qwen3.5-4B-Q4_K_M.gguf đã tồn tại ($ModelSize GB)"
} else {
    Write-Info "Đang tải mô hình Qwen3.5-4B-Q4_K_M.gguf (~2.55 GB) từ HuggingFace..."
    Write-Info "URL: https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
    $modelUrl = "https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
    try {
        if (Get-Command "curl.exe" -ErrorAction SilentlyContinue) {
            & curl.exe -L -C - --progress-bar -o $ModelPath $modelUrl
        } else {
            Invoke-WebRequest -Uri $modelUrl -OutFile $ModelPath
        }
        Write-Ok "Tải xong Qwen3.5-4B-Q4_K_M.gguf"
    } catch {
        Write-Warn "Không thể tự động tải Qwen3.5-4B-Q4_K_M.gguf: $_"
        Write-Warn "Vui lòng tải thủ công và lưu vào: $ModelPath"
    }
}

# 5.2. Binary llama-server
$LlamaDir = Join-Path $ScriptDir "var\bin\llama"
$LlamaServerExe = Join-Path $LlamaDir "llama-server.exe"
if (-not (Test-Path $LlamaDir)) {
    New-Item -ItemType Directory -Path $LlamaDir -Force | Out-Null
}

if (Test-Path $LlamaServerExe) {
    Write-Ok "llama-server.exe đã có tại $LlamaDir"
} else {
    Write-Info "Đang tải prebuilt llama.cpp binaries (b11681)..."
    $TempZipDir = Join-Path $env:TEMP "llama_setup_cache"
    if (-not (Test-Path $TempZipDir)) {
        New-Item -ItemType Directory -Path $TempZipDir -Force | Out-Null
    }

    $binZip = if ($hasNvidiaGpu) { "llama-b11681-bin-win-cuda-12.4-x64.zip" } else { "llama-b11681-bin-win-cpu-x64.zip" }
    $binUrl = "https://github.com/ggml-org/llama.cpp/releases/download/b11681/$binZip"
    $binZipPath = Join-Path $TempZipDir $binZip

    try {
        Write-Info "Tải binary $binZip..."
        if (Get-Command "curl.exe" -ErrorAction SilentlyContinue) {
            & curl.exe -L -C - --progress-bar -o $binZipPath $binUrl
        } else {
            Invoke-WebRequest -Uri $binUrl -OutFile $binZipPath
        }
        Expand-Archive -Path $binZipPath -DestinationPath $LlamaDir -Force

        if ($hasNvidiaGpu) {
            $cuZip = "cudart-llama-bin-win-cuda-12.4-x64.zip"
            $cuUrl = "https://github.com/ggml-org/llama.cpp/releases/download/b11681/$cuZip"
            $cuZipPath = Join-Path $TempZipDir $cuZip
            Write-Info "Tải CUDA runtime DLLs ($cuZip)..."
            if (Get-Command "curl.exe" -ErrorAction SilentlyContinue) {
                & curl.exe -L -C - --progress-bar -o $cuZipPath $cuUrl
            } else {
                Invoke-WebRequest -Uri $cuUrl -OutFile $cuZipPath
            }
            Expand-Archive -Path $cuZipPath -DestinationPath $LlamaDir -Force
        }
        Write-Ok "Đã cài đặt llama-server vào $LlamaDir"
    } catch {
        Write-Warn "Không thể tự động tải llama-server: $_"
        Write-Warn "Vui lòng tải prebuilt llama-server và đặt vào: $LlamaDir"
    }
}

# ── 6. .env.dev ──────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 6/7: Kiểm tra .env.dev"

if (Test-Path ".env.dev") {
    Write-Ok ".env.dev đã tồn tại"
} else {
    Copy-Item ".env.example" ".env.dev"
    Write-Ok "Đã copy .env.example → .env.dev (sửa theo máy nếu cần)"
}

# ── 7. Smoke test ────────────────────────────────────────────────────────────
Write-Sep
Write-Info "Bước 7/7: Smoke test"

try {
    & $VenvPython -c @"
from app.config import get_config
cfg = get_config()
print(f'  YOLO path:    {cfg.vision.yolo_model_path}')
print(f'  OCR langs:    {cfg.vision.ocr_language_list}')
print(f'  Device:       {cfg.vision.device}')
print(f'  gRPC port:    {cfg.server.grpc_port}')
print(f'  LLM Provider: {cfg.llm.llm_provider}')
print(f'  LLM Model:    {cfg.llm.local_llm_model_path}')
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
