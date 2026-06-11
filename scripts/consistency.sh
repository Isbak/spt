#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.consistency import validate_consistency
report = validate_consistency()
print(f"Conforms: {report.conforms}")
for issue in report.issues:
    print(f"{issue.severity}: {issue.focus_node} - {issue.message} [{issue.check}]")
PY
