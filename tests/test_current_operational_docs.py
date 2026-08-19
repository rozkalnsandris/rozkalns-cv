from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "docs" / "MIGRATION_RUNBOOK.md"
KNOWLEDGE = ROOT / "docs" / "PROJECT_KNOWLEDGE.md"


class CurrentOperationalDocsTests(unittest.TestCase):
    def test_migration_runbook_is_archival_not_retired_runner_instructions(self) -> None:
        text = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("# Migration runbook — archived", text)
        self.assertIn("completed historical record", text)
        self.assertIn("Do not reconstruct or execute", text)
        self.assertIn("rozkalns-cv-pull-deploy.timer", text)
        self.assertIn("AUTO_DEPLOY_SAFE", text)
        for stale_instruction in (
            "bash runner/activate-github-main-deploy.sh",
            "Deploy merged main to RPi5",
            "github-cv-runner",
            "rozkalns-cv-release",
            "bash scripts/bootstrap-github.sh",
            "cloudflared.env",
        ):
            self.assertNotIn(stale_instruction, text)

    def test_project_knowledge_tracks_current_pull_and_ingress_boundaries(self) -> None:
        text = KNOWLEDGE.read_text(encoding="utf-8")
        for required in (
            "Application services: `cv` (nginx) and `cvbot` (Python assistant)",
            "http://127.0.0.1:8088/",
            "Direct LAN publish: none",
            "systemd `cloudflared.service`",
            "public `rozkalnsandris/rozkalns-cv`",
            "GitHub Actions provides CI/security evidence only",
            "rozkalns-cv-pull-deploy.timer",
            "AUTO_DEPLOY_SAFE",
            "deploys only\n`cv` and `cvbot`",
        ):
            self.assertIn(required, text)

        for stale_current_claim in (
            "Tunnel service/container: `cv-cloudflared`",
            "Private repository: `rozkalnsandris/rozkalns-cv`",
            "Every successful push CI on `main` queues a serial production deployment",
            "Dedicated runner label: `rozkalns-cv-release`",
            "Cloudflare ingress for the root domain points to `http://cv:80`",
        ):
            self.assertNotIn(stale_current_claim, text)


if __name__ == "__main__":
    unittest.main()
