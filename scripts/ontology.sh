#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from app.visualizations.ontology_browser import ontology_browser_data
print(ontology_browser_data()["statistics"])
PY
