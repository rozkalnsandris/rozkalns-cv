#!/usr/bin/env bash
set -Eeuo pipefail

LEGACY_GITHUB_RUNNER_BOOTSTRAP_RETIRED=true
RUNNER_NAME='rpi5-rozkalns-cv-release'
RUNNER_HAS_DOCKER_GROUP=false
readonly LEGACY_GITHUB_RUNNER_BOOTSTRAP_RETIRED RUNNER_NAME RUNNER_HAS_DOCKER_GROUP

printf '%s\n' \
  'ERROR: legacy repository self-hosted runner installation is retired; use the RPi5 pull controller' \
  >&2
exit 64
