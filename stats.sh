#!/usr/bin/env bash
set -euo pipefail
PROM="http://127.0.0.1:9090"
OUT="/home/andris/docker/cv/html/stats.json"
NODE_DEV_REGEX='eth0'
q() {
  local query="$1" val
  val=$(curl -s -G "${PROM}/api/v1/query" \
          --data-urlencode "query=${query}" \
        | jq -r '.data.result[0].value[1] // empty' 2>/dev/null || true)
  echo "${val}"
}
round() {
  local v="$1" d="${2:-1}"
  [ -z "$v" ] && { echo ""; return; }
  awk -v v="$v" -v d="$d" 'BEGIN{ if(v=="") print ""; else printf "%.*f", d, v }'
}
UPTIME=$(round "$(q 'avg_over_time(up{job="node"}[30d]) * 100')" 1)
[ -z "$UPTIME" ] && UPTIME=$(round "$(q 'avg_over_time(up[30d]) * 100')" 1)
SERVICES=$(round "$(q 'count(up == 1)')" 0)
CPU_TEMP=$(round "$(q 'node_thermal_zone_temp')" 1)
[ -z "$CPU_TEMP" ] && CPU_TEMP=$(round "$(q 'avg(node_hwmon_temp_celsius)')" 1)
DAYS=$(round "$(q '(node_time_seconds - node_boot_time_seconds) / 86400')" 0)
CPU_USAGE=$(round "$(q '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')" 1)
RAM_USAGE=$(round "$(q '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100')" 1)
DISK_USAGE=$(round "$(q '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100')" 1)
LOAD1=$(round "$(q 'node_load1')" 2)
NET_DOWN=$(round "$(q "sum(rate(node_network_receive_bytes_total{device=~\"${NODE_DEV_REGEX}\"}[5m])) * 8 / 1e6")" 1)
NET_UP=$(round "$(q "sum(rate(node_network_transmit_bytes_total{device=~\"${NODE_DEV_REGEX}\"}[5m])) * 8 / 1e6")" 1)
# --- Docker skaitītāji (droši pret set -e) ---
DOCKER_CONTAINERS=$(docker ps -q 2>/dev/null | wc -l | tr -d ' ' || echo 0)
DOCKER_IMAGES=$(docker images -q 2>/dev/null | sort -u | wc -l | tr -d ' ' || echo 0)
[ -z "$DOCKER_CONTAINERS" ] && DOCKER_CONTAINERS=0
[ -z "$DOCKER_IMAGES" ] && DOCKER_IMAGES=0
NOW=$(date --iso-8601=seconds)
TMP="$(mktemp)"
cat > "$TMP" <<ENDJSON
{
  "updated": "${NOW}",
  "uptime_30d": ${UPTIME:-null},
  "services": ${SERVICES:-null},
  "docker_containers": ${DOCKER_CONTAINERS:-null},
  "docker_images": ${DOCKER_IMAGES:-null},
  "cpu_temp": ${CPU_TEMP:-null},
  "days_online": ${DAYS:-null},
  "cpu_usage": ${CPU_USAGE:-null},
  "ram_usage": ${RAM_USAGE:-null},
  "disk_usage": ${DISK_USAGE:-null},
  "load1": ${LOAD1:-null},
  "net_down": ${NET_DOWN:-null},
  "net_up": ${NET_UP:-null}
}
ENDJSON
mv "$TMP" "$OUT"
chmod 644 "$OUT"
echo "[stats.sh] wrote ${OUT} at ${NOW}"
