#!/usr/bin/env bash
set -euo pipefail
python - <<'EOF'
from semantic_platform.fabric.catalog import FabricCatalog
catalog = FabricCatalog()
print(catalog.summary())
EOF
