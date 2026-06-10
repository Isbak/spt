#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from semantic_platform.ontology_version import ontology_version_summary

summary = ontology_version_summary()
print(f"Ontologies: {summary['ontology_count']}")
if summary["invalid_versions"]:
    for record in summary["invalid_versions"]:
        print(record)
    raise SystemExit(1)
PY
