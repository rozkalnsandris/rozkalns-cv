from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_stats", ROOT / "scripts" / "generate-stats.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class StatsGeneratorTests(unittest.TestCase):
    def payload(self, values):
        return {
            "status": "success",
            "data": {"resultType": "vector", "result": values},
        }

    def test_parse_one_scalar(self) -> None:
        value = MODULE.parse_prometheus_scalar(
            self.payload([{"value": [1_700_000_000, "12.5"]}])
        )
        self.assertEqual(value, 12.5)

    def test_empty_result_is_null(self) -> None:
        self.assertIsNone(MODULE.parse_prometheus_scalar(self.payload([])))

    def test_multiple_series_are_rejected(self) -> None:
        with self.assertRaises(MODULE.StatsError):
            MODULE.parse_prometheus_scalar(
                self.payload(
                    [
                        {"value": [1, "1"]},
                        {"value": [1, "2"]},
                    ]
                )
            )

    def test_nan_and_malformed_values_are_rejected(self) -> None:
        for payload in (
            self.payload([{"value": [1, "NaN"]}]),
            self.payload([{"value": [1]}]),
            {"status": "error"},
            "not-an-object",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(MODULE.StatsError):
                    MODULE.parse_prometheus_scalar(payload)

    def test_build_snapshot_is_complete_and_deterministic(self) -> None:
        values = iter(
            [99.95, 14, 50.1, 20.2, 8.3, 42.4, 55.5, 12.345, 1.2, 0.4]
        )

        def scalar(query: str):
            return next(values)

        def docker_counter(command):
            return 7 if command[1] == "ps" else 11

        snapshot = MODULE.build_snapshot(
            scalar,
            docker_counter,
            now=lambda: datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(snapshot["updated"], "2026-08-06T12:00:00Z")
        self.assertEqual(snapshot["services"], 14)
        self.assertEqual(snapshot["docker_containers"], 7)
        self.assertEqual(snapshot["docker_images"], 11)
        self.assertEqual(snapshot["load1"], 12.35)
        MODULE.validate_snapshot(snapshot)

    def test_cpu_temperature_fallback_is_used_only_when_empty(self) -> None:
        calls = []

        def scalar(query: str):
            calls.append(query)
            if query == MODULE.PROMQL["cpu_temp"]:
                return None
            if query == MODULE.PROMQL["cpu_temp_fallback"]:
                return 51.25
            return 1.0

        snapshot = MODULE.build_snapshot(
            scalar,
            lambda command: 1,
            now=lambda: datetime(2026, 8, 6, tzinfo=timezone.utc),
        )
        self.assertEqual(snapshot["cpu_temp"], 51.2)
        self.assertIn(MODULE.PROMQL["cpu_temp_fallback"], calls)

    def test_atomic_write_preserves_previous_file_on_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "stats.json"
            output.write_text('{"previous": true}\n', encoding="utf-8")
            with self.assertRaises(MODULE.StatsError):
                MODULE.atomic_write_json(output, {"updated": "bad"})
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                '{"previous": true}\n',
            )

    def test_atomic_write_publishes_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "stats.json"
            snapshot = {"updated": "2026-08-06T12:00:00Z"}
            for key, digits in MODULE.DECIMALS.items():
                snapshot[key] = 1 if digits == 0 else 1.0
            MODULE.atomic_write_json(output, snapshot)
            loaded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(loaded, snapshot)
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
