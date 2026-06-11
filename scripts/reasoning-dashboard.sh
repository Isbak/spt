#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from app.visualizations.reasoning_view import reasoning_dashboard_data
print(reasoning_dashboard_data()["inference_volume"])
PY
