#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from rdflib import URIRef
from semantic_platform.execution.common import EXEC
from semantic_platform.execution.approvals import ExecutionApprovalEngine
from semantic_platform.execution.executor import GovernedExecutor
from semantic_platform.graph import load_graph
graph=load_graph(); approvals=ExecutionApprovalEngine(graph); action=URIRef(EXEC['update-resource-action'])
approval=approvals.request(action,'script','steward'); approvals.approve(approval.uri,'steward')
print(GovernedExecutor(graph).execute(action, policy=URIRef(EXEC['default-execution-policy'])))
PY
