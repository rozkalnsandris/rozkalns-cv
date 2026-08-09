from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "runner" / "pull-deploy" / "rozkalns-cv-pull-deploy-preflight"


class PullDeployPreflightContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PREFLIGHT.read_text(encoding="utf-8")

    def test_runs_only_as_unprivileged_andris(self) -> None:
        self.assertIn("must run as an unprivileged user", self.text)
        self.assertIn("must run as andris", self.text)
        self.assertNotIn("runs-on:", self.text)
        self.assertNotIn("self-hosted", self.text)

    def test_requires_exact_main_and_exact_successful_ci(self) -> None:
        self.assertIn("refs/remotes/origin/main", self.text)
        self.assertIn("merge-base --is-ancestor", self.text)
        self.assertIn("actions/workflows/ci.yml/runs", self.text)
        self.assertIn('row.get("event") == "push"', self.text)
        self.assertIn('row.get("head_branch") == "main"', self.text)
        self.assertIn('row.get("head_sha") == sha', self.text)
        self.assertIn('row.get("conclusion") == "success"', self.text)
        self.assertIn('row.get("name") == "validate"', self.text)

    def test_preserves_installed_helper_identity_gate(self) -> None:
        self.assertIn("runner/release/rozkalns-cv-deploy-main", self.text)
        self.assertIn("git hash-object \"$HELPER\"", self.text)
        self.assertIn("WAIT_HELPER_ACTIVATION", self.text)
        self.assertIn("root:root:755", self.text)

    def test_first_stage_cannot_mutate_production(self) -> None:
        self.assertNotIn("sudo ", self.text)
        self.assertNotIn("docker ", self.text)
        self.assertNotIn("systemctl ", self.text)
        self.assertNotIn("rozkalns-cv-deploy-main \"$TARGET_SHA\"", self.text)
        self.assertIn("PRODUCTION_MUTATION_AUTHORIZED=false", self.text)
        self.assertIn("PULL_DEPLOY_PREFLIGHT_RESULT=READY", self.text)

    def test_serializes_preflight_and_fails_closed(self) -> None:
        self.assertIn("flock -n 9", self.text)
        self.assertIn("NO_OP_BUSY", self.text)
        self.assertIn("set -Eeuo pipefail", self.text)
        self.assertIn("release-control worktree is not clean", self.text)


if __name__ == "__main__":
    unittest.main()
