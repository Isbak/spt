#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from semantic_platform.reasoning import reasoning_summary
summary = reasoning_summary()
print(f"Engine: {summary['engine_version']}")
print(f"Graphs: {', '.join(summary['graphs'])}")
print(f"Rules registered: {len(summary['rules'])}")
print(f"Rules used: {len(summary['rules_used'])}")
print(f"Inferred triples: {summary['inferred_count']}")
print(f"Explanations: {summary['explanation_count']}")
print(f"Consistency conforms: {summary['consistency_conforms']}")
PY
