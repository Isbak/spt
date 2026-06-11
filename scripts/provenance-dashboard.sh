#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from app.visualizations.provenance_view import provenance_view_data
print(provenance_view_data()["metrics"])
PY
