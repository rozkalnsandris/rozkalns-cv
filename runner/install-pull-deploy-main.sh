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
LIBRARY_SOURCE="$SOURCE_WORKTREE/runner/release/rozkalns-cv-deploy-main"
WRAPPER_SOURCE="$SOURCE_WORKTREE/runner/release/rozkalns-cv-pull-deploy-main"
LIBEXEC_DIR='/usr/local/libexec/rozkalns-cv'
LIBRARY_DEST="$LIBEXEC_DIR/rozkalns-cv-deploy-library"
WRAPPER_DEST='/usr/local/sbin/rozkalns-cv-pull-deploy-main'
SUDOERS='/etc/sudoers.d/rozkalns-cv-pull-deploy'
CALLER='andris'
EVIDENCE_ROOT='/home/andris/.local/state/rozkalns-cv-pull-deploy/evidence'

for command_name in bash chmod id install stat visudo; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail "required command is missing: $command_name"
done

[[ -f "$LIBRARY_SOURCE" && ! -L "$LIBRARY_SOURCE" ]] \
    || fail "deploy library source is missing or unsafe: $LIBRARY_SOURCE"
[[ -f "$WRAPPER_SOURCE" && ! -L "$WRAPPER_SOURCE" ]] \
    || fail "pull-deploy wrapper source is missing or unsafe: $WRAPPER_SOURCE"
id "$CALLER" >/dev/null 2>&1 || fail "pull-deploy caller is missing: $CALLER"
bash -n "$LIBRARY_SOURCE"
bash -n "$WRAPPER_SOURCE"

install -d -o root -g root -m 0755 "$LIBEXEC_DIR"
install -o root -g root -m 0755 "$LIBRARY_SOURCE" "$LIBRARY_DEST"
install -o root -g root -m 0755 "$WRAPPER_SOURCE" "$WRAPPER_DEST"
install -d -o "$CALLER" -g "$CALLER" -m 0700 "$EVIDENCE_ROOT"

[[ "$(stat -c '%U:%G:%a' "$LIBRARY_DEST")" == 'root:root:755' ]] \
    || fail 'installed deploy library ownership/mode is unexpected'
[[ "$(stat -c '%U:%G:%a' "$WRAPPER_DEST")" == 'root:root:755' ]] \
    || fail 'installed pull-deploy wrapper ownership/mode is unexpected'
[[ "$(stat -c '%U:%G:%a' "$EVIDENCE_ROOT")" == "$CALLER:$CALLER:700" ]] \
    || fail 'pull-deploy evidence root ownership/mode is unexpected'

cat >"$SUDOERS" <<'EOF'
andris ALL=(root) NOPASSWD: /usr/local/sbin/rozkalns-cv-pull-deploy-main *
EOF
chmod 0440 "$SUDOERS"
visudo -cf "$SUDOERS" >/dev/null

printf 'PULL_DEPLOY_TRANSPORT_INSTALL_RESULT=PASS\n'
printf 'LEGACY_HELPER_CHANGED=false\n'
printf 'LEGACY_RUNNER_RULE_CHANGED=false\n'
printf 'HOST_CONTROL_PLANE_CHANGED=true\n'
printf 'PRODUCTION_APPLICATION_CHANGED=false\n'
