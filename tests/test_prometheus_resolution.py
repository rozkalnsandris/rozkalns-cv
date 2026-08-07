from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "resolve_prometheus", ROOT / "scripts" / "resolve-prometheus.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrometheusResolutionTests(unittest.TestCase):
    def test_concrete_ipv4_binding_is_used_directly(self) -> None:
        self.assertEqual(
            MODULE.endpoint_from_docker_output("192.168.0.180:9090\n"),
            "http://192.168.0.180:9090",
        )

    def test_ipv4_wildcard_binding_maps_to_loopback(self) -> None:
        self.assertEqual(
            MODULE.endpoint_from_docker_output("0.0.0.0:9090\n"),
            "http://127.0.0.1:9090",
        )

    def test_ipv6_binding_is_rendered_with_brackets(self) -> None:
        self.assertEqual(
            MODULE.endpoint_from_docker_output("[fd00::10]:9090\n"),
            "http://[fd00::10]:9090",
        )

    def test_ambiguous_distinct_bindings_fail_closed(self) -> None:
        with self.assertRaises(MODULE.ResolutionError):
            MODULE.endpoint_from_docker_output(
                "192.168.0.180:9090\n127.0.0.1:9090\n"
            )

    def test_empty_binding_fails_closed(self) -> None:
        with self.assertRaises(MODULE.ResolutionError):
            MODULE.endpoint_from_docker_output("")

    def test_override_is_normalized_and_credentials_are_rejected(self) -> None:
        self.assertEqual(
            MODULE.normalize_url("http://192.168.0.180:9090/"),
            "http://192.168.0.180:9090",
        )
        with self.assertRaises(MODULE.ResolutionError):
            MODULE.normalize_url("http://user:pass@192.168.0.180:9090")

    def test_wrapper_requires_readiness_before_generation(self) -> None:
        wrapper = (ROOT / "stats.sh").read_text(encoding="utf-8")
        self.assertIn('scripts/resolve-prometheus.py', wrapper)
        self.assertIn('PROMETHEUS_URL_RESOLVED', wrapper)
        self.assertIn('/-/ready', wrapper)
        self.assertIn('--prometheus "$PROMETHEUS_URL_RESOLVED"', wrapper)


if __name__ == "__main__":
    unittest.main()
