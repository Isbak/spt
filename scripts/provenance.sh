#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.config import load_settings
from semantic_platform.provenance import load_provenance_graph
from semantic_platform.query import read_query, result_rows

settings = load_settings()
rows = result_rows(
    load_provenance_graph(settings=settings).query(
        read_query(settings.queries_dir / "provenance_trace.rq")
    )
)
print(f"Provenance rows: {len(rows)}")
if not rows:
    raise SystemExit(1)
PY
