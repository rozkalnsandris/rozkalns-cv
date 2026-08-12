from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
HELPER = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"
RUNNER_INSTALLER = ROOT / "runner" / "install-github-cv-runner.sh"
HELPER_INSTALLER = ROOT / "runner" / "install-github-main-deploy.sh"
ACTIVATOR = ROOT / "runner" / "activate-github-main-deploy.sh"
VALIDATOR = ROOT / "scripts" / "validate-source.sh"
GITIGNORE = ROOT / ".gitignore"
COMPOSE = ROOT / "docker-compose.yml"
README = ROOT / "README.md"
LEGACY_NETWORK = ROOT / "docker-compose.network.yml"
LEGACY_TUNNEL_EXAMPLE = ROOT / "cloudflared.env.example"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DeployContractTests(unittest.TestCase):
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

    def test_helper_never_controls_shared_cloudflare_connector(self) -> None:
        helper = read(HELPER)
        compose = read(COMPOSE)
        subprocess.run(["bash", "-n", str(HELPER)], check=True)

        for forbidden in (
            "cv-cloudflared",
            "CLOUDFLARED_",
            "COMPOSE_ENV_FILE",
            "CF_TUNNEL_TOKEN",
            "TUNNEL_TOKEN",
            "preflight_cloudflared_canary",
            "reconcile_cloudflared",
            "wait_cloudflared_edge",
            "cloudflared_connected_count",
            "compose_runtime up -d --no-deps cloudflared",
        ):
            self.assertNotIn(forbidden, helper)

        for forbidden in (
            "cloudflare/cloudflared",
            "container_name: cv-cloudflared",
            "CF_TUNNEL_TOKEN",
            "TUNNEL_TOKEN",
        ):
            self.assertNotIn(forbidden, compose)

        self.assertNotIn('cloudflared.env"', helper)
        self.assertIn("SHARED_INGRESS_CONTROLLED=false", helper)
        self.assertIn('http_ok "$PUBLIC_URL" 10 5 || return 1', helper)

    def test_rollback_preserves_shared_ingress_ownership_boundary(self) -> None:
        text = read(HELPER)
        for marker in (
            "preserve_shared_ingress_boundary_on_rollback()",
            'line.startswith("  cloudflared:")',
            'rm -f -- "$RUNTIME/cloudflared.env.example"',
            "ROLLBACK_SHARED_INGRESS_BOUNDARY=PASS",
            "failed-rollback-ingress-boundary",
        ):
            self.assertIn(marker, text)

        restore = text.index('managed_rsync "$BACKUP/runtime" "$RUNTIME"')
        boundary = text.index("preserve_shared_ingress_boundary_on_rollback", restore)
        redeploy = text.index("if deploy_runtime; then", boundary)
        self.assertLess(restore, boundary)
        self.assertLess(boundary, redeploy)
        self.assertNotIn('rm -f -- "$RUNTIME/cloudflared.env"', text)

    def test_compose_and_validator_enforce_cv_only_service_ownership(self) -> None:
        compose = read(COMPOSE)
        validator = read(VALIDATOR)
        self.assertIn("  cv:\n", compose)
        self.assertIn("  cvbot:\n", compose)
        self.assertNotIn("  cloudflared:\n", compose)
        self.assertNotIn("CF_TUNNEL_TOKEN", compose)
        self.assertNotIn("TUNNEL_TOKEN", compose)
        self.assertFalse(LEGACY_TUNNEL_EXAMPLE.exists())

        for marker in (
            "shared Cloudflare connector must not be owned by CV Compose",
            "Cloudflare tunnel token dependency must not be owned by CV Compose",
            "Compose must contain exactly the two CV-owned services",
            "shared Cloudflare connector must not be a CV Compose service",
            "cloudflared.env.example",
        ):
            self.assertIn(marker, validator)

    def test_readme_declares_host_owned_shared_ingress(self) -> None:
        text = read(README)
        for marker in (
            "shared Cloudflare Tunnel connector is host-wide infrastructure owned by",
            "`RPi5_main`",
            "systemd `cloudflared.service`",
            "does not own its token, container/image, lifecycle, readiness, canaries",
            "Host ingress origin: `http://127.0.0.1:8088/`",
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

    def test_cvbot_must_be_secure_before_nginx_and_public_gate(self) -> None:
        lines = [line.strip() for line in read(HELPER).splitlines()]
        cvbot_position = lines.index(
            "compose_runtime up -d --no-deps cvbot || return 1"
        )
        health_position = lines.index("wait_healthy cvbot 60 2 || return 1")
        security_position = lines.index("verify_cvbot_runtime_security || return 1")
        nginx_position = lines.index("compose_runtime up -d --no-deps cv || return 1")
        local_position = lines.index('http_ok "$LOCAL_URL" 10 3 || return 1')
        public_position = lines.index('http_ok "$PUBLIC_URL" 10 5 || return 1')
        self.assertLess(cvbot_position, health_position)
        self.assertLess(health_position, security_position)
        self.assertLess(security_position, nginx_position)
        self.assertLess(nginx_position, local_position)
        self.assertLess(local_position, public_position)

    def test_runtime_compose_is_pinned_to_canonical_file(self) -> None:
        text = read(HELPER)
        self.assertNotIn("COMPOSE_ENV_FILE", text)
        self.assertNotIn("--env-file", text)
        self.assertNotIn('cloudflared.env"', text)
        self.assertIn('docker compose -f docker-compose.yml "$@"', text)
        self.assertEqual(
            text.count('docker compose -f docker-compose.yml "$@"'),
            2,
        )
        self.assertNotIn('docker compose "$@"', text)

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
            "preserve_shared_ingress_boundary_on_rollback",
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
            "--exclude='stats.json'",
            "--exclude='bot/data/'",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("--exclude='cloudflared.env'", text)

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

    def test_failure_diagnostics_stay_application_scoped(self) -> None:
        text = read(HELPER)
        for marker in (
            "failed-source-sync-runtime",
            "failed-deploy-runtime",
            "failed-rollback-sync-runtime",
            "failed-rollback-ingress-boundary",
            "post-rollback-runtime",
            "failed-rollback-runtime",
            "CVBOT SECURITY",
            "CVBOT HEALTH HISTORY",
            "CVBOT LOGS",
        ):
            self.assertIn(marker, text)
        for forbidden in (
            "CLOUDFLARED LOGS",
            "CLOUDFLARED CANARY LOGS",
            "cloudflared-canary",
            "cv-cloudflared",
        ):
            self.assertNotIn(forbidden, text)

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
        self.assertIn("runtime CV assistant data must not be versioned", validator)
        self.assertIn("bot/data/*", gitignore)
        self.assertIn("!bot/data/.gitkeep", gitignore)

    def test_validation_uses_only_cv_application_env_placeholder(self) -> None:
        text = read(VALIDATOR)
        subprocess.run(["bash", "-n", str(VALIDATOR)], check=True)
        self.assertIn("create_placeholder()", text)
        self.assertIn('"$ROOT/bot/.env"', text)
        self.assertNotIn('"$ROOT/cloudflared.env"', text)
        self.assertNotIn("CF_TUNNEL_TOKEN=", text)
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

    def test_cvbot_client_secret_is_validated_without_disclosure(self) -> None:
        helper = read(HELPER)
        for marker in (
            "validate_cvbot_runtime_secret()",
            'values.get("CLIENT_KEY_SECRET", "")',
            "len(decoded) < 32",
            "hmac.compare_digest(secret, provider)",
            "CVBOT_CLIENT_KEY_SECRET=PASS",
            "validate_cvbot_runtime_secret || return 1",
        ):
            self.assertIn(marker, helper)
        for forbidden in (
            'echo "$CLIENT_KEY_SECRET"',
            'echo "$LLM_API_KEY"',
            'printf "%s" "$CLIENT_KEY_SECRET"',
            'printf "%s" "$LLM_API_KEY"',
        ):
            self.assertNotIn(forbidden, helper)


if __name__ == "__main__":
    unittest.main()
