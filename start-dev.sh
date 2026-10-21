#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing .venv Python; prepare dependencies before starting this launcher." >&2
  exit 1
fi
exec "$PYTHON" -m app.script.run_dev "$@"
