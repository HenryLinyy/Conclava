#!/usr/bin/env bash
set -euo pipefail

CONCLAVA_BASE_URL="${CONCLAVA_BASE_URL:-http://127.0.0.1:8088/v1}"
MODEL="${MODEL:-conclava-fast}"

echo "Benchmarking ${MODEL} via ${CONCLAVA_BASE_URL}/responses"
time curl -fsS "${CONCLAVA_BASE_URL}/responses" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"input\": \"用一句話回答：Conclava 是什麼？\",
    \"stream\": false
  }" >/tmp/conclava-benchmark-response.json

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/conclava-benchmark-response.json").read_text())
output = data.get("output", [])
text = output[0].get("text", "") if output else ""
print("output_chars=", len(text))
print("usage=", data.get("usage"))
PY
