#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${1:-$(git rev-parse --show-toplevel)}"
GITLEAKS_IMAGE='ghcr.io/gitleaks/gitleaks:v8.30.0@sha256:691af3c7c5a48b16f187ce3446d5f194838f91238f27270ed36eef6359a574d9'

fail() {
    printf 'GITLEAKS_HISTORY_SCAN=FAIL reason=%s\n' "$1" >&2
    exit 1
}

[[ -d "$ROOT/.git" ]] || fail 'not-a-git-repository'
[[ -f "$ROOT/.gitleaks.toml" ]] || fail 'missing-config'
command -v docker >/dev/null 2>&1 || fail 'docker-not-available'

if [[ "$(git -C "$ROOT" rev-parse --is-shallow-repository)" == true ]]; then
    fail 'shallow-history'
fi

work="$(mktemp -d)"
canary_dir="$work/canary-scan"
fixture_root="$work/fixture-scan"
cleanup() {
    rm -rf -- "$work"
}
trap cleanup EXIT
chmod 0700 "$work"
install -d -m 0755 "$canary_dir" "$fixture_root"

# Build an upstream-rule canary only at runtime. The suffix is deterministic for
# repeatability but derived at runtime, so no complete token-shaped value exists
# in repository source. Scan ONLY the canary directory; scanner logs live outside
# it and therefore cannot become self-generated scan input.
python3 - "$canary_dir/canary.txt" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

suffix = hashlib.sha256(
    b"rozkalns-cv-gitleaks-upstream-canary-v1"
).hexdigest()[:36]
Path(sys.argv[1]).write_text(
    "GITHUB_TOKEN=\"" + "gh" + "p_" + suffix + "\"\n",
    encoding="utf-8",
)
PY
chmod 0444 "$canary_dir/canary.txt"

# The canary intentionally runs WITHOUT the project config. It independently
# proves that the embedded v8.30.0 default github-pat detector is functioning.
set +e
docker run --rm \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --user 65534:65534 \
    --mount "type=bind,src=$canary_dir,dst=/canary,readonly" \
    "$GITLEAKS_IMAGE" \
    dir --no-banner --redact /canary \
    >"$work/canary.stdout" 2>"$work/canary.stderr"
canary_status=$?
set -e

if [[ "$canary_status" -ne 1 ]]; then
    printf 'Unexpected Gitleaks canary status: %s\n' "$canary_status" >&2
    sed -n '1,80p' "$work/canary.stderr" >&2
    fail 'detector-canary-did-not-trigger'
fi
printf 'GITLEAKS_CANARY=PASS\n'

# Acceptance matrix for the project threat model. Every credential-shaped value
# is assembled at runtime from deterministic hashes/fragments; none of the full
# fixture secrets exist in Git source or history.
python3 - "$fixture_root" <<'PY'
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])


def hex_value(label: str, length: int = 48) -> str:
    material = hashlib.sha512(("rozkalns-cv:" + label).encode()).hexdigest()
    return material[:length]


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

aws_id = "AK" + "IA" + hashlib.sha256(b"rozkalns-cv:aws-id").hexdigest().upper()[:16]
private_payload = base64.b64encode(
    hashlib.sha512(b"rozkalns-cv:private-key").digest() * 3
).decode("ascii")
jwt_header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
jwt_payload = b64url(json.dumps({"sub": "fixture", "aud": "ci"}, separators=(",", ":")).encode())
jwt_signature = b64url(hashlib.sha256(b"rozkalns-cv:jwt-signature").digest())
password_key = "ADMIN_" + "PASSWORD"
database_prefix = "DATABASE_" + "URL=\"postgresql://cvuser:"

fixtures = {
    "cloudflare_tunnel": (
        "CF_TUNNEL_TOKEN=\""
        + ".".join(hex_value(f"tunnel-{index}", 24) for index in range(3))
        + "\"\n"
    ),
    "cloudflare_api": "CLOUDFLARE_API_TOKEN=\"" + hex_value("cloudflare-api", 40) + "\"\n",
    "aws": (
        "AWS_ACCESS_KEY_ID=\"" + aws_id + "\"\n"
        + "AWS_SECRET_ACCESS_KEY=\"" + hex_value("aws-secret", 40) + "\"\n"
    ),
    "private_key": (
        "-----BEGIN " + "RSA PRIVATE KEY-----\n"
        + private_payload + "\n"
        + "-----END " + "RSA PRIVATE KEY-----\n"
    ),
    "webhook": "WEBHOOK_SECRET=\"" + hex_value("webhook", 40) + "\"\n",
    "jwt": "AUTH_JWT=\"" + jwt_header + "." + jwt_payload + "." + jwt_signature + "\"\n",
    "password": password_key + "=\"" + hex_value("pass" + "word", 30) + "!\"\n",
    "database_url": (
        database_prefix
        + hex_value("database-" + "credential", 28)
        + "@db.internal/cv\"\n"
    ),
    "high_entropy": "GENERIC_API_KEY=\"" + b64url(hashlib.sha256(b"rozkalns-cv:entropy").digest()) + "\"\n",
}

for name, content in fixtures.items():
    directory = root / name
    directory.mkdir(mode=0o755)
    path = directory / "fixture.txt"
    path.write_text(content, encoding="utf-8")
    path.chmod(0o444)
PY

fixture_names=(
    cloudflare_tunnel
    cloudflare_api
    aws
    private_key
    webhook
    jwt
    password
    database_url
    high_entropy
)

for fixture_name in "${fixture_names[@]}"; do
    stdout="$work/fixture-${fixture_name}.stdout"
    stderr="$work/fixture-${fixture_name}.stderr"
    set +e
    docker run --rm \
        --network none \
        --read-only \
        --cap-drop ALL \
        --security-opt no-new-privileges \
        --user 65534:65534 \
        --mount "type=bind,src=$ROOT/.gitleaks.toml,dst=/config/gitleaks.toml,readonly" \
        --mount "type=bind,src=$fixture_root,dst=/fixtures,readonly" \
        "$GITLEAKS_IMAGE" \
        dir --no-banner --redact --config /config/gitleaks.toml "/fixtures/$fixture_name" \
        >"$stdout" 2>"$stderr"
    fixture_status=$?
    set -e
    if [[ "$fixture_status" -ne 1 ]]; then
        printf 'Unexpected Gitleaks fixture status: class=%s status=%s\n' \
            "$fixture_name" "$fixture_status" >&2
        sed -n '1,80p' "$stderr" >&2
        fail "fixture-${fixture_name}-did-not-trigger"
    fi
    printf 'GITLEAKS_FIXTURE_%s=PASS\n' \
        "$(printf '%s' "$fixture_name" | tr '[:lower:]' '[:upper:]')"
done
printf 'GITLEAKS_FIXTURE_MATRIX=PASS count=%s\n' "${#fixture_names[@]}"

report="$work/history.json"
set +e
docker run --rm \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$ROOT,dst=/repo,readonly" \
    --mount "type=bind,src=$work,dst=/output" \
    --workdir /repo \
    "$GITLEAKS_IMAGE" \
    git --no-banner --redact --config /repo/.gitleaks.toml \
    --log-opts='--all' --report-format json --report-path /output/history.json \
    /repo \
    >"$work/history.stdout" 2>"$work/history.stderr"
history_status=$?
set -e

if [[ "$history_status" -ne 0 ]]; then
    printf 'Gitleaks history scan returned status %s. Findings are redacted.\n' \
        "$history_status" >&2
    sed -n '1,120p' "$work/history.stderr" >&2
    if [[ -s "$report" ]]; then
        python3 - "$report" <<'PY' >&2
from __future__ import annotations

import json
from pathlib import Path
import sys

rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"GITLEAKS_FINDING_COUNT={len(rows)}")
for row in rows[:50]:
    print(
        "finding"
        f" rule={row.get('RuleID', 'unknown')}"
        f" file={row.get('File', 'unknown')}"
        f" line={row.get('StartLine', row.get('Line', 'unknown'))}"
        f" commit={row.get('Commit', 'working-tree')}"
    )
PY
    fi
    fail 'history-findings-or-scan-error'
fi

if [[ -s "$report" ]]; then
    python3 - "$report" <<'PY'
from pathlib import Path
import json
import sys

rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if rows:
    raise SystemExit("successful Gitleaks scan unexpectedly produced findings")
PY
fi

printf 'GITLEAKS_HISTORY_SCAN=PASS\n'
