#!/usr/bin/env bash
set -euo pipefail

DATASET="${FUSEKI_DATASET:-semantic-platform}"
PORT="${FUSEKI_PORT:-3030}"
JENA_BIN="${JENA_BIN:-}"
if [[ -z "${JENA_BIN}" && -n "${JENA_HOME:-}" ]]; then
  JENA_BIN="${JENA_HOME}/bin"
fi

if [[ -n "${JENA_BIN}" && -x "${JENA_BIN}/fuseki-server" ]]; then
  FUSEKI_SERVER="${JENA_BIN}/fuseki-server"
elif command -v fuseki-server >/dev/null 2>&1; then
  FUSEKI_SERVER="$(command -v fuseki-server)"
else
  echo "fuseki-server not found. Set JENA_HOME, JENA_BIN, or add Apache Jena Fuseki to PATH." >&2
  exit 1
fi

echo "Starting local Apache Jena Fuseki on port ${PORT} with dataset /${DATASET}."
echo "This target uses an installed Jena/Fuseki distribution; it does not start Docker."
exec "${FUSEKI_SERVER}" --port="${PORT}" --mem "/${DATASET}"
