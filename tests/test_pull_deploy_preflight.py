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

    def test_uses_only_scoped_github_app_auth(self) -> None:
        self.assertIn(
            "/usr/local/sbin/rozkalns-github-app-read-token",
            self.text,
        )
        self.assertIn("unset GH_TOKEN GITHUB_TOKEN", self.text)
        self.assertIn(
            'sudo -n "$TOKEN_BROKER" --repository "$REPO"',
            self.text,
        )
        self.assertEqual(self.text.count("sudo -n"), 1)
        self.assertNotIn("gh auth status", self.text)
        self.assertIn("root:root:755", self.text)

    def test_requires_exact_main_and_exact_successful_ci(self) -> None:
        self.assertIn("refs/remotes/origin/main", self.text)
        self.assertIn("merge-base --is-ancestor", self.text)
        self.assertIn("actions/workflows/ci.yml/runs", self.text)
        self.assertIn('row.get("event") == "push"', self.text)
        self.assertIn('row.get("head_branch") == "main"', self.text)
        self.assertIn('row.get("head_sha") == sha', self.text)
        self.assertIn('row.get("conclusion") == "success"', self.text)
        self.assertIn('row.get("name") == "validate"', self.text)

    def test_uses_root_owned_deploy_impact_classifier(self) -> None:
        self.assertIn(
            "/usr/local/libexec/rozkalns-cv/classify-deploy-impact",
            self.text,
        )
        self.assertIn('--base "$PRODUCTION_SHA"', self.text)
        self.assertIn('--target "$TARGET_SHA"', self.text)
        self.assertIn('DEPLOY_IMPACT="${impact[0]}"', self.text)
        self.assertIn('CONTROL_PLANE_CHANGED="${impact[1]}"', self.text)
        self.assertIn("DB_HOST_APPLY_REQUIRED", self.text)
        self.assertIn("MANUAL_ROLLOUT_REQUIRED", self.text)
        self.assertIn("AUTO_DEPLOY_SAFE", self.text)
        self.assertIn("NO_DEPLOY", self.text)

    def test_sensitive_and_no_deploy_outcomes_precede_pull_identity_gate(self) -> None:
        sensitive_case = self.text.index(
            "DB_HOST_APPLY_REQUIRED|MANUAL_ROLLOUT_REQUIRED|NO_DEPLOY"
        )
        pull_gate = self.text.index("EXPECTED_PULL_LIBRARY_BLOB=")
        self.assertLess(sensitive_case, pull_gate)
        self.assertIn("PULL_DEPLOY_PREFLIGHT_RESULT=%s", self.text)
        self.assertIn("PRODUCTION_MUTATION_AUTHORIZED=false", self.text)

    def test_auto_safe_targets_require_exact_pull_artifact_identity(self) -> None:
        auto_case = self.text.index("AUTO_DEPLOY_SAFE)")
        pull_gate = self.text.index("EXPECTED_PULL_LIBRARY_BLOB=")
        self.assertLess(auto_case, pull_gate)
        for marker in (
            "PULL_LIBRARY='/usr/local/libexec/rozkalns-cv/"
            "rozkalns-cv-deploy-library'",
            "PULL_LIBRARY_SOURCE='runner/release/rozkalns-cv-deploy-main'",
            "PULL_WRAPPER='/usr/local/sbin/rozkalns-cv-pull-deploy-main'",
            "PULL_WRAPPER_SOURCE='runner/release/rozkalns-cv-pull-deploy-main'",
            'git hash-object "$PULL_LIBRARY"',
            'git hash-object "$PULL_WRAPPER"',
            "WAIT_PULL_TRANSPORT_ACTIVATION",
        ):
            self.assertIn(marker, self.text)
        self.assertNotIn("WAIT_HELPER_ACTIVATION", self.text)
        self.assertNotIn(
            "HELPER='/usr/local/sbin/rozkalns-cv-deploy-main'",
            self.text,
        )

    def test_missing_or_unsafe_pull_transport_is_a_wait_state(self) -> None:
        transport_check = self.text.index('[[ ! -x "$PULL_LIBRARY"')
        wait_state = self.text.index(
            "PULL_DEPLOY_PREFLIGHT_RESULT=WAIT_PULL_TRANSPORT_ACTIVATION",
            transport_check,
        )
        self.assertLess(transport_check, wait_state)
        self.assertIn('-L "$PULL_LIBRARY"', self.text)
        self.assertIn('-L "$PULL_WRAPPER"', self.text)
        self.assertIn(
            '"$(stat -c \'%U:%G:%a\' "$PULL_LIBRARY")" != \'root:root:755\'',
            self.text,
        )
        self.assertIn(
            '"$(stat -c \'%U:%G:%a\' "$PULL_WRAPPER")" != \'root:root:755\'',
            self.text,
        )

    def test_first_stage_cannot_mutate_production(self) -> None:
        self.assertNotIn("docker ", self.text)
        self.assertNotIn("systemctl ", self.text)
        self.assertNotIn('sudo -n "$PULL_WRAPPER"', self.text)
        self.assertNotIn('"$PULL_WRAPPER" "$TARGET_SHA"', self.text)
        self.assertIn("PRODUCTION_MUTATION_AUTHORIZED=false", self.text)
        self.assertIn("PULL_DEPLOY_PREFLIGHT_RESULT=READY", self.text)

    def test_ready_reports_both_exact_pull_artifact_blobs(self) -> None:
        self.assertIn("PULL_LIBRARY_BLOB_SHA=%s", self.text)
        self.assertIn("PULL_WRAPPER_BLOB_SHA=%s", self.text)
        self.assertIn('"$ACTUAL_PULL_LIBRARY_BLOB"', self.text)
        self.assertIn('"$ACTUAL_PULL_WRAPPER_BLOB"', self.text)

    def test_serializes_preflight_and_fails_closed(self) -> None:
        self.assertIn("flock -n 9", self.text)
        self.assertIn("NO_OP_BUSY", self.text)
        self.assertIn("set -Eeuo pipefail", self.text)
        self.assertIn("release-control worktree is not clean", self.text)


if __name__ == "__main__":
    unittest.main()
