from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-vacancy-fit.py"
FIXTURES = ROOT / "tests" / "fixtures" / "vacancy"
PROFILE = ROOT / "content" / "profile.json"
EVIDENCE = ROOT / "content" / "evidence.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VacancyFitCheckerTests(unittest.TestCase):
    def run_checker(self, *args: str, stdin: str | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=stdin,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd or ROOT,
            check=False,
        )

    def test_synthetic_vacancy_preserves_canonical_proficiency_boundaries(self) -> None:
        text = (FIXTURES / "synthetic-en.txt").read_text(encoding="utf-8")
        completed = self.run_checker("--json", stdin=text)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        categories = payload["categories"]

        self.assertEqual(
            [item["canonical_skill"] for item in categories["evidenced"]],
            ["Docker Compose", "Linux administration"],
        )
        self.assertEqual(
            [item["canonical_skill"] for item in categories["working"]],
            ["Python", "REST APIs"],
        )
        self.assertEqual(categories["learning"], [])
        self.assertEqual(
            [item["canonical_skill"] for item in categories["foundation"]],
            ["Networking"],
        )
        self.assertEqual(
            [item["requirement"] for item in categories["not_in_canonical_profile"]],
            ["Kubernetes"],
        )

    def test_evidenced_items_use_only_canonical_registry_urls(self) -> None:
        text = (FIXTURES / "synthetic-en.txt").read_text(encoding="utf-8")
        payload = json.loads(self.run_checker("--json", stdin=text).stdout)
        registry = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        allowed = {
            item["url"]
            for item in registry["evidence"].values()
        }
        for item in payload["categories"]["evidenced"]:
            self.assertGreater(len(item["evidence"]), 0)
            self.assertTrue({proof["url"] for proof in item["evidence"]}.issubset(allowed))

    def test_learning_and_foundation_items_are_never_presented_as_proven(self) -> None:
        text = "Basic SQL Networking SSH HTML/CSS Terraform Ansible AWS Cloud"
        payload = json.loads(self.run_checker("--json", stdin=text).stdout)
        categories = payload["categories"]
        self.assertEqual(
            [item["canonical_skill"] for item in categories["learning"]],
            ["Basic SQL"],
        )
        self.assertEqual(
            [item["canonical_skill"] for item in categories["foundation"]],
            ["HTML/CSS", "Networking", "SSH/FTP"],
        )
        for category in ("learning", "foundation"):
            for item in categories[category]:
                self.assertEqual(item["evidence"], [])
        canonical = {
            item["canonical_skill"]
            for category in ("evidenced", "working", "learning", "foundation")
            for item in categories[category]
        }
        for removed in ("Terraform", "Ansible", "AWS Cloud"):
            self.assertNotIn(removed, canonical)

    def test_compose_alias_and_unsupported_terms_are_conservative(self) -> None:
        text = (FIXTURES / "synthetic-de.txt").read_text(encoding="utf-8")
        payload = json.loads(self.run_checker("--json", stdin=text).stdout)
        categories = payload["categories"]
        self.assertIn(
            "Docker Compose",
            [item["canonical_skill"] for item in categories["evidenced"]],
        )
        self.assertIn(
            "Jenkins",
            [item["requirement"] for item in categories["not_in_canonical_profile"]],
        )
        self.assertEqual(categories["learning"], [])
        canonical = {
            item["canonical_skill"]
            for category in ("evidenced", "working", "learning", "foundation")
            for item in categories[category]
        }
        self.assertNotIn("Ansible", canonical)

    def test_json_output_is_deterministic_and_does_not_echo_source_text(self) -> None:
        text = (FIXTURES / "synthetic-en.txt").read_text(encoding="utf-8")
        first = self.run_checker("--json", stdin=text)
        second = self.run_checker("--json", stdin=text)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertNotIn(text.strip(), first.stdout)
        payload = json.loads(first.stdout)
        self.assertEqual(payload["source"], "stdin")
        self.assertNotIn("score", payload)
        self.assertNotIn("probability", payload)

    def test_local_file_mode_does_not_publish_file_path_or_vacancy_text(self) -> None:
        fixture = FIXTURES / "synthetic-de.txt"
        completed = self.run_checker("--json", "--file", str(fixture))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["source"], "local-file")
        self.assertNotIn(str(fixture), completed.stdout)
        self.assertNotIn(fixture.read_text(encoding="utf-8").strip(), completed.stdout)

    def test_execution_does_not_mutate_canonical_data_or_cwd(self) -> None:
        before = {PROFILE: sha256(PROFILE), EVIDENCE: sha256(EVIDENCE)}
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            completed = self.run_checker("--json", stdin="Linux Kubernetes", cwd=cwd)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(list(cwd.iterdir()), [])
        after = {PROFILE: sha256(PROFILE), EVIDENCE: sha256(EVIDENCE)}
        self.assertEqual(before, after)

    def test_checker_has_no_network_or_persistent_storage_capability(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.isdisjoint({"http", "logging", "requests", "socket", "sqlite3", "subprocess", "tempfile", "urllib"}))
        self.assertNotIn("write_text", source)
        self.assertNotIn("write_bytes", source)
        self.assertNotIn("mkdir(", source)

    def test_empty_and_oversized_input_fail_without_echoing_input(self) -> None:
        empty = self.run_checker("--json", stdin="")
        self.assertEqual(empty.returncode, 2)
        self.assertEqual(empty.stdout, "")
        oversized_text = "X" * 262_145
        oversized = self.run_checker("--json", stdin=oversized_text)
        self.assertEqual(oversized.returncode, 2)
        self.assertEqual(oversized.stdout, "")
        self.assertNotIn(oversized_text[:100], oversized.stderr)


if __name__ == "__main__":
    unittest.main()
