#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from semantic_platform.governance import governance_summary

summary = governance_summary()
print(f"Graph assets: {summary['graph_asset_count']}")
if summary["errors"]:
    for error in summary["errors"]:
        print(error)
    raise SystemExit(1)
PY
