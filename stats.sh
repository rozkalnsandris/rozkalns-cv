#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROMETHEUS_URL_RESOLVED="$(python3 "$ROOT/scripts/resolve-prometheus.py")"
PROMETHEUS_URL_RESOLVED="${PROMETHEUS_URL_RESOLVED%/}"

curl \
  --fail \
  --silent \
  --show-error \
  --connect-timeout 3 \
  --max-time 8 \
  "$PROMETHEUS_URL_RESOLVED/-/ready" \
  >/dev/null

exec python3 \
  "$ROOT/scripts/generate-stats.py" \
  --prometheus "$PROMETHEUS_URL_RESOLVED" \
  "$@"
