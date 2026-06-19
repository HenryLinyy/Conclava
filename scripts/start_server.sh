#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"
exec "${PYTHON:-python3}" -m uvicorn conclava.server:app \
  --host ${CONCLAVA_HOST:-127.0.0.1} \
  --port ${CONCLAVA_PORT:-8088}
