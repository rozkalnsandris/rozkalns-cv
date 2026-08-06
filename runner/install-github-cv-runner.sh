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

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail 'run installer through sudo'
IFS= read -r RUNNER_TOKEN || fail 'runner registration token was not provided on stdin'
[[ -n "$RUNNER_TOKEN" && "$RUNNER_TOKEN" != *[[:space:]]* ]] \
    || fail 'runner registration token format is invalid'

RUNNER_USER='github-cv-runner'
RUNNER_HOME='/home/github-cv-runner'
RUNNER_DIR="$RUNNER_HOME/actions-runner"
SOURCE_RUNNER='/home/github-release-runner/actions-runner'
REPOSITORY_URL='https://github.com/rozkalnsandris/rozkalns-cv'
RUNNER_NAME='rpi5-rozkalns-cv-release'
RUNNER_LABEL='rozkalns-cv-release'
SERVICE='actions.runner.rozkalnsandris-rozkalns-cv.rpi5-rozkalns-cv-release.service'

for command_name in chown chmod grep id install mktemp mv python3 rm runuser systemctl tar tr useradd; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail "required command is missing: $command_name"
done

if id "$RUNNER_USER" >/dev/null 2>&1 \
    && [[ -f "$RUNNER_DIR/.runner" ]] \
    && systemctl is-active --quiet "$SERVICE"; then
    if id -nG "$RUNNER_USER" | tr ' ' '\n' | grep -Fxq docker; then
        fail 'CV runner must not belong to docker group'
    fi
    printf 'CV_RUNNER_INSTALL_RESULT=ALREADY_ACTIVE\n'
    printf 'RUNNER_SERVICE=%s\n' "$SERVICE"
    printf 'RUNNER_HAS_DOCKER_GROUP=false\n'
    exit 0
fi

if systemctl is-active --quiet "$SERVICE"; then
    fail 'CV runner service is active without a valid runner registration'
fi

[[ -d "$SOURCE_RUNNER" && -x "$SOURCE_RUNNER/config.sh" ]] \
    || fail 'existing Hermes Deals runner distribution is unavailable'
[[ -x "$SOURCE_RUNNER/bin/Runner.Listener" ]] \
    || fail 'existing runner listener is unavailable'
RUNNER_VERSION=$("$SOURCE_RUNNER/bin/Runner.Listener" --version)
python3 - "$RUNNER_VERSION" <<'PY'
import sys

parts = tuple(int(value) for value in sys.argv[1].split("."))
if parts < (2, 327, 1):
    raise SystemExit("existing runner is too old; need at least 2.327.1")
PY

if ! id "$RUNNER_USER" >/dev/null 2>&1; then
    useradd \
        --create-home \
        --home-dir "$RUNNER_HOME" \
        --shell /usr/sbin/nologin \
        "$RUNNER_USER"
fi

install -d -o "$RUNNER_USER" -g "$RUNNER_USER" -m 0750 "$RUNNER_HOME"
[[ ! -L "$RUNNER_DIR" ]] || fail 'runner directory must not be a symlink'
rm -rf -- "$RUNNER_DIR"

TMP_COPY=$(mktemp -d "$RUNNER_HOME/.actions-runner-stage.XXXXXXXX")
cleanup() {
    if [[ -n "${TMP_COPY:-}" ]]; then
        rm -rf -- "$TMP_COPY"
    fi
}
trap cleanup EXIT

tar \
    --exclude='./.credentials' \
    --exclude='./.credentials_migrated' \
    --exclude='./.credentials_rsaparams' \
    --exclude='./.runner' \
    --exclude='./.runner_migrated' \
    --exclude='./.service' \
    --exclude='./.env' \
    --exclude='./_diag' \
    --exclude='./_work' \
    -C "$SOURCE_RUNNER" -cf - . \
    | tar -C "$TMP_COPY" -xf -

rm -rf -- \
    "$TMP_COPY/.credentials" \
    "$TMP_COPY/.credentials_migrated" \
    "$TMP_COPY/.credentials_rsaparams" \
    "$TMP_COPY/.runner" \
    "$TMP_COPY/.runner_migrated" \
    "$TMP_COPY/.service" \
    "$TMP_COPY/.env" \
    "$TMP_COPY/_diag" \
    "$TMP_COPY/_work"
for forbidden_state in \
    .credentials .credentials_migrated .credentials_rsaparams \
    .runner .runner_migrated .service .env _diag _work; do
    [[ ! -e "$TMP_COPY/$forbidden_state" ]] \
        || fail "copied runner retained forbidden state: $forbidden_state"
done

chown -R "$RUNNER_USER:$RUNNER_USER" "$TMP_COPY"
chmod 0750 "$TMP_COPY"
mv -- "$TMP_COPY" "$RUNNER_DIR"
TMP_COPY=''

(
    cd "$RUNNER_DIR"
    runuser -u "$RUNNER_USER" -- env \
        HOME="$RUNNER_HOME" \
        PATH='/usr/local/bin:/usr/bin:/bin' \
        ./config.sh \
        --unattended \
        --replace \
        --url "$REPOSITORY_URL" \
        --token "$RUNNER_TOKEN" \
        --name "$RUNNER_NAME" \
        --labels "$RUNNER_LABEL" \
        --work _work
)

(
    cd "$RUNNER_DIR"
    ./svc.sh install "$RUNNER_USER"
    ./svc.sh start
)

systemctl is-active --quiet "$SERVICE" || fail 'CV runner service did not start'
if id -nG "$RUNNER_USER" | tr ' ' '\n' | grep -Fxq docker; then
    fail 'CV runner must not belong to docker group'
fi

printf 'CV_RUNNER_INSTALL_RESULT=PASS\n'
printf 'RUNNER_VERSION=%s\n' "$RUNNER_VERSION"
printf 'RUNNER_SERVICE=%s\n' "$SERVICE"
printf 'RUNNER_HAS_DOCKER_GROUP=false\n'
