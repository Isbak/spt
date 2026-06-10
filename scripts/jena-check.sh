#!/usr/bin/env bash
set -euo pipefail

JENA_BIN="${JENA_BIN:-}"
if [[ -z "${JENA_BIN}" && -n "${JENA_HOME:-}" ]]; then
  JENA_BIN="${JENA_HOME}/bin"
fi

find_command() {
  local command_name="$1"
  if [[ -n "${JENA_BIN}" && -x "${JENA_BIN}/${command_name}" ]]; then
    printf '%s\n' "${JENA_BIN}/${command_name}"
    return 0
  fi
  if command -v "${command_name}" >/dev/null 2>&1; then
    command -v "${command_name}"
    return 0
  fi
  return 1
}

missing=0
for command_name in riot arq fuseki-server; do
  if resolved="$(find_command "${command_name}")"; then
    echo "Found ${command_name}: ${resolved}"
  else
    echo "Missing ${command_name}. Set JENA_HOME, JENA_BIN, or add Apache Jena/Fuseki commands to PATH." >&2
    missing=1
  fi
done

exit "${missing}"
