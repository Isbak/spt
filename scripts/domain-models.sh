#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
"$PYTHON" - <<'EOF'
from semantic_platform.api import get_domain_models

models = get_domain_models()
for model in models:
    print(
        f"{model.label}: {model.class_count} classes, "
        f"{model.property_count} properties, {len(model.shapes)} shapes, "
        f"{len(model.mappings)} mappings"
    )
print(f"{len(models)} domain model(s).")
EOF
