#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

ROOT="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ -d "$ROOT" ]] || fail "repository root is missing: $ROOT"

for required in \
    README.md \
    .gitignore \
    scripts/validate-source.sh \
    .github/workflows/ci.yml \
    .github/workflows/deploy-main.yml
do
    [[ -s "$ROOT/$required" ]] || fail "required file is missing or empty: $required"
done

compose=''
for candidate in docker-compose.yml docker-compose.yaml compose.yml compose.yaml; do
    if [[ -s "$ROOT/$candidate" ]]; then
        compose="$ROOT/$candidate"
        break
    fi
done
[[ -n "$compose" ]] || fail 'no Docker Compose file found'

# Accept common historical layouts while requiring the real site and bot source.
index=''
for candidate in index.html html/index.html site/index.html public/index.html; do
    if [[ -s "$ROOT/$candidate" ]]; then
        index="$ROOT/$candidate"
        break
    fi
done
[[ -n "$index" ]] || fail 'index.html not found in a supported source layout'
grep -Fq 'Andris Ro' "$index" || fail 'index.html does not identify Andris Rožkalns'

bot=''
for candidate in bot/app.py app.py cvbot/app.py; do
    if [[ -s "$ROOT/$candidate" ]]; then
        bot="$ROOT/$candidate"
        break
    fi
done
[[ -n "$bot" ]] || fail 'CV assistant Python entry point not found'
python3 -m py_compile "$bot"

while IFS= read -r -d '' script; do
    bash -n "$script"
done < <(find "$ROOT/scripts" "$ROOT/runner" -type f -name '*.sh' -print0)

# Real secret files are forbidden.
while IFS= read -r -d '' secret_file; do
    case "$(basename "$secret_file")" in
        .env.example|cloudflared.env.example) ;;
        *) fail "forbidden env file in repository: ${secret_file#$ROOT/}" ;;
    esac
done < <(find "$ROOT" -type f \( -name '.env' -o -name '*.env' \) -print0)

python3 "$ROOT/scripts/secret-scan.py" "$ROOT"

# Runtime conversations can contain visitor questions, answers, timestamps,
# and network metadata. They belong only on the production host.
if [[ -d "$ROOT/bot/data" ]] \
   && find "$ROOT/bot/data" -type f ! -name '.gitkeep' -print -quit \
      | grep -q .; then
    fail 'runtime CV assistant data must not be versioned'
fi

# Compose references host-only env files that are intentionally excluded from
# Git. Create empty/dummy files only for validation, then always remove them.
# The resolved Compose configuration is never printed because it could expose
# values when this script is run on the production host.
created_placeholders=()
cleanup() {
    local placeholder
    for placeholder in "${created_placeholders[@]:-}"; do
        rm -f -- "$placeholder"
    done
}
trap cleanup EXIT

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

if grep -Fqs 'cloudflared.env' "$compose"; then
    create_placeholder         "$ROOT/cloudflared.env"         $'CF_TUNNEL_TOKEN=ci-placeholder-not-a-secret\n'
fi

# The current production Compose file loads the CV assistant configuration
# from bot/.env. It must remain host-only, but Docker Compose requires the file
# to exist even for a read-only `config` validation.
if grep -Fqs 'bot/.env' "$compose"; then
    create_placeholder "$ROOT/bot/.env"
fi

(
    cd "$ROOT"
    CF_TUNNEL_TOKEN='ci-placeholder-not-a-secret' docker compose config --quiet
    services="$(CF_TUNNEL_TOKEN='ci-placeholder-not-a-secret' docker compose config --services)"
    grep -qx 'cv' <<<"$services" || fail 'Compose service cv is missing'
    grep -qx 'cvbot' <<<"$services" || fail 'Compose service cvbot is missing'
)

printf 'SOURCE_VALIDATION=PASS\n'
