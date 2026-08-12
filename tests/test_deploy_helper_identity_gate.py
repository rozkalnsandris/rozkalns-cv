from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
LEGACY_WORKFLOW = WORKFLOWS / "deploy-main.yml"
FORBIDDEN_SELF_HOSTED_MARKERS = (
    "self-hosted",
    "rozkalns-cv-release",
    "/usr/local/sbin/rozkalns-cv-deploy-main",
)


class LegacyDeployWorkflowRetirementTests(unittest.TestCase):
    def test_legacy_deploy_workflow_is_absent(self) -> None:
        self.assertFalse(
            LEGACY_WORKFLOW.exists(),
            "retired public-repository self-hosted deploy workflow must stay removed",
        )

    def test_active_workflows_do_not_target_legacy_cv_runner(self) -> None:
        workflow_files = sorted(
            path
            for pattern in ("*.yml", "*.yaml")
            for path in WORKFLOWS.glob(pattern)
        )
        self.assertTrue(workflow_files, "at least one CI workflow must remain")

        for path in workflow_files:
            text = path.read_text(encoding="utf-8")
            for marker in FORBIDDEN_SELF_HOSTED_MARKERS:
                with self.subTest(workflow=path.name, marker=marker):
                    self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
