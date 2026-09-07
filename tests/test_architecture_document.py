import ipaddress
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
README_PATH = ROOT / "README.md"


class ArchitectureDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")

    def test_recruiter_view_covers_required_boundaries(self) -> None:
        for marker in (
            "```mermaid",
            "Browser / visitor",
            "Cloudflare edge",
            "Shared Cloudflare Tunnel",
            "RPi5_main-owned",
            "Nginx / static CV",
            "CV Assistant",
            "Cloudflare Turnstile",
            "OpenAI Responses API",
            "Prometheus metrics source",
            "GitHub source",
            "CI + security checks",
            "Separate deployment process",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.architecture)

    def test_readme_links_recruiters_to_architecture_view(self) -> None:
        self.assertIn(
            "[Architecture & trust boundaries](docs/ARCHITECTURE.md)",
            self.readme,
        )

    def test_shared_ingress_ownership_cannot_silently_flip(self) -> None:
        self.assertIn(
            "This repository does not own the shared Tunnel connector",
            self.architecture,
        )
        self.assertIn(
            "`RPi5_main` owns the shared host-ingress connector lifecycle",
            self.architecture,
        )

        lowered = self.architecture.lower()
        for forbidden in (
            "rozkalns-cv owns the shared cloudflare tunnel",
            "application-owned cloudflared",
            "cv-owned cloudflare tunnel",
            "this repository owns the shared tunnel connector",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)

    def test_document_does_not_expose_private_host_or_network_details(self) -> None:
        lowered = self.architecture.lower()
        for forbidden in (
            "/home/",
            "/etc/",
            "/var/",
            "andris/",
            "account id",
            "api key",
            "private job-search",
            "residential address",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)

        ipv4_candidates = re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", self.architecture)
        for candidate in ipv4_candidates:
            with self.subTest(candidate=candidate):
                address = ipaddress.ip_address(candidate)
                self.assertFalse(address.is_private)
                self.assertFalse(address.is_loopback)
                self.assertFalse(address.is_link_local)

    def test_architecture_is_explicitly_not_live_state_evidence(self) -> None:
        self.assertIn(
            "not a production-status report",
            self.architecture,
        )
        self.assertIn(
            "It does not assert that these components are currently deployed or healthy",
            self.architecture,
        )
        self.assertIn(
            "Source readiness and production state are deliberately separate",
            self.architecture,
        )

    def test_public_evidence_anchors_exist_in_repository(self) -> None:
        anchors = (
            "nginx.conf",
            "docker-compose.yml",
            "bot/provider.py",
            "bot/config.py",
            "frontend/core/turnstile.mjs",
            "bot/turnstile.py",
            "scripts/generate-stats.py",
            "frontend/features/stats.mjs",
            "docs/LIVE_STATS.md",
            "README.md",
            "tests/test_compose_ingress_boundary.py",
            ".github/workflows/ci.yml",
        )
        for relative_path in anchors:
            with self.subTest(relative_path=relative_path):
                self.assertIn(f"`{relative_path}`", self.architecture)
                self.assertTrue((ROOT / relative_path).is_file())


if __name__ == "__main__":
    unittest.main()
