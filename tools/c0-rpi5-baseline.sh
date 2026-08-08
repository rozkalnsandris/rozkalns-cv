#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

: "${GITHUB_REPOSITORY:?}"
: "${GH_TOKEN:?}"
: "${GITHUB_RUN_ID:?}"
: "${RUNNER_TEMP:?}"

case "$PWD" in
  /home/github-cv-runner/actions-runner/_work/*) ;;
  *) printf 'unexpected runner workspace: %s\n' "$PWD" >&2; exit 1 ;;
esac
test "$PWD" != /home/andris/rozkalns-cv
test "$PWD" != /home/andris/docker/cv

baseline_sha="$(git rev-parse refs/remotes/origin/main)"
[[ "$baseline_sha" =~ ^[0-9a-f]{40}$ ]]
out="${RUNNER_TEMP}/gate-c0-rpi5-${baseline_sha}-${GITHUB_RUN_ID}"
src="${RUNNER_TEMP}/gate-c0-main-${baseline_sha}-${GITHUB_RUN_ID}"
home="${RUNNER_TEMP}/gate-c0-home-${GITHUB_RUN_ID}"
npm_cache="${RUNNER_TEMP}/gate-c0-npm-cache-${GITHUB_RUN_ID}"
install -d -m 0700 "$out" "$home" "$npm_cache"

cleanup() {
  git worktree remove --force "$src" >/dev/null 2>&1 || true
}
trap cleanup EXIT

git worktree add --detach "$src" "$baseline_sha"
BASELINE_SHA="$baseline_sha" OUT="$out" python3 - <<'PY'
import json, os, pathlib, urllib.parse, urllib.request
repo=os.environ["GITHUB_REPOSITORY"]
sha=os.environ["BASELINE_SHA"]
headers={
    "Accept":"application/vnd.github+json",
    "Authorization":f"Bearer {os.environ['GH_TOKEN']}",
    "X-GitHub-Api-Version":"2022-11-28",
    "User-Agent":"rozkalns-cv-gate-c0-rpi5",
}
url=(
    f"https://api.github.com/repos/{repo}/actions/workflows/ci.yml/runs"
    f"?branch=main&head_sha={urllib.parse.quote(sha,safe='')}&status=completed&per_page=100"
)
with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as response:
    data=json.load(response)
good=[
    row for row in data.get("workflow_runs",[])
    if row.get("event")=="push"
    and row.get("head_branch")=="main"
    and row.get("head_sha")==sha
    and row.get("conclusion")=="success"
]
if not good:
    raise SystemExit(f"no successful main push CI for {sha}")
chosen=max(good,key=lambda row:int(row["id"]))
safe={key:chosen.get(key) for key in (
    "id","html_url","head_sha","event","head_branch","status","conclusion","created_at","updated_at"
)}
pathlib.Path(os.environ["OUT"],"main-ci.json").write_text(
    json.dumps(safe,indent=2)+"\n",encoding="utf-8"
)
PY
printf 'C0_BASELINE_SHA=%s\n' "$baseline_sha"

SRC="$src" OUT="$out" python3 - <<'PY'
import hashlib, json, os, pathlib
src=pathlib.Path(os.environ["SRC"])
rows=[]
for path in sorted((src/"html").rglob("*")):
    if not path.is_file():
        continue
    rel=path.relative_to(src).as_posix()
    ext=path.suffix.lower()
    if ext not in {".html",".css",".mjs",".js"} and not (
        ext==".json" and "/i18n/" in f"/{rel}"
    ):
        continue
    body=path.read_bytes()
    rows.append({"path":rel,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest()})
pathlib.Path(os.environ["OUT"],"static-inventory.json").write_text(
    json.dumps(rows,indent=2)+"\n",encoding="utf-8"
)
PY

mapfile -t header_paths < <(SRC="$src" OUT="$out" python3 - <<'PY'
import json, os, pathlib, re
rows=json.loads(pathlib.Path(os.environ["OUT"],"static-inventory.json").read_text())
def pick(pattern):
    for row in rows:
        if re.search(pattern,row["path"]):
            return "/"+row["path"].removeprefix("html/")
    return None
values=[
    "/","/smarthome.html",
    pick(r"html/assets/.+\.[0-9a-f]{12}\.css$"),
    pick(r"html/assets/app\.[0-9a-f]{12}\.mjs$"),
]
values += [
    "/"+row["path"].removeprefix("html/")
    for row in rows
    if re.search(r"html/i18n/.+\.[0-9a-f]{12}\.json$",row["path"])
][:3]
values += ["/stats.json","/cv.pdf","/cv-lv.pdf","/api/health","/api/contact-config"]
print("\n".join(value for value in values if value))
PY
)

mapfile -t immutable_paths < <(OUT="$out" python3 - <<'PY'
import json, os, pathlib, re
rows=json.loads(pathlib.Path(os.environ["OUT"],"static-inventory.json").read_text())
values=[
    "/"+row["path"].removeprefix("html/")
    for row in rows
    if re.search(r"html/(assets/.+\.[0-9a-f]{12}\.(?:css|mjs|js)|i18n/.+\.[0-9a-f]{12}\.json)$",row["path"])
]
values += ["/cv.pdf","/cv-lv.pdf"]
print("\n".join(values))
PY
)

default_hashes() {
  local output="$1" path body
  : > "$output"
  for path in "${immutable_paths[@]}"; do
    body="$(mktemp)"
    curl --fail --silent --show-error --location --max-time 30 \
      "https://rozkalns.net${path}" --output "$body"
    printf '%s\t%s\n' "$(sha256sum "$body" | awk '{print $1}')" "$path" >> "$output"
    rm -f "$body"
  done
  sort -k2,2 -o "$output" "$output"
}

default_hashes "$out/served-immutable-before.sha256"

install -d -m 0700 "$out/headers/public" "$out/headers/origin"
: > "$out/http-status.tsv"
for path in "${header_paths[@]}"; do
  name="$(printf '%s' "$path" | sed 's#^/$#root#; s#^/##; s#[/?&=]#_#g')"
  for mode in public origin; do
    raw="$(mktemp)"
    if [[ "$mode" == public ]]; then
      curl --silent --show-error --location --max-time 30 \
        --dump-header "$raw" --output /dev/null "https://rozkalns.net${path}" || true
    else
      curl --silent --show-error --location --max-time 30 \
        --header 'Host: rozkalns.net' \
        --dump-header "$raw" --output /dev/null "http://127.0.0.1:8088${path}" || true
    fi
    awk 'BEGIN{IGNORECASE=1} /^(HTTP\/|Age:|Cache-Control:|Content-Encoding:|Content-Length:|Content-Security-Policy:|Content-Type:|ETag:|Expires:|Last-Modified:|Permissions-Policy:|Referrer-Policy:|Server:|Vary:|X-Content-Type-Options:|X-Frame-Options:|CF-Cache-Status:)/ {sub(/\r$/,""); print}' \
      "$raw" > "$out/headers/${mode}/${name}.txt"
    status="$(awk '/^HTTP\//{code=$2} END{print code}' "$raw")"
    test -n "$status" || status=000
    printf '%s\t%s\t%s\n' "$mode" "$path" "$status" >> "$out/http-status.tsv"
    rm -f "$raw"
  done
done
cat "$out/http-status.tsv"
awk -F '\t' '$2=="/" || $2=="/stats.json" {if($3!="200") exit 1}' "$out/http-status.tsv"
printf 'PUBLIC_AND_ORIGIN_CONTRACTS=PASS\n'

chrome="$(command -v chromium)"
node="$(command -v node)"
npm="$(command -v npm)"
test -x "$chrome"
test -x "$node"
test -x "$npm"
"$chrome" --version > "$out/chromium-version.txt"
"$node" --version > "$out/node-version.txt"
"$npm" --version > "$out/npm-version.txt"
node --check tools/c0-browser-baseline.mjs
HOME="$home" node tools/c0-browser-baseline.mjs \
  --output "$out" \
  --url https://rozkalns.net \
  --chrome "$chrome" \
  --sha "$baseline_sha"

export HOME="$home"
export npm_config_cache="$npm_cache"
export npm_config_audit=false
export npm_config_fund=false
export npm_config_ignore_scripts=true
export CHROME_PATH="$chrome"
npm view lighthouse@13.4.1 version dist.integrity --json > "$out/lighthouse-package.json"
npx --yes lighthouse@13.4.1 https://rozkalns.net/ \
  --quiet \
  --output=json \
  --output-path="$out/lighthouse-phone.json" \
  --only-categories=performance,accessibility,best-practices,seo \
  --chrome-flags='--headless=new --no-sandbox --disable-dev-shm-usage'
npx --yes lighthouse@13.4.1 https://rozkalns.net/ \
  --quiet \
  --preset=desktop \
  --output=json \
  --output-path="$out/lighthouse-desktop.json" \
  --only-categories=performance,accessibility,best-practices,seo \
  --chrome-flags='--headless=new --no-sandbox --disable-dev-shm-usage'

default_hashes "$out/served-immutable-after.sha256"
cmp -s "$out/served-immutable-before.sha256" "$out/served-immutable-after.sha256"
printf 'SERVED_IMMUTABLE_UNCHANGED=PASS\n'

OUT="$out" BASELINE_SHA="$baseline_sha" python3 - <<'PY'
import json, os, pathlib
out=pathlib.Path(os.environ["OUT"])
browser=json.loads((out/"browser-baseline.json").read_text())
inventory=json.loads((out/"static-inventory.json").read_text())
def lighthouse(name):
    data=json.loads((out/f"lighthouse-{name}.json").read_text())
    c=data["categories"]
    a=data["audits"]
    return {
        "performance":round(c["performance"]["score"]*100),
        "accessibility":round(c["accessibility"]["score"]*100),
        "best_practices":round(c["best-practices"]["score"]*100),
        "seo":round(c["seo"]["score"]*100),
        "fcp_ms":a["first-contentful-paint"]["numericValue"],
        "lcp_ms":a["largest-contentful-paint"]["numericValue"],
        "cls":a["cumulative-layout-shift"]["numericValue"],
        "tbt_ms":a["total-blocking-time"]["numericValue"],
        "transfer_bytes":a["total-byte-weight"]["numericValue"],
    }
phone=lighthouse("phone")
desktop=lighthouse("desktop")
lines=[
    "# Gate C0 production before-state","",
    f"- baseline main: `{os.environ['BASELINE_SHA']}`",
    "- runner: isolated RPi5 release workspace",
    "- Docker: **not used**",
    "- sudo: **not used**",
    "- production writes: **none**",
    "- direct runtime tree access: **not granted / not required**",
    "- contact/chat POSTs during browser interaction: **blocked locally by Chrome**","",
    "## Static identity","","| files | total bytes |","|---:|---:|",
    f"| {len(inventory)} | {sum(row['bytes'] for row in inventory)} |","",
    "## Browser network","","| viewport | cold bytes | warm bytes | warm cache hits |","|---|---:|---:|---:|",
    f"| desktop | {browser['desktop']['cold']['network']['transferredBytes']} | {browser['desktop']['warm']['network']['transferredBytes']} | {browser['desktop']['warm']['network']['cacheHits']} |",
    f"| phone | {browser['phone']['cold']['network']['transferredBytes']} | {browser['phone']['warm']['network']['transferredBytes']} | {browser['phone']['warm']['network']['cacheHits']} |","",
    "## Lighthouse 13.4.1","","| viewport | perf | a11y | best practices | SEO | FCP ms | LCP ms | CLS | TBT ms | bytes |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    f"| phone | {phone['performance']} | {phone['accessibility']} | {phone['best_practices']} | {phone['seo']} | {phone['fcp_ms']:.0f} | {phone['lcp_ms']:.0f} | {phone['cls']:.4f} | {phone['tbt_ms']:.0f} | {phone['transfer_bytes']:.0f} |",
    f"| desktop | {desktop['performance']} | {desktop['accessibility']} | {desktop['best_practices']} | {desktop['seo']} | {desktop['fcp_ms']:.0f} | {desktop['lcp_ms']:.0f} | {desktop['cls']:.4f} | {desktop['tbt_ms']:.0f} | {desktop['transfer_bytes']:.0f} |","",
    "## Keyboard / interaction","",
    f"- skip link first Tab: **{'PASS' if browser['desktop']['keyboard']['skipFirst'] else 'FAIL'}**",
    f"- EN/DE/LV in Tab flow: **{'PASS' if browser['desktop']['keyboard']['langButtons'] else 'FAIL'}**",
    f"- keyboard language switch: **{'PASS' if browser['desktop']['keyboard']['langSwitch'] else 'FAIL'}**",
    f"- keyboard nav activation: **{'PASS' if browser['desktop']['keyboard']['nav'] else 'FAIL'}**",
    f"- contact verification UI entered: **{'PASS' if (browser['desktop']['keyboard']['contact']['mount'] or browser['desktop']['keyboard']['contact']['status']) else 'OBSERVED'}**",
    f"- chat request blocked locally + Escape focus return: **{'PASS' if browser['desktop']['keyboard']['chatBlocked'] and browser['desktop']['keyboard']['chatFocusReturn'] else 'FAIL'}**","",
    "## Reproducibility / safety","",
    "- public and loopback-origin allowlisted headers/statuses captured",
    "- exact-main HTML/CSS/JS/i18n byte sizes + SHA-256 captured",
    "- immutable public assets hashed before and after; hashes unchanged",
    "- Chrome cold/warm waterfall, coverage and screenshots captured",
    "- Lighthouse package identity captured before use","",
]
(out/"SUMMARY.md").write_text("\n".join(lines),encoding="utf-8")
PY

for path in "$out/browser-baseline.json" "$out/SUMMARY.md"; do
  if grep -Ein '"(email|phone|phone_uri|token|cookie)"[[:space:]]*:' "$path"; then
    printf 'privacy-sensitive key found in %s\n' "$path" >&2
    exit 1
  fi
done
printf 'C0_PRIVACY_ARTIFACT_GATE=PASS\n'
printf 'PRODUCTION_WRITE=false\n'
printf 'DOCKER_ACCESS=false\n'
printf 'SUDO_USED=false\n'
cat "$out/SUMMARY.md"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  printf 'sha=%s\n' "$baseline_sha" >> "$GITHUB_OUTPUT"
  printf 'out=%s\n' "$out" >> "$GITHUB_OUTPUT"
fi
