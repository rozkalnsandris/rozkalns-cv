#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

ROOT="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}"
NETWORK_NAME='cv_default'
NETWORK_SUBNET='172.19.0.0/16'
NETWORK_GATEWAY='172.19.0.1'
VALIDATION_TMP=''
created_placeholders=()

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    local placeholder
    for placeholder in "${created_placeholders[@]:-}"; do
        rm -f -- "$placeholder"
    done
    if [[ -n "$VALIDATION_TMP" && -d "$VALIDATION_TMP" ]]; then
        rm -rf -- "$VALIDATION_TMP"
    fi
}
trap cleanup EXIT

[[ -d "$ROOT" ]] || fail "repository root is missing: $ROOT"
VALIDATION_TMP="$(mktemp -d "${TMPDIR:-/tmp}/rozkalns-cv-validate.XXXXXXXX")"

for required in \
    README.md \
    .gitignore \
    content/profile.json \
    content/profile.schema.json \
    content/pdf-manifest.json \
    content/translations/en.json \
    content/translations/de.json \
    content/translations/lv.json \
    bot/system_prompt.txt \
    frontend/index.html \
    frontend/smarthome.html \
    frontend/app.mjs \
    frontend/enhancements.mjs \
    frontend/smarthome.mjs \
    frontend/styles/main.css \
    frontend/styles/extra.css \
    frontend-dist-manifest.json \
    package.json \
    package-lock.json \
    vite.config.mjs \
    scripts/build-frontend.mjs \
    scripts/check-frontend-dist.mjs \
    scripts/build-content.py \
    scripts/sync-system-prompt.py \
    scripts/validate-source.sh \
    .github/workflows/ci.yml \
    .github/workflows/deploy-main.yml
do
    [[ -s "$ROOT/$required" ]] || fail "required file is missing or empty: $required"
done

for retired in update.sh update_cv-1.sh cloudflared.env.example; do
    [[ ! -e "$ROOT/$retired" ]] \
        || fail "retired source file must not exist: $retired"
done
[[ ! -e "$ROOT/docker-compose.network.yml" ]] \
    || fail 'legacy docker-compose.network.yml must be merged into the primary Compose file'
[[ ! -e "$ROOT/.venv" ]] \
    || fail 'repository-local .venv is generated state and must not exist'
[[ ! -e "$ROOT/node_modules" ]] \
    || fail 'repository-local node_modules is generated state and must not exist'
[[ ! -e "$ROOT/node_modules" ]] \
    || fail 'repository-local node_modules is generated state and must not exist'
[[ ! -e "$ROOT/node_modules" ]] \
    || fail 'repository-local node_modules is generated state and must not exist'
[[ ! -e "$ROOT/node_modules" ]] \
    || fail 'repository-local node_modules is generated state and must not exist'
[[ ! -e "$ROOT/.github/workflows/canonical-content-artifact.yml" ]] \
    || fail 'temporary canonical content finalizer must not remain in the repository'

find_generated_artifact() {
    find "$ROOT" \
        -path "$ROOT/.git" -prune -o \
        \( -type d -name '__pycache__' -o \
           -type f \( -name '*.pyc' -o -name '*.pyo' \) \) \
        -print -quit
}

if generated="$(find_generated_artifact)" && [[ -n "$generated" ]]; then
    fail "generated Python artifact must not exist: ${generated#$ROOT/}"
fi

compose=''
for candidate in docker-compose.yml docker-compose.yaml compose.yml compose.yaml; do
    if [[ -s "$ROOT/$candidate" ]]; then
        compose="$ROOT/$candidate"
        break
    fi
done
[[ -n "$compose" ]] || fail 'no Docker Compose file found'

if grep -Eiq '(^|[^[:alnum:]_])cloudflared([^[:alnum:]_]|$)' "$compose"; then
    fail 'shared Cloudflare connector must not be owned by CV Compose'
fi
if grep -Fq 'CF_TUNNEL_TOKEN' "$compose" || grep -Fq 'TUNNEL_TOKEN' "$compose"; then
    fail 'Cloudflare tunnel token dependency must not be owned by CV Compose'
fi

index=''
for candidate in index.html html/index.html site/index.html public/index.html; do
    if [[ -s "$ROOT/$candidate" ]]; then
        index="$ROOT/$candidate"
        break
    fi
done
[[ -n "$index" ]] || fail 'index.html not found in a supported source layout'
grep -Fq 'Andris Ro' "$index" || fail 'index.html does not identify Andris Rožkalns'

python_count=0
while IFS= read -r -d '' python_file; do
    PYTHONPYCACHEPREFIX="$VALIDATION_TMP/pycache" \
        python3 -m py_compile "$python_file"
    python_count=$((python_count + 1))
done < <(
    find "$ROOT/bot" "$ROOT/scripts" "$ROOT/tests" \
        -type f -name '*.py' -print0
)
(( python_count > 0 )) || fail 'no Python source files were validated'

while IFS= read -r -d '' script; do
    bash -n "$script"
done < <(find "$ROOT/scripts" "$ROOT/runner" -type f -name '*.sh' -print0)

while IFS= read -r -d '' secret_file; do
    case "$(basename "$secret_file")" in
        .env.example|*.env.example) ;;
        *) fail "forbidden env file in repository: ${secret_file#$ROOT/}" ;;
    esac
done < <(find "$ROOT" -type f \( -name '.env' -o -name '*.env' \) -print0)

python3 "$ROOT/scripts/secret-scan.py" "$ROOT"
python3 "$ROOT/scripts/build-content.py" --check
python3 "$ROOT/scripts/sync-system-prompt.py" --check

if [[ -d "$ROOT/bot/data" ]] \
   && find "$ROOT/bot/data" -type f ! -name '.gitkeep' -print -quit \
      | grep -q .; then
    fail 'runtime CV assistant data must not be versioned'
fi

create_placeholder() {
    local path="$1"
    local content="${2:-}"
    if [[ ! -e "$path" ]]; then
        install -d -m 0700 "$(dirname -- "$path")"
        printf '%s' "$content" >"$path"
        chmod 0600 "$path"
        created_placeholders+=("$path")
    fi
}

if grep -Fqs 'bot/.env' "$compose"; then
    create_placeholder "$ROOT/bot/.env"
fi

(
    cd "$ROOT"
    resolved="$(docker compose config)"
    docker compose config --quiet
    services="$(docker compose config --services)"
    grep -qx 'cv' <<<"$services" || fail 'Compose service cv is missing'
    grep -qx 'cvbot' <<<"$services" || fail 'Compose service cvbot is missing'
    [[ "$(wc -l <<<"$services" | tr -d '[:space:]')" == 2 ]] \
        || fail 'Compose must contain exactly the two CV-owned services'
    if grep -qx 'cloudflared' <<<"$services"; then
        fail 'shared Cloudflare connector must not be a CV Compose service'
    fi
    grep -Fq "name: $NETWORK_NAME" <<<"$resolved" \
        || fail 'effective Compose network name is not cv_default'
    grep -Fq "subnet: $NETWORK_SUBNET" <<<"$resolved" \
        || fail 'effective Compose subnet is not pinned'
    grep -Fq "gateway: $NETWORK_GATEWAY" <<<"$resolved" \
        || fail 'effective Compose gateway is not pinned'
)

if generated="$(find_generated_artifact)" && [[ -n "$generated" ]]; then
    fail "validation dirtied source tree: ${generated#$ROOT/}"
fi

printf 'PYTHON_SOURCE_COUNT=%s\n' "$python_count"
printf 'SOURCE_VALIDATION=PASS\n'
