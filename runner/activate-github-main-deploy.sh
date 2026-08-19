#!/usr/bin/env bash
set -Eeuo pipefail

LEGACY_GITHUB_RUNNER_BOOTSTRAP_RETIRED=true
readonly LEGACY_GITHUB_RUNNER_BOOTSTRAP_RETIRED

printf '%s\n' \
  'ERROR: legacy GitHub self-hosted runner activation is retired; use the RPi5 pull controller' \
  >&2
exit 64
