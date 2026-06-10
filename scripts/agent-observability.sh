#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.agents.observations import AgentObservationLog, ObservationType
from semantic_platform.agents.registry import AgentRegistry
agent = AgentRegistry().require("semantic-context-agent")
log = AgentObservationLog()
log.record(agent, ObservationType.REQUEST, "observability smoke test")
print(log.metrics())
PY
