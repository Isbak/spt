#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.governance import governance_summary

summary = governance_summary()
print(f"Graph assets: {summary['graph_asset_count']}")
if summary["errors"]:
    for error in summary["errors"]:
        print(error)
    raise SystemExit(1)
PY
