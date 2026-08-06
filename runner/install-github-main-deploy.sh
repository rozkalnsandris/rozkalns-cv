#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077
PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
export PATH

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail 'run installer with sudo'

SOURCE_WORKTREE='/home/andris/rozkalns-cv-worktrees/release-control'
SOURCE="$SOURCE_WORKTREE/runner/release/rozkalns-cv-deploy-main"
DEST='/usr/local/sbin/rozkalns-cv-deploy-main'
SUDOERS='/etc/sudoers.d/rozkalns-cv-github-deploy'
RUNNER='github-cv-runner'

for command_name in bash chmod id install visudo; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail "required command is missing: $command_name"
done

[[ -f "$SOURCE" ]] || fail "release helper is missing: $SOURCE"
id "$RUNNER" >/dev/null 2>&1 || fail "runner user is missing: $RUNNER"
bash -n "$SOURCE"

install -o root -g root -m 0755 "$SOURCE" "$DEST"

cat >"$SUDOERS" <<'EOF'
github-cv-runner ALL=(root) NOPASSWD: /usr/local/sbin/rozkalns-cv-deploy-main *
EOF
chmod 0440 "$SUDOERS"
visudo -cf "$SUDOERS" >/dev/null

printf 'HELPER_INSTALL_RESULT=PASS\n'
printf 'PRODUCTION_CHANGED=false\n'
