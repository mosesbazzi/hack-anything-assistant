#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR"

# quick self-check
python - <<'PY'
import pkgutil, pathlib
print("Has app:", bool(pkgutil.find_loader("app")))
print("Has headers.py:", pathlib.Path("app/checks/headers.py").exists())
PY

exec python -m uvicorn --app-dir "$SCRIPT_DIR" app.main:app --reload --host 0.0.0.0 --port 8000
