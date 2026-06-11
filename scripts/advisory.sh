#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from app.visualizations.advisory_view import advisory_dashboard_data
print(advisory_dashboard_data())
PY
