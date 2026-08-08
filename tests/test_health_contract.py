from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HealthContractTests(unittest.TestCase):
    def test_app_exposes_distinct_liveness_and_readiness(self) -> None:
        source = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/health")', source)
        self.assertIn('@app.get("/health/live")', source)
        self.assertIn('@app.get("/health/ready")', source)
        self.assertIn("check_local_readiness(", source)
        self.assertNotIn("requests.get(", source.split('def readiness()', 1)[1].split('@app.get("/contact-config")', 1)[0])

    def test_docker_healthcheck_uses_readiness(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("http://localhost:5000/health/ready", compose)
        self.assertNotIn("http://localhost:5000/health')", compose)

    def test_public_nginx_does_not_proxy_readiness(self) -> None:
        nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
        internal = "location = /api/health/ready {\n        return 404;\n    }"
        self.assertIn(internal, nginx)
        self.assertLess(nginx.index(internal), nginx.index("location /api/ {"))

    def test_deploy_waits_for_ready_cvbot_before_starting_nginx(self) -> None:
        helper = (ROOT / "runner/release/rozkalns-cv-deploy-main").read_text(
            encoding="utf-8"
        )
        wait = "wait_healthy cvbot 60 2 || return 1"
        web = "compose_runtime up -d --no-deps cv || return 1"
        self.assertIn(wait, helper)
        self.assertIn(web, helper)
        self.assertLess(helper.index(wait), helper.index(web))


if __name__ == "__main__":
    unittest.main()
