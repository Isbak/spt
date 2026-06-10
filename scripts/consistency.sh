#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.consistency import validate_consistency
report = validate_consistency()
print(f"Conforms: {report.conforms}")
for issue in report.issues:
    print(f"{issue.severity}: {issue.focus_node} - {issue.message} [{issue.check}]")
PY
