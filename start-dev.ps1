<#
.SYNOPSIS
    Khởi động toàn bộ IPLMS AI Microservice (PostgreSQL pgvector + FastAPI GPU).
#>
param(
    [switch]$NoBrowser
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   IPLMS AI Studio — Khởi Động Hệ Thống Dev (GPU)   " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Kiểm tra & khởi động Database pgvector trong Docker (rất nhẹ, ~50MB)
Write-Host "`n[1/3] Kiểm tra cơ sở dữ liệu Vector (PostgreSQL pgvector)..." -ForegroundColor Yellow
try {
    # Dừng container ai và gateway cũ trong docker nếu đang chạy để tránh xung đột cổng 8000
    docker compose --env-file .env.dev stop ai gateway 2>$null
    # Đảm bảo ai-db (postgres) đang chạy
    docker compose --env-file .env.dev up -d ai-db 2>$null
    Write-Host "  ✓ pgvector database đang chạy tại localhost:5435" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Không khởi động được Docker ai-db, kiểm tra xem Docker Desktop đã bật chưa." -ForegroundColor Yellow
}

# 2. Kiểm tra Python .venv và GPU
Write-Host "`n[2/3] Kiểm tra môi trường Python & Card đồ họa..." -ForegroundColor Yellow
$Python = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "  ✖ Chưa tìm thấy .venv! Vui lòng chạy .\setup-dev.ps1 trước." -ForegroundColor Red
    exit 1
}

& $Python -c @"
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import torch
cuda = torch.cuda.is_available()
name = torch.cuda.get_device_name(0) if cuda else 'CPU'
print(f'  ✓ PyTorch {torch.__version__} | CUDA: {cuda} | Device: {name}')
"@

# 3. Khởi chạy AI FastAPI REST Server
Write-Host "`n[3/3] Đang khởi chạy AI Studio tại http://localhost:8000/ ..." -ForegroundColor Green
Write-Host "  - Web Dashboard UI:  http://localhost:8000/" -ForegroundColor Cyan
Write-Host "  - API Swagger Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  - Nhấn Ctrl+C để dừng server.`n" -ForegroundColor Gray

if (-not $NoBrowser) {
    Start-Process "http://localhost:8000/"
}

& $Python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
