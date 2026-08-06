from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_stats_http", ROOT / "scripts" / "generate-stats.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PrometheusClientTests(unittest.TestCase):
    def successful_payload(self) -> str:
        return json.dumps(
            {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [{"value": [1_700_000_000, "12.5"]}],
                },
            }
        )

    def test_curl_uses_bounded_connect_and_total_timeouts(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=self.successful_payload(), stderr=""
        )
        client = MODULE.PrometheusClient(
            MODULE.HttpConfig(
                base_url="http://prometheus:9090",
                connect_timeout=2.0,
                total_timeout=7.0,
                attempts=1,
            )
        )
        with patch.object(
            MODULE.subprocess, "run", return_value=completed
        ) as mocked:
            self.assertEqual(client.scalar("up"), 12.5)
        command = mocked.call_args.args[0]
        self.assertIn("--fail", command)
        self.assertEqual(command[command.index("--connect-timeout") + 1], "2.0")
        self.assertEqual(command[command.index("--max-time") + 1], "7.0")
        self.assertIn("query=up", command)
        self.assertEqual(mocked.call_args.kwargs["timeout"], 9.0)

    def test_transient_timeout_is_retried_with_a_bound(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=self.successful_payload(), stderr=""
        )
        client = MODULE.PrometheusClient(
            MODULE.HttpConfig(
                base_url="http://prometheus:9090",
                attempts=3,
                retry_delay=0,
            )
        )
        with patch.object(
            MODULE.subprocess,
            "run",
            side_effect=[
                subprocess.TimeoutExpired("curl", 10),
                subprocess.TimeoutExpired("curl", 10),
                completed,
            ],
        ) as mocked:
            self.assertEqual(client.scalar("up"), 12.5)
        self.assertEqual(mocked.call_count, 3)

    def test_all_failed_attempts_raise_stats_error(self) -> None:
        client = MODULE.PrometheusClient(
            MODULE.HttpConfig(
                base_url="http://prometheus:9090",
                attempts=2,
                retry_delay=0,
            )
        )
        with patch.object(
            MODULE.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired("curl", 10),
        ):
            with self.assertRaises(MODULE.StatsError):
                client.scalar("up")


if __name__ == "__main__":
    unittest.main()
