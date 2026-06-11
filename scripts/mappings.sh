#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.mappings import list_mappings, validate_catalog

failures = validate_catalog()
for record in list_mappings():
    print(f"{record.label} | {record.version} | {record.source} -> {record.target_graph}")
if failures:
    for path, errors in failures.items():
        print(path)
        for error in errors:
            print(f"  {error}")
    raise SystemExit(1)
PY
