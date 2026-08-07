#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

# The CV can be deployed to any checkout path. Keep the scheduled entrypoint
# location-independent and publish into the same checkout that owns this
# script unless an explicit --output was supplied for validation/testing.
has_output=false
for arg in "$@"; do
  if [[ "$arg" == "--output" || "$arg" == --output=* ]]; then
    has_output=true
    break
  fi
done

if [[ "$has_output" == false ]]; then
  set -- --output "$ROOT/html/stats.json" "$@"
fi

exec python3 "$ROOT/scripts/generate-stats.py" "$@"
