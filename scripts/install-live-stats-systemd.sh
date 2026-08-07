#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 022

SERVICE='rozkalns-cv-stats.service'
TIMER='rozkalns-cv-stats.timer'
RUNTIME='/home/andris/docker/cv'
SOURCE_DIR="$RUNTIME/ops/systemd"
UNIT_DIR='/etc/systemd/system'
STATS_JSON="$RUNTIME/html/stats.json"
CRON_USER='andris'

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail 'run this installer with sudo'
[[ -d "$RUNTIME" && ! -L "$RUNTIME" ]] || fail "runtime is missing: $RUNTIME"
[[ -x "$RUNTIME/stats.sh" && ! -L "$RUNTIME/stats.sh" ]] || fail 'runtime stats.sh is missing or not executable'
[[ -f "$SOURCE_DIR/$SERVICE" && ! -L "$SOURCE_DIR/$SERVICE" ]] || fail "$SERVICE source is missing"
[[ -f "$SOURCE_DIR/$TIMER" && ! -L "$SOURCE_DIR/$TIMER" ]] || fail "$TIMER source is missing"
command -v systemctl >/dev/null 2>&1 || fail 'systemctl is unavailable'
command -v crontab >/dev/null 2>&1 || fail 'crontab is unavailable'
command -v python3 >/dev/null 2>&1 || fail 'python3 is unavailable'

install -o root -g root -m 0644 "$SOURCE_DIR/$SERVICE" "$UNIT_DIR/$SERVICE"
install -o root -g root -m 0644 "$SOURCE_DIR/$TIMER" "$UNIT_DIR/$TIMER"

# The systemd timer is the only canonical scheduler after migration. Remove only
# legacy CV stats cron commands while preserving every unrelated cron entry.
cron_before="$(mktemp)"
cron_after="$(mktemp)"
cleanup() {
  rm -f -- "$cron_before" "$cron_after"
}
trap cleanup EXIT

if crontab -u "$CRON_USER" -l >"$cron_before" 2>/dev/null; then
  python3 - "$cron_before" "$cron_after" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
patterns = (
    "/home/andris/docker/cv/stats.sh",
    "/home/andris/rozkalns-cv/stats.sh",
    "scripts/generate-stats.py",
)
kept: list[str] = []
removed: list[str] = []
for line in source.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and any(p in line for p in patterns):
        removed.append(line)
    else:
        kept.append(line)
destination.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
for row in removed:
    print(f"REMOVED_LEGACY_CRON={row}")
PY
  crontab -u "$CRON_USER" "$cron_after"
else
  : >"$cron_before"
fi

systemctl daemon-reload
systemctl enable --now "$TIMER"

# Run immediately rather than waiting for the next minute boundary. A failed
# generation leaves the previous valid stats.json untouched and aborts install.
systemctl start "$SERVICE" || {
  systemctl --no-pager --full status "$SERVICE" || true
  journalctl -u "$SERVICE" -n 80 --no-pager || true
  fail 'initial live stats refresh failed'
}

systemctl is-enabled --quiet "$TIMER" || fail 'timer is not enabled'
systemctl is-active --quiet "$TIMER" || fail 'timer is not active'
[[ -s "$STATS_JSON" && ! -L "$STATS_JSON" ]] || fail 'stats.json was not published'

python3 - "$STATS_JSON" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
updated = data.get("updated")
if not isinstance(updated, str) or not updated.endswith("Z"):
    raise SystemExit("stats updated timestamp is invalid")
timestamp = datetime.fromisoformat(updated.replace("Z", "+00:00"))
age = (datetime.now(timezone.utc) - timestamp).total_seconds()
if age < -30 or age > 120:
    raise SystemExit(f"stats are not fresh: age_seconds={age:.1f}")
required = (
    "uptime_30d",
    "docker_containers",
    "load1",
    "days_online",
    "cpu_usage",
    "ram_usage",
    "disk_usage",
    "cpu_temp",
)
missing = [key for key in required if key not in data]
if missing:
    raise SystemExit("stats fields are missing: " + ",".join(missing))
print(f"STATS_UPDATED={updated}")
print(f"STATS_AGE_SECONDS={age:.1f}")
for key in required:
    print(f"STATS_{key.upper()}={data[key]}")
PY

printf '\nLIVE_STATS_SYSTEMD_SETUP=PASS\n'
systemctl --no-pager --full status "$TIMER" | sed -n '1,12p'
systemctl --no-pager --full status "$SERVICE" | sed -n '1,16p' || true
