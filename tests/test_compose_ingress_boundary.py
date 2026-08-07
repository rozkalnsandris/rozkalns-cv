from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
README = ROOT / "README.md"


class ComposeIngressBoundaryTests(unittest.TestCase):
    def test_cv_publish_is_loopback_only(self) -> None:
        text = COMPOSE.read_text(encoding="utf-8")

        self.assertIn("      - 127.0.0.1:8088:80\n", text)
        self.assertNotRegex(text, r"(?m)^\s*-\s*8088:80\s*$")
        self.assertNotIn("0.0.0.0:8088", text)
        self.assertNotIn("[::]:8088", text)
        self.assertNotIn("192.168.0.180:8088", text)

    def test_cv_readme_has_no_direct_lan_publish(self) -> None:
        text = README.read_text(encoding="utf-8")

        self.assertIn("Host-local origin: `http://127.0.0.1:8088/`", text)
        self.assertIn("Direct LAN publish: none", text)
        self.assertNotIn("Local: `http://192.168.0.180:8088/`", text)

    def test_no_wildcard_cv_port_mapping_variant_is_tracked(self) -> None:
        text = COMPOSE.read_text(encoding="utf-8")
        forbidden = re.compile(
            r"(?m)^\s*-\s*(?:0\.0\.0\.0:|\[::\]:)?8088:80\s*$"
        )
        self.assertIsNone(forbidden.search(text))


if __name__ == "__main__":
    unittest.main()
