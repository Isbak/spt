#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.named_graphs import graph_lifecycle_summary

summary = graph_lifecycle_summary()
print(f"Named graphs: {summary['named_graph_count']}")
if summary["errors"]:
    for error in summary["errors"]:
        print(error)
    raise SystemExit(1)
PY
