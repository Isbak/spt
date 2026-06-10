#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.rule_registry import load_rule_registry
for rule in load_rule_registry().all():
    print(f"{rule.label} | version={rule.version} | owner={rule.owner} | steward={rule.steward} | status={rule.status} | executable={rule.executable}")
PY
