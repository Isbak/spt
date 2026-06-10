#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from semantic_platform.validate import run_validation

syntax_results, shacl_report = run_validation()
failed = [result for result in syntax_results if not result.valid]
for result in syntax_results:
    status = "PASS" if result.valid else "FAIL"
    print(f"{status} RDF syntax {result.path}")
    if result.message:
        print(result.message)
print(shacl_report.report_text)
if failed or not shacl_report.conforms:
    raise SystemExit(1)
PY
