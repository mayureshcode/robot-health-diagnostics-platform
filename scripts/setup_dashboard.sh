#!/usr/bin/env bash
# Optional dashboard Python dependencies in the existing isolated venv.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv --system-site-packages .venv
fi
if ! .venv/bin/python -c 'import fastapi, uvicorn, httpx; from pydantic import ConfigDict' >/dev/null 2>&1; then
  echo '[RHM] Installing pinned FastAPI/Pydantic dashboard dependencies ...'
  .venv/bin/python -m pip install --disable-pip-version-check \
    --timeout 120 --retries 4 -r tools/dashboard-requirements.txt
fi
.venv/bin/python -c 'import fastapi, uvicorn, httpx; from pydantic import ConfigDict' || {
  echo '[RHM] ERROR: dashboard dependencies unavailable' >&2
  exit 2
}
echo '[RHM] FastAPI dashboard dependencies available in .venv'
