#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.agents.registry import AgentRegistry
errors = AgentRegistry().validate()
if errors:
    print("\n".join(errors))
    raise SystemExit(1)
print("Agent registry validation passed")
PY
