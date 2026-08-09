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

    def test_pull_entrypoint_preserves_transaction_and_rollback_gates(self) -> None:
        for marker in (
            'flock 9',
            'prune_backups || fail \'backup retention preflight failed\'',
            'merge-base --is-ancestor "$TARGET_SHA" "$REMOTE_MAIN"',
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
