#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from app.visualizations.provenance_view import provenance_view_data
print(provenance_view_data()["metrics"])
PY
