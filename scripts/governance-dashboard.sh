#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from app.visualizations.governance_view import governance_dashboard_data
print(governance_dashboard_data()["metrics"])
PY
