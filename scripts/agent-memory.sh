#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.agents.memory import AgentMemoryStore, MemoryType
from semantic_platform.agents.registry import AgentRegistry
agent = AgentRegistry().require("semantic-context-agent")
store = AgentMemoryStore()
store.remember(agent, MemoryType.WORKING, "memory smoke test")
print(f"Agent memory entries: {len(store.recall(agent))}")
PY
