#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from app.visualizations.analytics_view import analytics_dashboard_data
print(analytics_dashboard_data())
PY
