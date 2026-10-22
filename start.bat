@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Chuyen thu muc lam viec ve thu muc chua file batch
cd /d "%~dp0"
title IPLMS AI Studio ^& Microservice

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ====================================================
echo    IPLMS AI Studio -- Khoi Dong He Thong Dev (GPU)
echo ====================================================

:: Phan tich tham so dau vao
set NO_BROWSER=0
if /i "%~1"=="--no-browser" set NO_BROWSER=1
if /i "%~1"=="/nobrowser" set NO_BROWSER=1
if /i "%~1"=="-n" set NO_BROWSER=1

:: 1. Kiem tra & khoi dong Database pgvector trong Docker (tuy chon)
echo.
echo [1/3] Kiem tra co so du lieu Vector (PostgreSQL pgvector)...
where docker >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    docker compose --env-file .env.dev stop ai gateway >nul 2>&1
    docker compose --env-file .env.dev up -d ai-db >nul 2>&1
    echo   [OK] pgvector database dang chay tai localhost:5435
) else (
    echo   [INFO] Docker chua bat hoac chua cai dat. He thong su dung Local Seed Fallback.
)

:: 2. Kiem tra Python .venv va Card do hoa
echo.
echo [2/3] Kiem tra moi truong Python ^& Card do hoa GPU...
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   [ERROR] Chua tim thay .venv!
    echo   Vui long chay lenh sau trong PowerShell de cai dat moi truong:
    echo     powershell -ExecutionPolicy Bypass -File .\setup-dev.ps1
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import os; os.environ['OPENBLAS_NUM_THREADS'] = '1'; import torch; cuda = torch.cuda.is_available(); name = torch.cuda.get_device_name(0) if cuda else 'CPU'; print(f'  [OK] PyTorch {torch.__version__} | CUDA: {cuda} | Device: {name}')"
if %ERRORLEVEL% NEQ 0 (
    echo   [WARN] Canh bao: Loi khi kiem tra PyTorch CUDA.
)

:: 3. Khoi chay AI Studio Web UI & Uvicorn Server
echo.
echo [3/3] Dang khoi chay AI Studio tai http://localhost:8000/ ...
echo   - Web Dashboard UI:  http://localhost:8000/
echo   - API Swagger Docs:  http://localhost:8000/docs
echo   - Local LLM Engine:  llama-server (Qwen3.5-4B CUDA) tai port 8005
echo   - Nhan Ctrl+C de dung server.
echo.

if %NO_BROWSER% EQU 0 (
    start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000/"
)

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server da dung voi ma loi %ERRORLEVEL%.
    pause
)
