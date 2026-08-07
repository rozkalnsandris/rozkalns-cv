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
COMPOSE = ROOT / "docker-compose.yml"
LEGACY_NETWORK = ROOT / "docker-compose.network.yml"


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
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("actions/checkout", text)
        self.assertNotIn("actions/upload-artifact@v", text)
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

    def test_runtime_compose_uses_host_env_file(self) -> None:
        text = read(HELPER)
        self.assertIn('COMPOSE_ENV_FILE="$RUNTIME/cloudflared.env"', text)
        self.assertIn(
            'docker compose --env-file "$COMPOSE_ENV_FILE" "$@"', text
        )
        self.assertIn(
            '[[ -s "$COMPOSE_ENV_FILE" && ! -L "$COMPOSE_ENV_FILE" ]]',
            text,
        )
        self.assertEqual(text.count("docker compose "), 2)

    def test_effective_compose_network_is_pinned_everywhere(self) -> None:
        compose = read(COMPOSE)
        helper = read(HELPER)
        validator = read(VALIDATOR)
        self.assertFalse(LEGACY_NETWORK.exists())
        for marker in (
            "name: cv_default",
            "subnet: 172.19.0.0/16",
            "gateway: 172.19.0.1",
        ):
            self.assertIn(marker, compose)
        for marker in (
            "NETWORK_NAME='cv_default'",
            "NETWORK_SUBNET='172.19.0.0/16'",
            "NETWORK_GATEWAY='172.19.0.1'",
            'validate_rendered_network "$CANDIDATE"',
            'validate_rendered_network "$RUNTIME"',
            "validate_existing_network || return 1",
            "existing cv_default network conflicts with the pinned subnet",
        ):
            self.assertIn(marker, helper)
        for marker in (
            "legacy docker-compose.network.yml must be merged",
            "effective Compose network name is not cv_default",
            "effective Compose subnet is not pinned",
            "effective Compose gateway is not pinned",
        ):
            self.assertIn(marker, validator)

    def test_transaction_covers_every_post_mutation_failure(self) -> None:
        text = read(HELPER)
        for marker in (
            "MUTATION_STARTED=true",
            "TRANSACTION_COMMITTED=true",
            "trap 'finish $?' EXIT",
            '[[ "$MUTATION_STARTED" == true ]]',
            '[[ "$TRANSACTION_COMMITTED" != true ]]',
            '[[ "$ROLLBACK_ATTEMPTED" != true ]]',
            'managed_rsync "$BACKUP/runtime" "$RUNTIME"',
            "write_state_atomically || fail",
            "write_runtime_manifest",
        ):
            self.assertIn(marker, text)

        mutation = text.index("MUTATION_STARTED=true")
        source_sync = text.index('managed_rsync "$CANDIDATE" "$RUNTIME"')
        commit = text.index("TRANSACTION_COMMITTED=true")
        state = text.index("write_state_atomically || fail")
        self.assertLess(mutation, source_sync)
        self.assertLess(source_sync, state)
        self.assertLess(state, commit)

    def test_critical_deploy_failures_are_explicitly_propagated(self) -> None:
        text = read(HELPER)
        for marker in (
            'normalize_managed_permissions "$RUNTIME" || return 1',
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

    def test_static_permissions_and_candidate_are_validated_safely(self) -> None:
        text = read(HELPER)
        for marker in (
            "umask 022; exec git",
            '[[ -d "$root/html" && ! -L "$root/html" ]]',
            '[[ -f "$root/html/index.html" && ! -L "$root/html/index.html" ]]',
            '[[ -f "$root/nginx.conf" && ! -L "$root/nginx.conf" ]]',
            'find "$root" -type l -print -quit',
            'find "$root/html" -type d -exec chmod 0755 {} +',
            'find "$root/html" -type f -exec chmod 0644 {} +',
            'managed_rsync "$STAGE" "$CANDIDATE"',
            'normalize_managed_permissions "$CANDIDATE"',
        ):
            self.assertIn(marker, text)

    def test_capacity_atomic_state_and_backup_retention_are_required(self) -> None:
        text = read(HELPER)
        for marker in (
            "BACKUP_RETENTION_COUNT=5",
            "BACKUP_RETENTION_DAYS=14",
            "MIN_FREE_BYTES=1073741824",
            "MIN_FREE_INODES=10000",
            'require_capacity "$RUNTIME"',
            'require_capacity "$BACKUP_ROOT"',
            'mktemp "$STATE_DIR/.current-sha.XXXXXXXX"',
            'mv -f -- "$tmp" "$STATE_FILE"',
            'sync -f "$STATE_DIR"',
            "prune_backups || fail 'backup retention preflight failed'",
        ):
            self.assertIn(marker, text)

    def test_backup_does_not_duplicate_secrets_or_chat_data(self) -> None:
        text = read(HELPER)
        self.assertIn('managed_rsync "$RUNTIME" "$BACKUP/runtime"', text)
        for marker in (
            "--exclude='.env'",
            "--exclude='*.env'",
            "--exclude='cloudflared.env'",
            "--exclude='stats.json'",
            "--exclude='bot/data/'",
        ):
            self.assertIn(marker, text)

    def test_source_validation_runs_as_unprivileged_owner(self) -> None:
        text = read(HELPER)
        lines = [line.strip() for line in text.splitlines()]
        self.assertIn(
            'runuser -u "$OWNER" -- bash '
            '"$STAGE/scripts/validate-source.sh" "$STAGE"',
            text,
        )
        self.assertFalse(
            any(
                line.startswith(
                    'bash "$STAGE/scripts/validate-source.sh" "$STAGE"'
                )
                for line in lines
            )
        )

    def test_failure_diagnostics_are_captured_before_rollback(self) -> None:
        text = read(HELPER)
        for marker in (
            "failed-source-sync-runtime",
            "failed-deploy-runtime",
            "failed-rollback-sync-runtime",
            "post-rollback-runtime",
            "failed-rollback-runtime",
            "CVBOT HEALTH HISTORY",
            "CVBOT LOGS",
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
            "runtime CV assistant data must not be versioned", validator
        )
        self.assertIn("bot/data/*", gitignore)
        self.assertIn("!bot/data/.gitkeep", gitignore)

    def test_validation_uses_host_only_env_placeholders(self) -> None:
        text = read(VALIDATOR)
        subprocess.run(["bash", "-n", str(VALIDATOR)], check=True)
        self.assertIn("create_placeholder()", text)
        self.assertIn('"$ROOT/bot/.env"', text)
        self.assertIn('"$ROOT/cloudflared.env"', text)
        self.assertIn("CF_TUNNEL_TOKEN=ci-placeholder-not-a-secret", text)
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
