#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.agents.provenance import AgentProvenanceRecorder
from semantic_platform.agents.registry import AgentRegistry
agent = AgentRegistry().require("semantic-context-agent")
recorder = AgentProvenanceRecorder()
chain = recorder.record_execution(agent, request_user="make", graphs_accessed=["reference"], output_text="smoke")
print(f"Agent provenance execution: {chain.execution}")
PY
