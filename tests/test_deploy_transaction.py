from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"


def run_library(commands: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["ROZKALNS_CV_DEPLOY_LIBRARY_ONLY"] = "1"
    script = f"source {shlex.quote(str(HELPER))}\n{commands}\n"
    return subprocess.run(
        ["bash", "-c", script],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class DeployTransactionBehaviorTests(unittest.TestCase):
    def test_capacity_comparison_is_bounded(self) -> None:
        result = run_library(
            "capacity_ok 1000 100 999 99\n"
            "! capacity_ok 998 100 999 99\n"
            "! capacity_ok 1000 98 999 99"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_atomic_state_update_replaces_complete_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_file = state_dir / "current-sha"
            state_file.write_text("old\n", encoding="utf-8")
            target = "a" * 40
            result = run_library(
                f"STATE_DIR={shlex.quote(str(state_dir))}\n"
                f"STATE_FILE={shlex.quote(str(state_file))}\n"
                f"TARGET_SHA={target}\n"
                "write_state_atomically\n"
                "cat \"$STATE_FILE\""
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, target + "\n")
            self.assertEqual(
                state_file.read_text(encoding="utf-8"), target + "\n"
            )

    def test_failed_atomic_state_update_keeps_old_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_file = state_dir / "current-sha"
            state_file.write_text("old\n", encoding="utf-8")
            missing_state_dir = state_dir / "missing"
            result = run_library(
                f"STATE_DIR={shlex.quote(str(missing_state_dir))}\n"
                f"STATE_FILE={shlex.quote(str(state_file))}\n"
                f"TARGET_SHA={'b' * 40}\n"
                "if write_state_atomically; then exit 99; fi"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                state_file.read_text(encoding="utf-8"), "old\n"
            )

    def test_backup_pruning_enforces_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(7):
                path = root / f"backup-{index}"
                path.mkdir()
                stamp = 1_700_000_000 + index
                os.utime(path, (stamp, stamp))
            result = run_library(
                f"BACKUP_ROOT={shlex.quote(str(root))}\n"
                "BACKUP_RETENTION_COUNT=3\n"
                "BACKUP_RETENTION_DAYS=99999\n"
                "prune_backups\n"
                "find \"$BACKUP_ROOT\" -mindepth 1 -maxdepth 1 "
                "-type d | wc -l"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "3")

    def test_managed_backup_excludes_host_only_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            destination = root / "destination"
            (source / "html").mkdir(parents=True)
            (source / "bot" / "data").mkdir(parents=True)
            destination.mkdir()
            (source / "html" / "index.html").write_text(
                "ok", encoding="utf-8"
            )
            (source / "html" / "stats.json").write_text(
                "{}", encoding="utf-8"
            )
            (source / "legacy.env").write_text(
                "secret", encoding="utf-8"
            )
            (source / "bot" / ".env").write_text(
                "secret", encoding="utf-8"
            )
            (source / "bot" / "data" / "chat.jsonl").write_text(
                "private", encoding="utf-8"
            )
            result = run_library(
                f"managed_rsync {shlex.quote(str(source))} "
                f"{shlex.quote(str(destination))}\n"
                f"test -f {shlex.quote(str(destination / 'html' / 'index.html'))}\n"
                f"test ! -e {shlex.quote(str(destination / 'html' / 'stats.json'))}\n"
                f"test ! -e {shlex.quote(str(destination / 'legacy.env'))}\n"
                f"test ! -e {shlex.quote(str(destination / 'bot' / '.env'))}\n"
                f"test ! -e {shlex.quote(str(destination / 'bot' / 'data' / 'chat.jsonl'))}"
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_cvbot_runtime_security_gate_accepts_only_hardened_state(self) -> None:
        secure = {
            "user": "10001:10001",
            "readonly": True,
            "cap_add": None,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "pids": 128,
            "privileged": False,
            "mounts": [
                {
                    "Destination": "/app/data",
                    "RW": True,
                    "Type": "bind",
                }
            ],
        }
        secure_json = json.dumps(secure, separators=(",", ":"))
        result = run_library(
            "docker() { printf '%s\\n' "
            f"{shlex.quote(secure_json)}; }}\n"
            "verify_cvbot_runtime_security"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CVBOT_RUNTIME_SECURITY=PASS", result.stdout)
        self.assertIn("CVBOT_RUNTIME_USER=10001:10001", result.stdout)
        self.assertIn("CVBOT_ROOTFS_READ_ONLY=true", result.stdout)
        self.assertIn("CVBOT_CAP_DROP=ALL", result.stdout)
        self.assertIn("CVBOT_NO_NEW_PRIVILEGES=true", result.stdout)

        insecure = dict(secure)
        insecure["readonly"] = False
        insecure_json = json.dumps(insecure, separators=(",", ":"))
        rejected = run_library(
            "docker() { printf '%s\\n' "
            f"{shlex.quote(insecure_json)}; }}\n"
            "if verify_cvbot_runtime_security; then exit 99; fi"
        )
        self.assertEqual(rejected.returncode, 0, rejected.stderr)

    def test_rendered_compose_accepts_exactly_cv_and_cvbot(self) -> None:
        accepted = run_library(
            "compose_at() {\n"
            "  if [[ \"${3:-}\" == --services ]]; then\n"
            "    printf 'cv\\ncvbot\\n'\n"
            "  else\n"
            "    printf 'name: cv_default\\nsubnet: 172.19.0.0/16\\ngateway: 172.19.0.1\\n'\n"
            "  fi\n"
            "}\n"
            "validate_rendered_network /tmp/candidate"
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        rejected = run_library(
            "compose_at() {\n"
            "  if [[ \"${3:-}\" == --services ]]; then\n"
            "    printf 'cv\\ncvbot\\ncloudflared\\n'\n"
            "  else\n"
            "    printf 'name: cv_default\\nsubnet: 172.19.0.0/16\\ngateway: 172.19.0.1\\n'\n"
            "  fi\n"
            "}\n"
            "if validate_rendered_network /tmp/candidate; then exit 99; fi"
        )
        self.assertEqual(rejected.returncode, 0, rejected.stderr)

    def test_summary_proves_shared_ingress_is_not_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            evidence.mkdir()
            state = root / "current-sha"
            state.write_text("c" * 40 + "\n", encoding="utf-8")
            result = run_library(
                f"EVIDENCE_DIR={shlex.quote(str(evidence))}\n"
                f"STATE_FILE={shlex.quote(str(state))}\n"
                f"TARGET_SHA={'d' * 40}\n"
                "OLD_SHA=unknown\n"
                "DEPLOYED=true\n"
                "MUTATION_STARTED=true\n"
                "TRANSACTION_COMMITTED=true\n"
                "write_summary PASS false"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = (evidence / "summary.env").read_text(encoding="utf-8")
            self.assertIn("DEPLOY_RESULT=PASS", summary)
            self.assertIn("SHARED_INGRESS_CONTROLLED=false", summary)
            self.assertNotIn("CLOUDFLARED", summary)

    def test_uncommitted_failure_invokes_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "backup"
            (backup / "runtime").mkdir(parents=True)
            marker = root / "rollback-called"
            result = run_library(
                f"BACKUP={shlex.quote(str(backup))}\n"
                "MUTATION_STARTED=true\n"
                "TRANSACTION_COMMITTED=false\n"
                "ROLLBACK_ATTEMPTED=false\n"
                "EVIDENCE_READY=false\n"
                "WORK=''\nSTAGE=''\n"
                f"rollback() {{ printf called > {shlex.quote(str(marker))}; "
                "ROLLBACK_ATTEMPTED=true; return 0; }\n"
                "finish 23"
            )
            self.assertEqual(result.returncode, 23)
            self.assertEqual(
                marker.read_text(encoding="utf-8"), "called"
            )

    def test_committed_failure_does_not_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "backup"
            (backup / "runtime").mkdir(parents=True)
            marker = root / "rollback-called"
            result = run_library(
                f"BACKUP={shlex.quote(str(backup))}\n"
                "MUTATION_STARTED=true\n"
                "TRANSACTION_COMMITTED=true\n"
                "ROLLBACK_ATTEMPTED=false\n"
                "EVIDENCE_READY=false\n"
                "WORK=''\nSTAGE=''\n"
                f"rollback() {{ printf called > {shlex.quote(str(marker))}; "
                "return 0; }\n"
                "finish 17"
            )
            self.assertEqual(result.returncode, 17)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
