from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/c9-production-acceptance.yml"
SMOKE = ROOT / "scripts/c9-production-smoke.mjs"


class C9ProductionAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.smoke = SMOKE.read_text(encoding="utf-8")

    def test_workflow_is_main_only_and_never_pull_request_triggered(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertRegex(self.workflow, r"(?m)^  push:\s*$")
        self.assertRegex(self.workflow, r"(?m)^      - main\s*$")
        self.assertNotRegex(self.workflow, r"(?m)^  pull_request(?:_target)?:")
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)
        self.assertIn("needs: resolve", self.workflow)
        for label in ("self-hosted", "Linux", "ARM64", "rozkalns-cv-release"):
            self.assertIn(f"- {label}", self.workflow)

    def test_acceptance_waits_for_exact_ci_deploy_and_evidence(self) -> None:
        for marker in (
            "head_sha={encoded}",
            "C9_MAIN_CI=PASS",
            "C9_DEPLOY=PASS",
            "Verify installed deploy helper matches target source",
            "Deploy queued merge SHA",
            "Verify public frontend contracts",
            "Upload deploy evidence",
            "rozkalns-cv-deploy-{expected}-run-{run_id}",
        ):
            self.assertIn(marker, self.workflow)
        self.assertIn("main moved during C9 acceptance", self.workflow)

    def test_self_hosted_acceptance_is_read_only(self) -> None:
        production = self.workflow.split("\n  production:\n", 1)[1]
        self.assertNotRegex(production, r"(?m)^\s+sudo(?:\s|$)")
        self.assertNotRegex(production, r"(?m)^\s+docker(?:\s|$)")
        self.assertNotIn("docker compose", production)
        self.assertIn("PRODUCTION_WRITE=false", production)
        self.assertIn("SUDO_USED=false", production)
        self.assertIn("DOCKER_USED=false", production)
        self.assertIn("SHARED_TUNNEL_MUTATION=false", production)

    def test_turnstile_production_boundary_has_no_test_key_bypass(self) -> None:
        combined = self.workflow + "\n" + self.smoke
        for dummy_key in (
            "1x00000000000000000000AA",
            "2x00000000000000000000AB",
            "1x0000000000000000000000000000000AA",
            "2x0000000000000000000000000000000AA",
        ):
            self.assertNotIn(dummy_key, combined)
        self.assertNotIn("siteverify", self.smoke.lower())
        self.assertIn("TURNSTILE_REAL_SUCCESS=MANUAL_ONLY", self.workflow)
        self.assertIn("Real production Turnstile is intentionally not solved by automation", self.smoke)
        self.assertIn("#contactEmail.contact-masked", self.smoke)
        self.assertIn("#contactPhone.contact-masked", self.smoke)

    def test_browser_evidence_does_not_log_contact_or_chat_content(self) -> None:
        self.assertNotRegex(self.smoke, r"console\.log\([^\n]*(?:chat|contact|reply|message)")
        self.assertNotRegex(self.smoke, r"console\.log\([^\n]*(?:mailto|tel)")
        self.assertIn("CONTACT_OR_CHAT_CONTENT_LOGGED=false", self.workflow)
        self.assertIn('document.querySelector(\'#chatStatus\')?.textContent === "Answer complete."', self.smoke)

    def test_acceptance_artifact_upload_is_pinned(self) -> None:
        self.assertIn(
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1",
            self.workflow,
        )
        self.assertIn("retention-days: 90", self.workflow)


if __name__ == "__main__":
    unittest.main()
