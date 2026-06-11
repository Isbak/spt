#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'PY'
from rdflib import Graph
from semantic_platform.execution.outcomes import OutcomeStore
from semantic_platform.execution.verification import VerificationService
g=Graph(); outcome=OutcomeStore(g).create('https://example.org/execution/1','Succeeded','ok')
print(VerificationService(g).verify(outcome.uri))
PY
