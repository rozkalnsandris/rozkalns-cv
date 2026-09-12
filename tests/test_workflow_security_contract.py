from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_workflow_security.py"
SPEC = importlib.util.spec_from_file_location("check_workflow_security", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load workflow security validator: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate_repository = MODULE.validate_repository
validate_workflow_text = MODULE.validate_workflow_text


class WorkflowSecurityContractTests(unittest.TestCase):
    def test_repository_workflows_match_explicit_security_contract(self) -> None:
        validate_repository(ROOT)

    def test_write_permission_is_rejected(self) -> None:
        workflow = """permissions:\n  contents: write\njobs:\n  validate:\n    runs-on: ubuntu-24.04\n    timeout-minutes: 10\n"""
        with self.assertRaisesRegex(ValueError, "permissions must be exactly"):
            validate_workflow_text("ci.yml", workflow)

    def test_local_job_without_timeout_is_rejected(self) -> None:
        workflow = """permissions:\n  contents: read\njobs:\n  validate:\n    runs-on: ubuntu-24.04\n"""
        with self.assertRaisesRegex(ValueError, "missing timeout-minutes"):
            validate_workflow_text("ci.yml", workflow)

    def test_unbounded_timeout_is_rejected(self) -> None:
        workflow = """permissions:\n  contents: read\njobs:\n  validate:\n    runs-on: ubuntu-24.04\n    timeout-minutes: 120\n"""
        with self.assertRaisesRegex(ValueError, "must be 1..60"):
            validate_workflow_text("ci.yml", workflow)

    def test_reusable_job_requires_allowlist_and_immutable_pin(self) -> None:
        workflow = """permissions:\n  contents: read\njobs:\n  github-only-policy-drift:\n    uses: rozkalnsandris/ops-workflows/.github/workflows/github-only-policy-drift.yml@main\n"""
        with self.assertRaisesRegex(ValueError, "immutable 40-hex pin"):
            validate_workflow_text("github-only-policy-drift.yml", workflow)

    def test_unknown_workflow_requires_explicit_permission_policy(self) -> None:
        workflow = """permissions:\n  contents: read\njobs:\n  validate:\n    runs-on: ubuntu-24.04\n    timeout-minutes: 10\n"""
        with self.assertRaisesRegex(ValueError, "lacks explicit permission policy"):
            validate_workflow_text("new-workflow.yml", workflow)


if __name__ == "__main__":
    unittest.main()
