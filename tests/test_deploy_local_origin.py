from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"
COMPOSE = ROOT / "docker-compose.yml"


class DeployLocalOriginTests(unittest.TestCase):
    def test_deploy_health_uses_same_loopback_origin_as_compose(self) -> None:
        helper = HELPER.read_text(encoding="utf-8")
        compose = COMPOSE.read_text(encoding="utf-8")

        self.assertIn("LOCAL_URL='http://127.0.0.1:8088/'", helper)
        self.assertEqual(
            helper.count("LOCAL_URL='http://127.0.0.1:8088/'"),
            1,
        )
        self.assertNotIn("192.168.0.180:8088", helper)
        self.assertIn("      - 127.0.0.1:8088:80\n", compose)

    def test_local_health_gate_precedes_public_gate(self) -> None:
        helper = HELPER.read_text(encoding="utf-8")
        local = helper.index('http_ok "$LOCAL_URL" 10 3 || return 1')
        public = helper.index('http_ok "$PUBLIC_URL" 10 5 || return 1')
        self.assertLess(local, public)


if __name__ == "__main__":
    unittest.main()
