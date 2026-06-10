#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.agents.registry import AgentRegistry
registry = AgentRegistry()
for agent in registry.list_agents():
    print(f"{agent.agent_id}: {agent.label} {agent.version} {agent.status.value}")
PY
