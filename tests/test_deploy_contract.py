from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-main.yml"
CI = ROOT / ".github" / "workflows" / "ci.yml"
HELPER = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"
RUNNER_INSTALLER = ROOT / "runner" / "install-github-cv-runner.sh"
HELPER_INSTALLER = ROOT / "runner" / "install-github-main-deploy.sh"
ACTIVATOR = ROOT / "runner" / "activate-github-main-deploy.sh"
VALIDATOR = ROOT / "scripts" / "validate-source.sh"
GITIGNORE = ROOT / ".gitignore"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DeployContractTests(unittest.TestCase):
    def test_workflow_is_sha_bound_and_uses_dedicated_runner(self) -> None:
        text = read(WORKFLOW)
        for marker in (
            "workflow_run:",
            "workflows:\n      - CI",
            "branches:\n      - main",
            "github.event.workflow_run.conclusion == 'success'",
            "rozkalns-cv-release",
            "/usr/local/sbin/rozkalns-cv-deploy-main",
            "https://rozkalns.net/",
            "actions/upload-artifact@v6",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("actions/checkout", text)
        self.assertNotIn("concurrency:", text)

    def test_main_push_ci_is_not_cancelled_by_newer_merge(self) -> None:
        text = read(CI)
        self.assertIn(
            "ci-${{ github.event_name }}-${{ github.event.pull_request.number || github.sha }}",
            text,
        )
        self.assertIn(
            "cancel-in-progress: ${{ github.event_name == 'pull_request' }}",
            text,
        )

    def test_helper_never_restarts_shared_tunnel(self) -> None:
        text = read(HELPER)
        subprocess.run(["bash", "-n", str(HELPER)], check=True)
        self.assertIn("compose_runtime up -d --no-deps cvbot", text)
        self.assertIn("compose_runtime up -d --no-deps cv", text)
        self.assertIn("CLOUDFLARED_RESTARTED=false", text)
        self.assertNotIn("compose_runtime restart cloudflared", text)
        self.assertNotIn("compose_runtime up -d cloudflared", text)
        self.assertNotIn("docker compose restart cloudflared", text)
        self.assertNotIn("docker compose up -d cloudflared", text)
        self.assertIn("write_summary 'FAIL_ROLLBACK_PASS' true", text)
        self.assertIn("write_summary 'PASS' false", text)

    def test_cvbot_must_be_healthy_before_nginx(self) -> None:
        lines = [line.strip() for line in read(HELPER).splitlines()]
        cvbot_position = lines.index(
            "compose_runtime up -d --no-deps cvbot || return 1"
        )
        health_position = lines.index(
            "wait_healthy cvbot 60 2 || return 1"
        )
        nginx_position = lines.index(
            "compose_runtime up -d --no-deps cv || return 1"
        )

        self.assertLess(cvbot_position, health_position)
        self.assertLess(health_position, nginx_position)

        text = read(HELPER)
        self.assertIn('"$health" == healthy', text)
        self.assertIn("WAIT_HEALTH", text)

    def test_runtime_compose_uses_host_env_file(self) -> None:
        text = read(HELPER)
        self.assertIn(
            'COMPOSE_ENV_FILE="$RUNTIME/cloudflared.env"',
            text,
        )
        self.assertIn(
            'docker compose --env-file "$COMPOSE_ENV_FILE" "$@"',
            text,
        )
        self.assertIn(
            '[[ -s "$COMPOSE_ENV_FILE" && ! -L "$COMPOSE_ENV_FILE" ]]',
            text,
        )
        self.assertEqual(text.count("docker compose "), 1)

    def test_critical_deploy_failures_are_explicitly_propagated(self) -> None:
        text = read(HELPER)
        for marker in (
            "normalize_static_permissions || return 1",
            "compose_runtime config --quiet || return 1",
            "compose_runtime build cvbot || return 1",
            "compose_runtime up -d --no-deps cvbot || return 1",
            "wait_healthy cvbot 60 2 || return 1",
            "compose_runtime up -d --no-deps cv || return 1",
            "wait_running cv 30 2 || return 1",
            'http_ok "$LOCAL_URL" 10 3 || return 1',
            'http_ok "$PUBLIC_URL" 10 5 || return 1',
            "capture_runtime_diagnostics 'failed-source-sync-runtime'",
        ):
            self.assertIn(marker, text)

        deployed = text.index("DEPLOYED=true")
        source_sync = text.index("if ! rsync -a --delete")
        source_failure = text.index(
            "capture_runtime_diagnostics 'failed-source-sync-runtime'"
        )
        source_rollback = text.index("rollback || true", source_failure)
        self.assertLess(deployed, source_sync)
        self.assertLess(source_sync, source_failure)
        self.assertLess(source_failure, source_rollback)

    def test_static_permissions_are_normalized_safely(self) -> None:
        text = read(HELPER)
        for marker in (
            "umask 022; exec git",
            '[[ -d "$RUNTIME/html" && ! -L "$RUNTIME/html" ]]',
            '[[ -f "$RUNTIME/html/index.html" && '
            '! -L "$RUNTIME/html/index.html" ]]',
            '[[ -f "$RUNTIME/nginx.conf" && '
            '! -L "$RUNTIME/nginx.conf" ]]',
            'find "$RUNTIME/html" -type d -exec chmod 0755 {} + '
            '|| return 1',
            'find "$RUNTIME/html" -type f -exec chmod 0644 {} + '
            '|| return 1',
            'chmod 0644 "$RUNTIME/nginx.conf" || return 1',
        ):
            self.assertIn(marker, text)

    def test_failure_diagnostics_are_captured_before_rollback(self) -> None:
        text = read(HELPER)
        diagnostics = text.index(
            "capture_runtime_diagnostics 'failed-deploy-runtime'"
        )
        rollback = text.index("rollback || true", diagnostics)
        self.assertLess(diagnostics, rollback)
        for marker in (
            "CVBOT HEALTH HISTORY",
            "CVBOT LOGS",
            "post-rollback-runtime",
            "failed-rollback-runtime",
        ):
            self.assertIn(marker, text)

    def test_evidence_is_restricted_then_handed_to_runner(self) -> None:
        text = read(HELPER)
        for marker in (
            "EVIDENCE_ROOT='/home/github-cv-runner/actions-runner/_work/_temp'",
            '"${SUDO_USER:-}" == github-cv-runner',
            "evidence directory is outside the dedicated runner temp root",
            "chown -R -- \"$EVIDENCE_UID:$EVIDENCE_GID\" \"$EVIDENCE_DIR\"",
            "chmod -R u+rwX,go-rwx \"$EVIDENCE_DIR\"",
            "trap 'finish $?' EXIT",
        ):
            self.assertIn(marker, text)

    def test_runtime_chat_data_is_private_and_preserved(self) -> None:
        helper = read(HELPER)
        validator = read(VALIDATOR)
        gitignore = read(GITIGNORE)

        self.assertIn("--exclude='bot/data/'", helper)
        self.assertIn(
            "runtime CV assistant data must not be versioned",
            validator,
        )
        self.assertIn("bot/data/*", gitignore)
        self.assertIn("!bot/data/.gitkeep", gitignore)

    def test_validation_uses_host_only_env_placeholders(self) -> None:
        text = read(VALIDATOR)
        subprocess.run(["bash", "-n", str(VALIDATOR)], check=True)

        self.assertIn("create_placeholder()", text)
        self.assertIn('"$ROOT/bot/.env"', text)
        self.assertIn('"$ROOT/cloudflared.env"', text)
        self.assertIn(
            "CF_TUNNEL_TOKEN=ci-placeholder-not-a-secret",
            text,
        )
        self.assertIn('rm -f -- "$placeholder"', text)

    def test_runner_has_no_docker_group_and_sudo_is_narrow(self) -> None:
        for script in (RUNNER_INSTALLER, HELPER_INSTALLER, ACTIVATOR):
            subprocess.run(["bash", "-n", str(script)], check=True)

        runner = read(RUNNER_INSTALLER)
        helper = read(HELPER_INSTALLER)
        self.assertIn("RUNNER_HAS_DOCKER_GROUP=false", runner)
        self.assertIn("rozkalns-cv-release", runner)
        self.assertIn(
            "github-cv-runner ALL=(root) NOPASSWD: "
            "/usr/local/sbin/rozkalns-cv-deploy-main *",
            helper,
        )


if __name__ == "__main__":
    unittest.main()
