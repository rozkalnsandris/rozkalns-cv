from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-main.yml"


class DeployHelperIdentityGateTests(unittest.TestCase):
    def test_deploy_verifies_installed_helper_before_mutation(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        gate = "Verify installed deploy helper matches target source"
        deploy = "Deploy queued merge SHA"
        self.assertIn(gate, text)
        self.assertIn("contents: read", text)
        self.assertIn("git hash-object \"$helper\"", text)
        self.assertIn("runner/release/rozkalns-cv-deploy-main", text)
        self.assertIn("target helper blob SHA is invalid", text)
        self.assertIn("test \"$actual_blob\" = \"$expected_blob\"", text)
        self.assertIn("root:root:755", text)
        self.assertIn("INSTALLED_HELPER_IDENTITY=PASS", text)
        self.assertLess(text.index(gate), text.index(deploy))
        self.assertLess(
            text.index("test \"$actual_blob\" = \"$expected_blob\""),
            text.index("sudo --non-interactive /usr/local/sbin/rozkalns-cv-deploy-main"),
        )


if __name__ == "__main__":
    unittest.main()
