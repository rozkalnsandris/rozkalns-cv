#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ ${EUID:-$(id -u)} -ne 0 ]] || fail 'run activation as andris, not root'

SOURCE_WORKTREE='/home/andris/rozkalns-cv-worktrees/release-control'
[[ "$(pwd -P)" == "$SOURCE_WORKTREE" ]] \
    || fail 'activation must run from the detached release-control worktree'

for command_name in gh git sudo; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail "required command is missing: $command_name"
done

git fetch --prune origin main
HEAD_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse refs/remotes/origin/main)"
[[ "$HEAD_SHA" == "$REMOTE_SHA" ]] || fail 'release-control is not exact origin/main'
[[ -z "$(git branch --show-current)" ]] || fail 'release-control must remain detached'
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]] \
    || fail 'release-control worktree is not clean'

RUNNER_TOKEN="$(
    gh api \
        --method POST \
        repos/rozkalnsandris/rozkalns-cv/actions/runners/registration-token \
        --jq .token
)"
[[ -n "$RUNNER_TOKEN" ]] || fail 'GitHub did not return a runner token'

printf '%s\n' "$RUNNER_TOKEN" \
    | sudo bash ./runner/install-github-cv-runner.sh
unset RUNNER_TOKEN

sudo bash ./runner/install-github-main-deploy.sh

printf 'GITHUB_CV_ACTIVATION_RESULT=PASS\n'
printf 'SOURCE_SHA=%s\n' "$HEAD_SHA"
printf 'NEXT=successful main CI queues production deploy automatically\n'
