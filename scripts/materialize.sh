#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from semantic_platform.api import materialize_sources, load_sources_into_fuseki
from semantic_platform.materialize import mapping_files

results = materialize_sources()
if not results:
    raise SystemExit("No R2RML mappings found in mappings/r2rml/")

total = 0
for result in results:
    total += result.triple_count
    print(
        f"{result.mapping_path.name} | rows={result.record_count} "
        f"triples={result.triple_count} -> {result.target_graph} ({result.output_path})"
    )
if total == 0:
    raise SystemExit("Materialization produced no triples")

# Best-effort load into Fuseki; skipped (not failed) when the server is down so
# local materialization and CI stay green without a running Fuseki.
for load in load_sources_into_fuseki():
    state = "loaded" if load.loaded else "skipped"
    print(f"fuseki {state}: {load.target_graph} ({load.message})")
PY
