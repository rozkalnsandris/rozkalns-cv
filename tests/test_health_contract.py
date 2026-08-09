from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HealthContractTests(unittest.TestCase):
    def test_app_exposes_distinct_liveness_and_readiness(self) -> None:
        source = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        self.assertIn('@flask_app.get("/health")', source)
        self.assertIn('@flask_app.get("/health/live")', source)
        self.assertIn('@flask_app.get("/health/ready")', source)
        self.assertIn("check_local_readiness(", source)
        readiness_body = source.split("def readiness()", 1)[1].split(
            '@flask_app.get("/contact-config")', 1
        )[0]
        self.assertNotIn("requests.get(", readiness_body)
        self.assertNotIn("requests.post(", readiness_body)
        self.assertNotIn("result.reason", readiness_body)

    def test_docker_healthcheck_uses_readiness(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("http://localhost:5000/health/ready", compose)
        self.assertNotIn("http://localhost:5000/health')", compose)

    def test_nginx_identity_is_unchanged_by_health_contract(self) -> None:
        nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertNotIn("location = /api/health/ready", nginx)
        self.assertIn(
            'net.rozkalns.cv.nginx-config-sha256: "24a4b18221429dce78485d2ff4c8d65380cc94301c9409714dec882064dd74ff"',
            compose,
        )

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
