from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEGACY_HELPER = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"
PULL_HELPER = ROOT / "runner" / "release" / "rozkalns-cv-pull-deploy-main"
INSTALLER = ROOT / "runner" / "install-pull-deploy-main.sh"


class PullDeployTransportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = LEGACY_HELPER.read_text(encoding="utf-8")
        cls.pull = PULL_HELPER.read_text(encoding="utf-8")
        cls.installer = INSTALLER.read_text(encoding="utf-8")
        for script in (LEGACY_HELPER, PULL_HELPER, INSTALLER):
            subprocess.run(["bash", "-n", str(script)], check=True)

    def test_legacy_runner_entrypoint_is_left_intact_for_canary(self) -> None:
        for marker in (
            '[[ "${SUDO_USER:-}" == github-cv-runner ]]',
            "EVIDENCE_ROOT='/home/github-cv-runner/actions-runner/_work/_temp'",
            "deployment helper must be invoked by the dedicated CV runner",
        ):
            self.assertIn(marker, self.legacy)

    def test_pull_entrypoint_reuses_only_root_owned_deploy_library(self) -> None:
        for marker in (
            "DEPLOY_LIBRARY='/usr/local/libexec/rozkalns-cv/"
            "rozkalns-cv-deploy-library'",
            '[[ -f "$DEPLOY_LIBRARY" && ! -L "$DEPLOY_LIBRARY" ]]',
            '"$(stat -c \'%U:%G:%a\' "$DEPLOY_LIBRARY")" == \'root:root:755\'',
            "ROZKALNS_CV_DEPLOY_LIBRARY_ONLY=1",
            'source "$DEPLOY_LIBRARY"',
            "unset ROZKALNS_CV_DEPLOY_LIBRARY_ONLY",
        ):
            self.assertIn(marker, self.pull)

        self.assertNotIn(
            "/home/andris/rozkalns-cv-worktrees/release-control",
            self.pull,
        )

    def test_pull_entrypoint_accepts_only_local_andris_sudo_identity(self) -> None:
        for marker in (
            "PULL_CALLER='andris'",
            '[[ "${SUDO_USER:-}" == "$PULL_CALLER" ]]',
            '[[ "$(id -un "$SUDO_UID" 2>/dev/null)" == "$PULL_CALLER" ]]',
            "pull-deploy caller uid/gid must be non-root",
            "pull-deploy caller identity mismatch",
        ):
            self.assertIn(marker, self.pull)

        for forbidden in (
            "github-cv-runner",
            "actions-runner",
            "GITHUB_TOKEN",
            "GH_TOKEN",
        ):
            self.assertNotIn(forbidden, self.pull)

    def test_pull_entrypoint_requires_exact_argument_shape(self) -> None:
        for marker in (
            '[[ "$#" -eq 2 ]]',
            "pull-deploy helper requires exactly target SHA and evidence directory",
            '[[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]]',
            '[[ -n "$EVIDENCE_DIR" ]]',
        ):
            self.assertIn(marker, self.pull)

        argument_gate = self.pull.index('[[ "$#" -eq 2 ]]')
        source_library = self.pull.index('source "$DEPLOY_LIBRARY"')
        self.assertLess(argument_gate, source_library)

    def test_pull_evidence_is_caller_owned_and_path_bounded(self) -> None:
        for marker in (
            "PULL_EVIDENCE_ROOT='/home/andris/.local/state/"
            "rozkalns-cv-pull-deploy/evidence'",
            '"$PULL_EVIDENCE_ROOT"/rozkalns-cv-main-deploy-*',
            "evidence directory is outside the pull-deploy evidence root",
            "evidence directory is not owned by the pull-deploy caller",
            "evidence directory group does not match the pull-deploy caller",
            "DEPLOY_TRANSPORT=pull-controller",
        ):
            self.assertIn(marker, self.pull)

    def test_pull_entrypoint_requires_exact_current_main(self) -> None:
        for marker in (
            'owner_git -C "$PRIMARY" fetch --prune origin main',
            'REMOTE_MAIN="$(owner_git -C "$PRIMARY" rev-parse refs/remotes/origin/main)"',
            '[[ "$TARGET_SHA" == "$REMOTE_MAIN" ]]',
            "target SHA is not current origin/main",
        ):
            self.assertIn(marker, self.pull)

        self.assertNotIn(
            'merge-base --is-ancestor "$TARGET_SHA" "$REMOTE_MAIN"',
            self.pull,
        )

    def test_pull_entrypoint_preserves_transaction_and_rollback_gates(self) -> None:
        for marker in (
            'flock 9',
            'prune_backups || fail \'backup retention preflight failed\'',
            'runuser -u "$OWNER" -- bash -c',
            'managed_rsync "$CANDIDATE" "$RUNTIME"',
            'if ! deploy_runtime >>"$EVIDENCE_DIR/deploy.log" 2>&1; then',
            "capture_runtime_diagnostics 'failed-deploy-runtime'",
            "write_state_atomically || fail 'atomic deployed-state update failed'",
            "TRANSACTION_COMMITTED=true",
            "write_summary 'PASS' false",
        ):
            self.assertIn(marker, self.pull)

        self.assertNotIn("cloudflared", self.pull.lower())

    def test_target_runtime_prerequisites_are_checked_before_any_mutation(self) -> None:
        for marker in (
            "validate_candidate_runtime_prerequisites()",
            'runtime_requires_cvbot_client_secret "$CANDIDATE"',
            "validate_cvbot_runtime_secret_strict || return 1",
            "TARGET_RUNTIME_PREREQUISITES=PASS",
            "target-prerequisites.log",
            "target runtime prerequisites failed before production mutation",
        ):
            self.assertIn(marker, self.pull)

        prerequisite = self.pull.index(
            "if ! validate_candidate_runtime_prerequisites"
        )
        backup = self.pull.index(
            'BACKUP="$BACKUP_ROOT/${STAMP}-${OLD_SHA:-unknown}"'
        )
        mutation = self.pull.index("MUTATION_STARTED=true")
        sync = self.pull.index('managed_rsync "$CANDIDATE" "$RUNTIME"')
        self.assertLess(prerequisite, backup)
        self.assertLess(prerequisite, mutation)
        self.assertLess(prerequisite, sync)

    def test_candidate_prerequisite_failure_survives_conditional_context(self) -> None:
        marker = "validate_candidate_runtime_prerequisites() {"
        body = self.pull.split(marker, 1)[1].split("\n}\n", 1)[0]
        function_source = marker + body + "\n}\n"
        script = f"""
set -Eeuo pipefail
CANDIDATE=/tmp/unused
runtime_requires_cvbot_client_secret() {{ return 0; }}
validate_cvbot_runtime_secret_strict() {{ return 17; }}
{function_source}
if validate_candidate_runtime_prerequisites >/dev/null 2>&1; then
    exit 91
fi
"""
        completed = subprocess.run(
            ["bash", "-c", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_pull_rollback_secret_contract_is_restored_baseline_aware(self) -> None:
        for marker in (
            "runtime_requires_cvbot_client_secret()",
            "CLIENT_KEY_SECRET_MIN_BYTES = 32",
            "def validate_client_key_secret",
            "validate_cvbot_runtime_secret_strict()",
            "validate_cvbot_runtime_secret()",
            'runtime_requires_cvbot_client_secret "$RUNTIME"',
            "CVBOT_CLIENT_KEY_SECRET=NOT_REQUIRED_BY_BASELINE",
            "cvbot client pseudonymization secret contract failed",
            "cvbot client pseudonymization secret must be dedicated",
        ):
            self.assertIn(marker, self.pull)

        source_library = self.pull.index('source "$DEPLOY_LIBRARY"')
        override = self.pull.index("validate_cvbot_runtime_secret()")
        self.assertLess(source_library, override)
        self.assertNotIn('echo "$CLIENT_KEY_SECRET"', self.pull)
        self.assertNotIn('echo "$LLM_API_KEY"', self.pull)
        self.assertNotIn('printf "%s" "$CLIENT_KEY_SECRET"', self.pull)
        self.assertNotIn('printf "%s" "$LLM_API_KEY"', self.pull)

    def test_pull_public_frontend_contracts_are_inside_transaction(self) -> None:
        for marker in (
            "verify_public_frontend_contracts()",
            "/assets/app\\.[0-9a-f]{12}\\.mjs\\?cfg=[0-9a-f]{12}",
            "^Cache-Control:.*immutable",
            "^X-Content-Type-Options:[[:space:]]*nosniff",
            "nonce-[0-9a-f]{32}",
            "script-src-attr 'none'",
            "https://static.cloudflareinsights.com/beacon.min.js",
            "unsafe-inline",
            "PUBLIC_MODULE_MIME=PASS",
            "PUBLIC_CACHE_IMMUTABLE=PASS",
            "PUBLIC_NOSNIFF=PASS",
            "PUBLIC_CSP_NONCE=PASS",
            "failed-public-contract-runtime",
            "public frontend contract verification failed",
        ):
            self.assertIn(marker, self.pull)

        deploy = self.pull.index(
            'if ! deploy_runtime >>"$EVIDENCE_DIR/deploy.log" 2>&1; then'
        )
        public_gate = self.pull.index(
            'if ! verify_public_frontend_contracts >>"$EVIDENCE_DIR/deploy.log" 2>&1; then'
        )
        state = self.pull.index(
            "write_state_atomically || fail 'atomic deployed-state update failed'"
        )
        committed = self.pull.index("TRANSACTION_COMMITTED=true")
        self.assertLess(deploy, public_gate)
        self.assertLess(public_gate, state)
        self.assertLess(state, committed)

    def test_installer_adds_parallel_transport_without_touching_legacy_rule(self) -> None:
        for marker in (
            "LIBRARY_SOURCE=\"$SOURCE_WORKTREE/runner/release/"
            "rozkalns-cv-deploy-main\"",
            "WRAPPER_SOURCE=\"$SOURCE_WORKTREE/runner/release/"
            "rozkalns-cv-pull-deploy-main\"",
            "LIBRARY_DEST=\"$LIBEXEC_DIR/rozkalns-cv-deploy-library\"",
            "WRAPPER_DEST='/usr/local/sbin/rozkalns-cv-pull-deploy-main'",
            "SUDOERS='/etc/sudoers.d/rozkalns-cv-pull-deploy'",
            "CALLER='andris'",
            "EVIDENCE_ROOT='/home/andris/.local/state/"
            "rozkalns-cv-pull-deploy/evidence'",
            "andris ALL=(root) NOPASSWD: "
            "/usr/local/sbin/rozkalns-cv-pull-deploy-main *",
            "LEGACY_HELPER_CHANGED=false",
            "LEGACY_RUNNER_RULE_CHANGED=false",
            "PRODUCTION_APPLICATION_CHANGED=false",
        ):
            self.assertIn(marker, self.installer)

        for forbidden in (
            "/etc/sudoers.d/rozkalns-cv-github-deploy",
            "install-github-cv-runner",
            "systemctl",
            "userdel",
            "rm -rf /home/github-cv-runner",
        ):
            self.assertNotIn(forbidden, self.installer)


if __name__ == "__main__":
    unittest.main()
