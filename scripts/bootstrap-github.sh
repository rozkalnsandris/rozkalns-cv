#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
REPOSITORY='rozkalnsandris/rozkalns-cv'

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ ${EUID:-$(id -u)} -ne 0 ]] || fail 'run as andris, not root'
[[ "$(pwd -P)" == "$ROOT" ]] || fail "run from repository root: $ROOT"

for command_name in gh git docker python3; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail "required command is missing: $command_name"
done

bash scripts/validate-source.sh "$ROOT"

if [[ ! -d .git ]]; then
    git init -b main
fi

git config user.name >/dev/null 2>&1 || git config user.name 'Andris Rožkalns'
git config user.email >/dev/null 2>&1 || git config user.email 'andris@rozkalns.net'

if [[ -n "$(git status --porcelain=v1 --untracked-files=all)" ]]; then
    git add --all
    git commit -m 'chore: import current rozkalns.net production source'
fi

if ! gh repo view "$REPOSITORY" >/dev/null 2>&1; then
    gh repo create "$REPOSITORY" \
        --private \
        --description 'Source and safe RPi5 deployment for rozkalns.net CV' \
        --source . \
        --remote origin
elif ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "git@github.com:${REPOSITORY}.git"
fi

git branch -M main
git push --set-upstream origin main

printf 'GITHUB_BOOTSTRAP_RESULT=PASS\n'
printf 'REPOSITORY=%s\n' "$REPOSITORY"
printf 'NEXT=install dedicated release runner from a detached origin/main worktree\n'
