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

    def test_helper_preflights_tunnel_replica_before_replacement(self) -> None:
        text = read(HELPER)
        subprocess.run(["bash", "-n", str(HELPER)], check=True)
        for marker in (
            "preflight_cloudflared_canary()",
            'compose_at "$root" run -d --no-deps',
            "--name \"$CLOUDFLARED_CANARY\" cloudflared",
            "tunnel --no-autoupdate --metrics 0.0.0.0:20241 run",
            '"http://$ip:20241/diag/tunnel"',
            "wait_cloudflared_edge \"$CLOUDFLARED_CANARY\" 30 2",
            "CLOUDFLARED_CANARY_READY=true",
            "cloudflared target replica did not become edge-ready",
        ):
            self.assertIn(marker, text)

        canary = text.index('preflight_cloudflared_canary "$CANDIDATE"')
        backup = text.index('BACKUP="$BACKUP_ROOT/${STAMP}-${OLD_SHA:-unknown}"')
        mutation = text.index("MUTATION_STARTED=true")
        source_sync = text.index('managed_rsync "$CANDIDATE" "$RUNTIME"')
        self.assertLess(canary, backup)
        self.assertLess(backup, mutation)
        self.assertLess(mutation, source_sync)

    def test_helper_reconciles_pinned_tunnel_only_after_canary(self) -> None:
        text = read(HELPER)
        for marker in (
            "compose_runtime up -d --no-deps cvbot",
            "compose_runtime up -d --no-deps cv",
            "compose_runtime up -d --no-deps cloudflared",
            "wait_running cv-cloudflared 30 2",
            "wait_cloudflared_edge cv-cloudflared 30 2",
            "CLOUDFLARED_IMAGE_IDENTITY=PASS",
            '[[ "$CLOUDFLARED_CANARY_READY" == true ]] || return 1',
            "remove_cloudflared_canary",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("compose_runtime restart cloudflared", text)
        self.assertNotIn("docker compose restart cloudflared", text)
        self.assertIn("write_summary 'FAIL_ROLLBACK_PASS' true", text)
        self.assertIn("write_summary 'PASS' false", text)

    def test_cloudflared_image_identity_is_exact_and_digest_pinned(self) -> None:
        text = read(HELPER)
        self.assertIn('images="$(compose_at "$root" config --images)"', text)
        self.assertIn(
            "count=\"$(grep -Ec '^cloudflare/cloudflared:' <<<\"$images\" || true)\"",
            text,
        )
        self.assertIn('[[ "$count" == 1 ]] || return 1', text)
        self.assertIn('[[ "$image" == *@sha256:* ]] || return 1', text)
        self.assertIn(
            'actual="$(docker inspect -f \'{{.Config.Image}}\' '
            'cv-cloudflared 2>/dev/null || true)"',
            text,
        )
        self.assertIn('[[ "$actual" == "$expected" ]] || return 1', text)
        compose = read(COMPOSE)
        self.assertIn(
            "command: tunnel --no-autoupdate --metrics 0.0.0.0:20241 run",
            compose,
        )

    def test_cloudflared_readiness_is_edge_not_process_only(self) -> None:
        text = read(HELPER)
        for marker in (
            "cloudflared_connected_count()",
            "/diag/tunnel",
            'row.get("isConnected") is True',
            "WAIT_CLOUDFLARED_EDGE",
            "CLOUDFLARED_EDGE_READY=PASS",
            "wait_cloudflared_edge cv-cloudflared 30 2",
        ):
            self.assertIn(marker, text)

    def test_cloudflared_failure_evidence_is_sanitized_and_complete(self) -> None:
        text = read(HELPER)
        for marker in (
            "redact_cloudflared_logs()",
            "<redacted-token>",
            "===== CLOUDFLARED LOGS =====",
            "===== CLOUDFLARED CANARY LOGS =====",
            "cloudflared-canary-failure.log",
            "cloudflared-canary-ready.log",
            "CLOUDFLARED_CANARY_PRESERVED",
        ):
            self.assertIn(marker, text)

    def test_cvbot_runtime_security_is_fail_closed_and_evidenced(self) -> None:
        text = read(HELPER)
        for marker in (
            "verify_cvbot_runtime_security()",
            'require(data.get("user") == expected_user, "cvbot user mismatch")',
            'require(data.get("readonly") is True, "cvbot rootfs is writable")',
            'require(data.get("privileged") is False, "cvbot is privileged")',
            'require((data.get("cap_add") or []) == [], "cvbot has added capabilities")',
            'require(cap_drop == ["ALL"], "cvbot does not drop all capabilities")',
            '"no-new-privileges:true" in security_opt',
            'require(data.get("pids") == 128, "cvbot pids limit mismatch")',
            'row.get("Destination") == "/app/data"',
            "CVBOT_RUNTIME_SECURITY=PASS",
            "CVBOT_RUNTIME_USER=",
            "CVBOT_ROOTFS_READ_ONLY=true",
            "CVBOT_CAP_ADD=none",
            "CVBOT_CAP_DROP=ALL",
            "CVBOT_NO_NEW_PRIVILEGES=true",
            "CVBOT_PIDS_LIMIT=128",
            "CVBOT_DATA_RW=true",
            "===== CVBOT SECURITY =====",
        ):
            self.assertIn(marker, text)

    def test_cvbot_must_be_secure_before_nginx_and_tunnel(self) -> None:
        lines = [line.strip() for line in read(HELPER).splitlines()]
        cvbot_position = lines.index(
            "compose_runtime up -d --no-deps cvbot || return 1"
        )
        health_position = lines.index(
            "wait_healthy cvbot 60 2 || return 1"
        )
        security_position = lines.index(
            "verify_cvbot_runtime_security || return 1"
        )
        nginx_position = lines.index(
            "compose_runtime up -d --no-deps cv || return 1"
        )
        local_position = lines.index(
            'http_ok "$LOCAL_URL" 10 3 || return 1'
        )
        tunnel_position = lines.index("reconcile_cloudflared || return 1")
        public_position = lines.index(
            'http_ok "$PUBLIC_URL" 10 5 || return 1'
        )
        self.assertLess(cvbot_position, health_position)
        self.assertLess(health_position, security_position)
        self.assertLess(security_position, nginx_position)
        self.assertLess(nginx_position, local_position)
        self.assertLess(local_position, tunnel_position)
        self.assertLess(tunnel_position, public_position)

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
            "verify_cvbot_runtime_security || return 1",
            "compose_runtime up -d --no-deps cv || return 1",
            "wait_running cv 30 2 || return 1",
            'http_ok "$LOCAL_URL" 10 3 || return 1',
            "reconcile_cloudflared || return 1",
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

    def test_source_validation_runs_as_unprivileged_owner_from_stage(self) -> None:
        text = read(HELPER)
        self.assertIn('runuser -u "$OWNER" -- bash -c', text)
        self.assertIn(
            "'cd \"$1\" && exec bash \"$1/scripts/validate-source.sh\" \"$1\"'",
            text,
        )
        self.assertIn('bash "$STAGE"', text)
        self.assertNotIn(
            'runuser -u "$OWNER" -- bash "$STAGE/scripts/validate-source.sh"',
            text,
        )

    def test_failure_diagnostics_are_captured_before_rollback(self) -> None:
        text = read(HELPER)
        for marker in (
            "failed-source-sync-runtime",
            "failed-deploy-runtime",
            "failed-rollback-sync-runtime",
            "post-rollback-runtime",
            "failed-rollback-runtime",
            "failed-cloudflared-canary-preflight",
            "CVBOT SECURITY",
            "CVBOT HEALTH HISTORY",
            "CVBOT LOGS",
            "CLOUDFLARED LOGS",
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
