#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from app.visualizations.ontology_browser import ontology_browser_data
print(ontology_browser_data()["statistics"])
PY
