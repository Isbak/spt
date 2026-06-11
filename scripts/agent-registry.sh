#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from semantic_platform.agents.registry import AgentRegistry
errors = AgentRegistry().validate()
if errors:
    print("\n".join(errors))
    raise SystemExit(1)
print("Agent registry validation passed")
PY
