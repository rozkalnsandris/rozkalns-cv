from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SbomContractTests(unittest.TestCase):
    def test_generated_sboms_are_current_and_cyclonedx(self) -> None:
        run = subprocess.run(["python3", str(ROOT / "scripts" / "generate-sbom.py"), "--check"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        for filename, source in (("sbom-python.cdx.json", "bot/requirements.txt"), ("sbom-node.cdx.json", "package-lock.json")):
            doc = json.loads((ROOT / "security" / filename).read_text(encoding="utf-8"))
            self.assertEqual(doc["bomFormat"], "CycloneDX")
            self.assertEqual(doc["specVersion"], "1.6")
            self.assertEqual(doc["version"], 1)
            self.assertTrue(doc["components"])
            self.assertTrue(doc["dependencies"])
            props = {row["name"]: row["value"] for row in doc["metadata"]["properties"]}
            self.assertEqual(props["rozkalns:source-lock"], source)

    def test_python_sbom_matches_locked_package_set(self) -> None:
        import re
        lock = (ROOT / "bot" / "requirements.txt").read_text(encoding="utf-8")
        expected = {(m.group(1).lower().replace("_", "-"), m.group(2)) for m in re.finditer(r"(?m)^([A-Za-z0-9_.-]+)==([^\s\\]+)", lock)}
        doc = json.loads((ROOT / "security" / "sbom-python.cdx.json").read_text(encoding="utf-8"))
        actual = {(row["name"], row["version"]) for row in doc["components"]}
        self.assertEqual(actual, expected)

    def test_node_sbom_matches_lock_package_set(self) -> None:
        lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
        expected = {(path.rsplit("node_modules/", 1)[-1], row["version"]) for path, row in lock["packages"].items() if path}
        doc = json.loads((ROOT / "security" / "sbom-node.cdx.json").read_text(encoding="utf-8"))
        actual = {(row["name"], row["version"]) for row in doc["components"]}
        self.assertEqual(actual, expected)

    def test_sboms_do_not_embed_local_paths_or_secrets(self) -> None:
        for filename in ("sbom-python.cdx.json", "sbom-node.cdx.json"):
            text = (ROOT / "security" / filename).read_text(encoding="utf-8")
            self.assertNotIn("/home/", text)
            self.assertNotIn("GITHUB_TOKEN", text)
            self.assertNotIn("OPENAI_API_KEY", text)


if __name__ == "__main__":
    unittest.main()
