#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Callable


PROMQL = {
    "uptime_30d": 'avg(avg_over_time(up{job="node"}[30d])) * 100',
    "services": 'count(up{job!=""} == 1)',
    "cpu_temp": 'avg(node_thermal_zone_temp)',
    "cpu_temp_fallback": 'avg(node_hwmon_temp_celsius)',
    "days_online": 'avg(node_time_seconds - node_boot_time_seconds) / 86400',
    "cpu_usage": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
    "ram_usage": 'avg((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100)',
    "disk_usage": '100 * (1 - (sum(node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}) / sum(node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"})))',
    "load1": 'avg(node_load1)',
    "net_down": 'sum(rate(node_network_receive_bytes_total{device=~"eth0|enp.*|end.*"}[5m])) * 8 / 1e6',
    "net_up": 'sum(rate(node_network_transmit_bytes_total{device=~"eth0|enp.*|end.*"}[5m])) * 8 / 1e6',
}

DECIMALS = {
    "uptime_30d": 1,
    "services": 0,
    "docker_containers": 0,
    "docker_images": 0,
    "cpu_temp": 1,
    "days_online": 0,
    "cpu_usage": 1,
    "ram_usage": 1,
    "disk_usage": 1,
    "load1": 2,
    "net_down": 1,
    "net_up": 1,
}


class StatsError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpConfig:
    base_url: str
    connect_timeout: float = 3.0
    total_timeout: float = 8.0
    attempts: int = 3
    retry_delay: float = 0.5


class PrometheusClient:
    def __init__(self, config: HttpConfig) -> None:
        if config.attempts <= 0:
            raise ValueError("attempts must be positive")
        self.config = config

    def scalar(self, query: str) -> float | None:
        command = [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--connect-timeout",
            str(self.config.connect_timeout),
            "--max-time",
            str(self.config.total_timeout),
            "--get",
            "--data-urlencode",
            f"query={query}",
            f"{self.config.base_url.rstrip('/')}/api/v1/query",
        ]
        last_error: Exception | None = None
        for attempt in range(1, self.config.attempts + 1):
            try:
                completed = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.config.total_timeout + 2,
                )
                payload = json.loads(completed.stdout)
                return parse_prometheus_scalar(payload)
            except Exception as error:
                last_error = error
                if attempt < self.config.attempts:
                    time.sleep(self.config.retry_delay)
        raise StatsError(
            f"Prometheus query failed after {self.config.attempts} attempts: "
            f"{type(last_error).__name__}"
        ) from last_error


def parse_prometheus_scalar(payload: object) -> float | None:
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise StatsError("Prometheus response status is not success")
    data = payload.get("data")
    if not isinstance(data, dict) or data.get("resultType") != "vector":
        raise StatsError("Prometheus response is not a vector")
    result = data.get("result")
    if not isinstance(result, list):
        raise StatsError("Prometheus result is not a list")
    if not result:
        return None
    if len(result) != 1:
        raise StatsError("Prometheus query returned multiple series")
    row = result[0]
    if not isinstance(row, dict):
        raise StatsError("Prometheus result row is invalid")
    value = row.get("value")
    if not isinstance(value, list) or len(value) != 2:
        raise StatsError("Prometheus scalar value is invalid")
    try:
        number = float(value[1])
    except (TypeError, ValueError) as error:
        raise StatsError("Prometheus value is not numeric") from error
    if not math.isfinite(number):
        raise StatsError("Prometheus value is not finite")
    return number


def docker_count(command: list[str]) -> int:
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    values = {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    }
    return len(values)


def rounded(value: float | int | None, digits: int) -> float | int | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        raise StatsError("snapshot contains non-finite number")
    if digits == 0:
        return int(round(number))
    return round(number, digits)


def build_snapshot(
    scalar: Callable[[str], float | None],
    docker_counter: Callable[[list[str]], int],
    *,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, object]:
    values: dict[str, float | int | None] = {}
    for key, query in PROMQL.items():
        if key == "cpu_temp_fallback":
            continue
        values[key] = scalar(query)
    if values["cpu_temp"] is None:
        values["cpu_temp"] = scalar(PROMQL["cpu_temp_fallback"])

    values["docker_containers"] = docker_counter(["docker", "ps", "-q"])
    values["docker_images"] = docker_counter(["docker", "images", "-q"])

    timestamp = now()
    if timestamp.tzinfo is None:
        raise StatsError("snapshot timestamp must be timezone-aware")
    snapshot: dict[str, object] = {
        "updated": timestamp.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    }
    for key in (
        "uptime_30d",
        "services",
        "docker_containers",
        "docker_images",
        "cpu_temp",
        "days_online",
        "cpu_usage",
        "ram_usage",
        "disk_usage",
        "load1",
        "net_down",
        "net_up",
    ):
        snapshot[key] = rounded(values[key], DECIMALS[key])
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: object) -> None:
    if not isinstance(snapshot, dict):
        raise StatsError("snapshot must be an object")
    expected = {"updated", *DECIMALS.keys()}
    if set(snapshot) != expected:
        raise StatsError("snapshot fields do not match the schema")
    updated = snapshot.get("updated")
    if not isinstance(updated, str) or not updated.endswith("Z"):
        raise StatsError("updated must be an RFC3339 UTC string")
    try:
        parsed = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    except ValueError as error:
        raise StatsError("updated timestamp is invalid") from error
    if parsed.tzinfo is None:
        raise StatsError("updated timestamp lacks a timezone")
    for key, digits in DECIMALS.items():
        value = snapshot.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise StatsError(f"{key} is not numeric or null")
        if not math.isfinite(float(value)):
            raise StatsError(f"{key} is not finite")
        if digits == 0 and not isinstance(value, int):
            raise StatsError(f"{key} must be an integer")


def atomic_write_json(output: Path, snapshot: dict[str, object]) -> None:
    validate_snapshot(snapshot)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                snapshot,
                handle,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        loaded = json.loads(temporary.read_text(encoding="utf-8"))
        validate_snapshot(loaded)
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
        directory_fd = os.open(output.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument(
        "--output", default="/home/andris/docker/cv/html/stats.json"
    )
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--connect-timeout", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--lock", default="/run/lock/rozkalns-cv-stats.lock"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    lock_path = Path(args.lock)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("STATS_RESULT=SKIP_ALREADY_RUNNING")
            return 0

        client = PrometheusClient(
            HttpConfig(
                base_url=args.prometheus,
                connect_timeout=args.connect_timeout,
                attempts=args.attempts,
                total_timeout=args.timeout,
            )
        )
        snapshot = build_snapshot(client.scalar, docker_count)
        atomic_write_json(output, snapshot)
        print(f"STATS_RESULT=PASS OUTPUT={output}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
