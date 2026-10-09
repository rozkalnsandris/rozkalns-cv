from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / "deploy/simple-deploy/nginx.conf"
APP = ROOT / "bot/app.py"
SUPERVISOR = ROOT / "deploy/simple-deploy/supervise.py"


class SimpleFirstNginxContactQuotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conf = CONF.read_text(encoding="utf-8")

    def test_origin_global_backstop_uses_no_spoofable_client_header(self):
        self.assertIn(
            "limit_req_zone $server_name zone=cv_contact_global:1m rate=60r/m;",
            self.conf,
        )
        self.assertNotIn("cv_contact_per_ip", self.conf)
        self.assertNotIn("limit_req_dry_run on;", self.conf)

    def test_exact_contact_location_is_ratelimited_before_siteverify(self):
        match = re.search(
            r"location = /api/contact-reveal \{([^{}]+)\}", self.conf
        )
        self.assertIsNotNone(match)
        route = match.group(1)
        for rule in (
            "limit_req zone=cv_contact_global burst=15 nodelay;",
            "limit_req_status 429;",
            "proxy_pass http://127.0.0.1:5000/contact-reveal;",
            "proxy_set_header Host $host;",
            "proxy_set_header X-Real-IP $remote_addr;",
        ):
            self.assertIn(rule, route)
        self.assertIn("location /api/ {", self.conf)
        for endpoint in ("/api/chat", "/api/chat-config", "/api/chat-admission"):
            self.assertIn("location = " + endpoint + " { return 404; }", self.conf)

    def test_docker_gateway_does_not_grant_forwarded_header_trust(self):
        for forbidden in (
            "set_real_ip_from", "real_ip_header", "real_ip_recursive",
            "172.19.0.1/32", "172.23.0.1/32",
            "$proxy_add_x_forwarded_for", "cv_contact_per_ip",
        ):
            self.assertNotIn(forbidden, self.conf)
        self.assertEqual(
            self.conf.count('proxy_set_header CF-Connecting-IP "";'), 2
        )
        self.assertEqual(
            self.conf.count("proxy_set_header X-Forwarded-For $remote_addr;"), 2
        )
        self.assertEqual(
            self.conf.count("proxy_set_header X-Real-IP $remote_addr;"), 2
        )

    def test_no_public_sqlite_or_open_backend_port(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn("if public_only", source)
        self.assertIn("if not public_only:", source)
        self.assertIn("return address, \"\"", source)
        self.assertIn("127.0.0.1:5000", SUPERVISOR.read_text(encoding="utf-8"))
        self.assertNotIn("listen 5000", self.conf)


if __name__ == "__main__":
    unittest.main()
