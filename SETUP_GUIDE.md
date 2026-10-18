# AI local setup and integration notes

This integration retains the current CPU Docker contract and modular ONNX/two-line pipeline. CUDA is not installed or enabled automatically. No real-model benchmark is certified by this guide.

- Read [DESIGN](DESIGN.md), [AI conventions](docs/AI_CONVENTIONS.md), and [branch workflow](docs/GIT_WORKFLOW.md).
- Image build context remains the umbrella root: `docker build -f ai/Dockerfile .`. Standalone image CI recreates this layout. `Dockerfile.dockerignore` travels with the Dockerfile and excludes runtime photos, training checkpoints and unrelated data. Do not build from the AI directory alone.
- `setup-dev.ps1` / `setup-dev.sh` install requirements and may download models/create local configuration. Run only after dependency/setup approval; this integration did not execute setup or install packages.
- Once dependencies and service prerequisites are prepared, `start-dev.ps1 -NoBrowser` or `bash start-dev.sh` supervises native REST and gRPC together. A busy port or exited child is an error; existing Docker services are never stopped. A listener is not proof that model/DB/provider are ready.
- The native launcher binds both transports to loopback. Docker retains its internal gRPC binding and loopback gateway contract. Do not expose the developer tools through the gateway.
- Developer diagnostics are disabled by default. `AI_DEVELOPER_DASHBOARD_ENABLED=true` only enables the direct-loopback Vision diagnostics under `/api/vision/*`. The old `/dashboard` page was removed (IPLMS ADR-0050): configuration checks, trying Copilot and uploading knowledge drafts live in the AI Console "Công cụ thử" page (`http://localhost:8090/console/tools`), with login, roles and audit.
- Knowledge ingestion creates a draft. Reuse the document UUID on retry; a new draft version may still be created. Evaluation/publication remains the existing workflow.
- Randomly initialized checkpoints are not trained models; the new checkpoint generator was excluded from integration. Never overwrite a checkpoint to make a service appear ready.

Focused offline checks and remaining integration gates are recorded in the issue handoff. Do not run real ingestion, model downloads or provider calls as a smoke test without an authorized local fixture.
