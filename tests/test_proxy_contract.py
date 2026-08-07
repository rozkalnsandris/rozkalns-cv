from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NGINX = ROOT / "nginx.conf"
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / "bot" / ".env.example"


class ProxyContractTests(unittest.TestCase):
    def test_nginx_trusts_cloudflare_header_only_from_cv_network(self) -> None:
        text = NGINX.read_text(encoding="utf-8")
        self.assertIn("set_real_ip_from 172.19.0.0/16;", text)
        self.assertIn("real_ip_header CF-Connecting-IP;", text)
        self.assertIn("real_ip_recursive off;", text)
        self.assertRegex(
            text,
            re.compile(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr;"),
        )
        self.assertNotRegex(
            text,
            re.compile(r"proxy_set_header\s+X-Real-IP\s+\$http_"),
        )

    def test_nginx_proxy_has_fixed_address(self) -> None:
        text = COMPOSE.read_text(encoding="utf-8")
        self.assertIn("ipv4_address: 172.19.0.10", text)
        self.assertIn("subnet: 172.19.0.0/16", text)

    def test_bot_trust_boundary_matches_nginx_address(self) -> None:
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        self.assertIn("TRUSTED_PROXY_CIDRS=172.19.0.10/32", text)
        self.assertIn("CLIENT_KEY_SECRET=", text)
        self.assertIn("CHAT_RETENTION_DAYS=7", text)
        self.assertIn("TELEGRAM_INCLUDE_CONTENT=false", text)


if __name__ == "__main__":
    unittest.main()
