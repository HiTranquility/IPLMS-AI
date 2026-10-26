# AI local setup and integration notes

This integration retains the current CPU Docker contract and modular ONNX/two-line pipeline. CUDA is not installed or enabled automatically. No real-model benchmark is certified by this guide.

- Read [DESIGN](DESIGN.md), [AI conventions](docs/standards/AI_CONVENTIONS.md), and [branch workflow](docs/standards/GIT_WORKFLOW.md).
- Image build context remains the umbrella root: `docker build -f ai/Dockerfile .`. Standalone image CI recreates this layout. `Dockerfile.dockerignore` travels with the Dockerfile and excludes runtime photos, training checkpoints and unrelated data. Do not build from the AI directory alone.
- `setup-dev.ps1` / `setup-dev.sh` install requirements and may download models/create local configuration. Run only after dependency/setup approval; this integration did not execute setup or install packages.
- Once dependencies and service prerequisites are prepared, `start-dev.ps1 -NoBrowser` or `bash start-dev.sh` supervises native REST and gRPC together. A busy port or exited child is an error; existing Docker services are never stopped. A listener is not proof that model/DB/provider are ready.
- The native launcher binds both transports to loopback. Docker retains its internal gRPC binding and loopback gateway contract. Do not expose the developer tools through the gateway.
- Developer diagnostics are disabled by default. `AI_DEVELOPER_DASHBOARD_ENABLED=true` only enables the direct-loopback Vision diagnostics under `/api/vision/*`. The old `/dashboard` page was removed (IPLMS ADR-0050): configuration checks, trying Copilot and uploading knowledge drafts live in the AI Console "Công cụ thử" page (`http://localhost:8090/console/tools`), with login, roles and audit.
- Knowledge ingestion creates a draft. Reuse the document UUID on retry; a new draft version may still be created. Evaluation/publication remains the existing workflow.
- Randomly initialized checkpoints are not trained models; the new checkpoint generator was excluded from integration. Never overwrite a checkpoint to make a service appear ready.

Focused offline checks and remaining integration gates are recorded in the issue handoff. Do not run real ingestion, model downloads or provider calls as a smoke test without an authorized local fixture.
# 🚀 IPLMS-AI: Developer Setup & Troubleshooting Guide
*(Comprehensive Environment Setup Guide for All Developers & Platforms)*

**Version:** `v0.5.0`  
**Target Environments:** Windows 10/11, Ubuntu/Debian Linux, macOS (Apple Silicon / Intel), Docker Engine / Docker Desktop.

---

## 📋 Table of Contents
1. [Overview of Architecture & Port Allocation](#1-overview-of-architecture--port-allocation)
2. [Hardware Acceleration Matrix (GPU vs CPU)](#2-hardware-acceleration-matrix-gpu-vs-cpu)
3. [Pre-packaged Model Artifacts (Zero Manual Model Hunt)](#3-pre-packaged-model-artifacts-zero-manual-model-hunt)
4. [Quickstart 1: Windows (1-Click Automated Setup)](#4-quickstart-1-windows-1-click-automated-setup)
5. [Quickstart 2: Linux & macOS (Bash Setup)](#5-quickstart-2-linux--macos-bash-setup)
6. [Quickstart 3: Docker-Only (Full Containerized Stack)](#6-quickstart-3-docker-only-full-containerized-stack)
7. [Important Gotchas: Database Connection (Host vs Docker)](#7-important-gotchas-database-connection-host-vs-docker)
8. [Verification, Dashboard & Test Execution](#8-verification-dashboard--test-execution)
9. [Troubleshooting & Common Pitfalls](#9-troubleshooting--common-pitfalls)

---

## 1. Overview of Architecture & Port Allocation

The IPLMS AI service provides 3 primary AI capabilities:
- **Vision Pipeline**: License plate recognition (YOLOv8 + EasyOCR) and vehicle classification (CNN NetV2).
- **Copilot & RAG**: Knowledge base retrieval and dispute arbitration guidance via pgvector and OpenAI.
- **Forecast & Tariff**: Parking lot occupancy predictions and dynamic pricing simulation.

### Port Allocation:

| Service / Transport | Port (Internal) | Port (Host / Public) | Description |
| :--- | :---: | :---: | :--- |
| **FastAPI REST API & Web UI** | `:8000` | `http://localhost:8000/` | Web Dashboard SPA, image recognition API, Swagger docs (`/docs`). |
| **Local LLM llama-server (CUDA)** | `:8005` | `http://localhost:8005/` | Local OpenAI-compatible server running Qwen3.5-4B-GGUF with full CUDA GPU offload. |
| **gRPC Server** | `:50051` | `localhost:50051` | High-performance RPC transport called by IPLMS NestJS backend. |
| **PostgreSQL (pgvector)** | `:5432` | `localhost:5435` | Dedicated PostgreSQL 16 + pgvector for Copilot knowledge chunks. |
| **Traefik L7 Gateway** | `:8000`, `:50051` | `:8000`, `:50051`, `:8080` | Reverse proxy and HTTP/2 cleartext (h2c) gRPC load balancer. |

---

## 2. Hardware Acceleration Matrix (GPU vs CPU)

The service is fully platform-adaptive. It automatically detects hardware upon running `setup-dev` or starting the service:

| Hardware Profile | Detection | Installed Package | Configuration (`.env.dev`) | Expected Latency |
| :--- | :--- | :--- | :--- | :---: |
| **NVIDIA GPU (Windows/Linux)** | `nvidia-smi` detected | `torch==2.6.0+cu124`<br>`llama-server` CUDA 12.4 | `AI_DEVICE=cuda`<br>`AI_LLM_PROVIDER=local` | ⚡ **ANPR:** 150ms - 300ms<br>⚡ **LLM RAG:** 2s - 3s (100% GPU offload, ~20 t/s) |
| **CPU Only (Windows/Linux)** | No NVIDIA GPU | Standard CPU PyTorch (via `requirements.txt`) | `AI_DEVICE=cpu` or `auto` | ⏱️ **ANPR:** 1.2s - 2.0s<br>⏱️ **LLM:** 6s - 10s (CPU fallback) |
| **macOS (Apple Silicon M1/M2/M3)** | Darwin / MPS | Standard PyTorch (via `requirements.txt`) | `AI_DEVICE=cpu` | ⏱️ **ANPR:** 800ms - 1.5s |

> [!NOTE]
> Developers without NVIDIA GPUs do **not** need to install CUDA. The system gracefully executes on CPU without breaking any features or unit tests.
> Khi có card NVIDIA (ví dụ GTX 1650 4GB), hệ thống tự động offload **100% toàn bộ 33 layers** của mô hình `Qwen3.5-4B-Q4_K_M` lên VRAM (~2.9GB VRAM với `-np 1 -c 4096`), vẫn chừa lại >1.1GB VRAM cho pipeline Vision (YOLOv8 + EasyOCR).

---

## 3. Pre-packaged Model Artifacts (Zero Manual Model Hunt)

All required deep learning checkpoints are pre-bundled directly within the repository. New developers do **not** need to manually download weights from external cloud drives:

1. **YOLOv8 Plate Detector:** Located at `model/artifacts/bootstrap/anpr/best.pt` (~6MB).
2. **Vehicle Classifier CNN:** Located at `model/checkpoint/vehicle-classifier.pth` (`NetV2`, ~4.5MB).
3. **EasyOCR Character Recognition Models:** Automatically downloaded during setup into `var/easyocr-cache/` (~113MB) to prevent pollution of user home directories.
4. **Local Copilot LLM:** `Qwen3.5-4B-Q4_K_M.gguf` (~2.55GB) in `model/checkpoint/llm/` served via official prebuilt CUDA 12.4 `llama-server` binaries in `var/bin/llama/` (không yêu cầu cài đặt Visual Studio C++ Compiler).

---

## 4. Quickstart 1: Windows (1-Click Automated Setup)

### Prerequisites:
- Windows 10/11 (64-bit).
- Python 3.10, 3.11, or 3.12 installed and added to `PATH`.
- Docker Desktop installed and running (for the lightweight PostgreSQL pgvector database).

### Step-by-Step:

1. **Open PowerShell in the project directory**:
   ```powershell
   cd <path-to-cloned-repo>
   ```

2. **Run the Automated Setup Script**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup-dev.ps1
   ```
   *This script automatically:*
   * Creates the virtual environment `.venv`.
   * Checks for an NVIDIA GPU and installs PyTorch CUDA 12.4 if present, or CPU PyTorch if not.
   * Compiles gRPC stubs from `proto/`.
   * Verifies YOLO and CNN weights.
   * Caches EasyOCR models into `var/easyocr-cache/` (~113MB).
   * **Downloads Local Copilot LLM & llama-server:** Checks and downloads `Qwen3.5-4B-Q4_K_M.gguf` (~2.55 GB) from Hugging Face into `model/checkpoint/llm/`, plus prebuilt CUDA 12.4 / CPU `llama-server` binaries into `var/bin/llama/`.
   * Generates `.env.dev` from `.env.example`.
   * Executes smoke tests verifying vision, gRPC, and LLM configuration.

3. **Launch All Services (One-Click Launcher)**:
   ```powershell
   .\start-dev.ps1
   # Hoặc mở Command Prompt / Nhấp đúp chuột vào file:
   .\start.bat
   ```
   *This script starts `ai-db` (pgvector on port 5435), verifies CUDA availability, opens the default browser, and launches the FastAPI Web UI on `http://localhost:8000/`.*

4. **Alternative: Run Manually**:
   * **FastAPI Web Server:**
     ```powershell
     .\.venv\Scripts\Activate.ps1
     uvicorn app.main:app --reload --port 8000
     ```
   * **gRPC Server:**
     ```powershell
     .\.venv\Scripts\Activate.ps1
     python -m app.grpc_server
     ```

---

## 5. Quickstart 2: Linux & macOS (Bash Setup)

### Prerequisites:
- Python 3.10, 3.11, or 3.12 (`python3-venv` package on Debian/Ubuntu).
- Docker Engine or Docker Desktop.

### Step-by-Step:

1. **Navigate to the repository root**:
   ```bash
   cd <path-to-cloned-repo>
   ```

2. **Make scripts executable and run setup**:
   ```bash
   chmod +x setup-dev.sh start-dev.sh
   bash setup-dev.sh
   ```
   *This script automatically performs all 7 steps: `.venv` setup, CUDA detection, gRPC stub generation, weights verification, EasyOCR caching, automated download of `Qwen3.5-4B-Q4_K_M.gguf` & prebuilt `llama-server`, `.env.dev` generation, and smoke tests.*

3. **Start the service**:
   ```bash
   bash start-dev.sh
   ```
   *Access the dashboard at `http://localhost:8000/`.*

---

## 6. Quickstart 3: Docker-Only (Full Containerized Stack)

Use this method when you want to test the exact production container orchestration (Traefik Gateway + AI Microservice + pgvector).

### Steps:

1. **Create the shared Docker bridge network** *(one-time setup required by docker-compose)*:
   ```bash
   docker network create iplms-backend-dev_default
   ```

2. **Build and start all 3 containers**:
   ```bash
   # Thiếu file develop thì Traefik dùng traefik.yml: dashboard :8080 tắt.
   docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.develop.yml up -d --build
   ```

3. **Check container health**:
   ```bash
   docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.develop.yml ps
   ```
   *All services (`iplms-ai-dev-ai`, `iplms-ai-dev-gateway`, `iplms-ai-dev-postgres`) should be in `Up (healthy)` state.*

4. **Stop the stack**:
   ```bash
   docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.develop.yml down
   ```

---

## 7. Important Gotchas: Database Connection (Host vs Docker)

In `.env.dev`, the default database URL is configured for Docker networking:
```env
AI_DATABASE_URL=postgresql://postgres:change-me@ai-db:5432/iplms_knowledge
```

* **Inside Docker Containers:** Containers resolve `ai-db` via the internal Docker bridge network on port `5432`.
* **Running Python Natively on Host:** The PostgreSQL container maps its port to host port `5435`. If you run Copilot RAG queries from local Python, change the host in `.env.dev`:
  ```env
  AI_DATABASE_URL=postgresql://postgres:change-me@localhost:5435/iplms_knowledge
  ```

---

## 8. Verification, Dashboard & Test Execution

### 1. Web Dashboard (UI)
Open your browser at:
```text
http://localhost:8000/
```
* Use the **Vision / ANPR** tab to upload vehicle photos or test with pre-loaded samples.
* View real-time processing time, confidence score, bounding box crop, and detected vehicle type.

### 2. Swagger / OpenAPI Documentation
Open:
```text
http://localhost:8000/docs
```

### 3. Run the Unit Test Suite
To verify that vision algorithms, syntax parsers, and prior fusion rules pass:
```powershell
# Windows
.\.venv\Scripts\python.exe -m unittest test.test_confidence test.test_plate_text test.test_plate_metrics test.test_vision_mapper test.test_vision_optimizations

# Linux / macOS
python -m unittest test.test_confidence test.test_plate_text test.test_plate_metrics test.test_vision_mapper test.test_vision_optimizations
```
*Expected: 66/66 tests PASSED.*

---

## 9. Troubleshooting & Common Pitfalls

| Symptom / Error | Root Cause | Exact Solution |
| :--- | :--- | :--- |
| `script cannot be loaded because running scripts is disabled` | Windows PowerShell ExecutionPolicy defaults to `Restricted` | Execute with bypass flag: `powershell -ExecutionPolicy Bypass -File .\setup-dev.ps1` |
| `UnicodeEncodeError: 'charmap' codec can't encode character '\u2588'` | Windows console codepage defaults to CP1252 | Handled automatically in `setup-dev.ps1`. If running manually, execute `$env:PYTHONIOENCODING="utf-8"` |
| `network iplms-backend-dev_default declared as external, but could not be found` | Docker external network has not been created yet | Run `docker network create iplms-backend-dev_default` |
| `UserWarning: expandable_segments not supported on this platform` | PyTorch on Windows CUDA allocator notification | **Safe to ignore.** PyTorch Windows does not support dynamic segment expansion; the engine includes automatic `torch.cuda.empty_cache()` handling. |
| `Port already in use: 8000 or 50051` | A previous instance of Uvicorn or Docker container is holding the port | On Windows: `Get-Process python \| Stop-Process -Force` or run `docker compose stop ai gateway` |
| `exec /usr/local/bin/docker-entrypoint.sh: no such file or directory` | Windows Git checkout converted script line endings to CRLF (`\r\n`) | Handled automatically by `RUN sed -i 's/\r$//'` in `Dockerfile`. Ensure Git uses `git config core.autocrlf input`. |
| `ImportError: cannot import name 'readtext'` or corrupted torch | Interrupted pip download left incomplete wheel package | Run: `pip install --force-reinstall --no-deps torch torchvision` |
