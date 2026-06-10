#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from app.visualizations.governance_view import governance_dashboard_data
print(governance_dashboard_data()["metrics"])
PY
