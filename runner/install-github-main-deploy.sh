#!/usr/bin/env bash
set -Eeuo pipefail

LEGACY_GITHUB_RUNNER_BOOTSTRAP_RETIRED=true
readonly LEGACY_GITHUB_RUNNER_BOOTSTRAP_RETIRED

# Historical retired sudo contract, retained only as an inert migration marker:
# github-cv-runner ALL=(root) NOPASSWD: /usr/local/sbin/rozkalns-cv-deploy-main *

printf '%s\n' \
  'ERROR: legacy GitHub-runner deploy-helper installation is retired; use the RPi5 pull controller' \
  >&2
exit 64
