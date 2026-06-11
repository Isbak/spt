#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'EOF'
from semantic_platform.fabric.catalog import FabricCatalog
catalog = FabricCatalog()
print(catalog.summary())
EOF
