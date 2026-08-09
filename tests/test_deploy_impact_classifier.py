from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runner" / "pull-deploy" / "classify_deploy_impact.py"

spec = importlib.util.spec_from_file_location("cv_deploy_impact_classifier", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DeployImpactClassifierTests(unittest.TestCase):
    def test_docs_and_tests_need_no_deploy(self) -> None:
        payload = module.classify_paths(
            ["README.md", "docs/CVBOT_HEALTH.md", "tests/test_bot.py"]
        )
        self.assertEqual(payload["classification"], module.NO_DEPLOY)
        self.assertFalse(payload["control_plane_changed"])

    def test_ordinary_frontend_and_app_code_is_auto_safe(self) -> None:
        payload = module.classify_paths(
            [
                "frontend/features/chat.mjs",
                "html/index.html",
                "content/profile.json",
                "bot/chat_entry.py",
            ]
        )
        self.assertEqual(payload["classification"], module.AUTO_DEPLOY_SAFE)
        self.assertFalse(payload["control_plane_changed"])

    def test_runtime_dependencies_and_control_plane_require_manual_rollout(self) -> None:
        for path in (
            "bot/Dockerfile",
            "bot/.env.example",
            "bot/storage.py",
            "docker-compose.yml",
            "package-lock.json",
            ".github/workflows/ci.yml",
            "runner/release/rozkalns-cv-deploy-main",
            "scripts/validate-source.sh",
            "mystery/runtime.conf",
        ):
            with self.subTest(path=path):
                payload = module.classify_paths([path])
                self.assertEqual(
                    payload["classification"], module.MANUAL_ROLLOUT_REQUIRED
                )

    def test_db_and_host_boundaries_are_highest_impact(self) -> None:
        payload = module.classify_paths(
            [
                "frontend/app.mjs",
                "migrations/0001.sql",
                "ops/systemd/rozkalns-cv.service",
            ]
        )
        self.assertEqual(payload["classification"], module.DB_HOST_APPLY_REQUIRED)

    def test_mixed_change_uses_highest_severity(self) -> None:
        payload = module.classify_paths(
            [
                "docs/CVBOT_CHAT_ADMISSION.md",
                "frontend/features/chat.mjs",
                "docker-compose.yml",
            ]
        )
        self.assertEqual(payload["classification"], module.MANUAL_ROLLOUT_REQUIRED)

    def test_control_plane_flag_is_exact(self) -> None:
        self.assertTrue(
            module.classify_paths(["runner/pull-deploy/controller"])[
                "control_plane_changed"
            ]
        )
        self.assertTrue(
            module.classify_paths([".github/workflows/deploy-main.yml"])[
                "control_plane_changed"
            ]
        )
        self.assertFalse(
            module.classify_paths(["docker-compose.yml"])["control_plane_changed"]
        )

    def test_unsafe_path_fails_closed(self) -> None:
        for path in ("", "/etc/passwd", "../runtime", "frontend/../runtime"):
            with self.subTest(path=path):
                with self.assertRaises(module.ClassifierError):
                    module.classify_paths([path])


if __name__ == "__main__":
    unittest.main()
