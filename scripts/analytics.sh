#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from app.visualizations.analytics_view import analytics_dashboard_data
print(analytics_dashboard_data())
PY
