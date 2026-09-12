from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check-public-artifact-privacy.py"
SPEC = importlib.util.spec_from_file_location("check_public_artifact_privacy", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load public artifact privacy scanner: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
POLICY = MODULE.load_policy(ROOT / "security" / "public-artifact-privacy.json")


class PublicArtifactPrivacyTests(unittest.TestCase):
    def test_canonical_generated_public_artifacts_pass(self) -> None:
        artifacts, findings = MODULE.scan_repository(ROOT, POLICY)
        self.assertEqual(findings, [])
        self.assertTrue(any(path.endswith(".html") for path in artifacts))
        self.assertTrue(any(path.endswith(".json") for path in artifacts))
        self.assertTrue(any(path.endswith(".pdf") for path in artifacts))

    def test_address_publication_authorization_remains_false(self) -> None:
        self.assertIs(POLICY["ADDRESS_PUBLICATION_AUTHORIZED"], False)

    def test_synthetic_private_classes_fail_without_echoing_values(self) -> None:
        phone = "+" + " ".join(("999", "555", "010", "463"))
        address = " ".join(("999", "Example", "Street"))
        email = "synthetic" + "@" + "example.invalid"
        credential = "api_key=" + "synthetic_private_token_463"
        marker = "PRIVATE_" + "ONLY_FIXTURE_463"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_root = root / "html"
            artifact_root.mkdir()
            artifact = artifact_root / "synthetic.html"
            artifact.write_text("\n".join((phone, address, email, credential, marker)), encoding="utf-8")
            _, findings = MODULE.scan_repository(root, POLICY)
        rules = {finding.rule for finding in findings}
        self.assertEqual(
            rules,
            {"protected_phone", "street_address", "unexpected_email", "credential_material", "private_fixture_marker"},
        )
        diagnostics = MODULE.format_findings(findings)
        for value in (phone, address, email, credential, marker):
            self.assertNotIn(value, diagnostics)

    def test_intentionally_public_email_is_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_root = root / "html"
            artifact_root.mkdir()
            (artifact_root / "public.html").write_text("Contact: andris@rozkalns.net", encoding="utf-8")
            _, findings = MODULE.scan_repository(root, POLICY)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
