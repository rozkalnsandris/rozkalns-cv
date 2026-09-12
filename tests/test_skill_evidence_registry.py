import json
from pathlib import Path
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "content" / "profile.json"
EVIDENCE_PATH = ROOT / "content" / "evidence.json"


class SkillEvidenceRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        cls.registry = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_registry_points_to_canonical_profile_without_redefining_levels(self) -> None:
        self.assertEqual(self.registry["schema_version"], 1)
        self.assertEqual(self.registry["canonical_profile"], "content/profile.json")

        policy = self.registry["policy"]
        self.assertEqual(policy["proficiency_source"], "content/profile.json#skills")
        self.assertFalse(policy["mapping_changes_proficiency"])
        self.assertEqual(policy["learning_default"], "unproven")

        forbidden_keys = {"level", "proficiency", "category", "skill_level"}

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)

        walk(self.registry)

    def test_all_core_skills_have_public_evidence(self) -> None:
        mappings = self.registry["skill_evidence"]
        core = self.profile["skills"]["core"]

        missing = [skill for skill in core if not mappings.get(skill)]
        self.assertEqual(missing, [], f"core skills without evidence: {missing}")

    def test_mappings_only_reference_canonical_non_learning_skills(self) -> None:
        skills = self.profile["skills"]
        all_skills = {
            skill
            for group in skills.values()
            for skill in group
        }
        learning = set(skills["learning"])
        mapped = set(self.registry["skill_evidence"])

        self.assertTrue(mapped.issubset(all_skills))
        self.assertTrue(mapped.isdisjoint(learning))

    def test_evidence_ids_are_defined_and_used(self) -> None:
        evidence = self.registry["evidence"]
        mappings = self.registry["skill_evidence"]
        referenced = {evidence_id for evidence_ids in mappings.values() for evidence_id in evidence_ids}
        undefined = referenced - set(evidence)
        project_used = {evidence_id for evidence_id, item in evidence.items() if item["project_ids"]}
        unused = set(evidence) - referenced - project_used
        self.assertEqual(undefined, set(), f"undefined evidence ids: {undefined}")
        self.assertEqual(unused, set(), f"unused evidence ids: {unused}")

    def test_repository_file_evidence_is_local_public_and_current(self) -> None:
        allowed_hosts = set(self.registry["policy"]["allowed_url_hosts"])
        self.assertEqual(allowed_hosts, {"github.com", "rozkalns.net"})

        for evidence_id, item in self.registry["evidence"].items():
            with self.subTest(evidence_id=evidence_id):
                self.assertEqual(item["kind"], "repository_file")
                repository = item["repository"]
                self.assertRegex(repository, r"^rozkalnsandris/[A-Za-z0-9_.-]+$")
                path_text = item["path"]
                self.assertIsInstance(path_text, str)
                self.assertNotEqual(path_text, "")
                path = Path(path_text)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                if repository == "rozkalnsandris/rozkalns-cv":
                    self.assertTrue((ROOT / path).is_file(), f"stale local evidence path: {path_text}")
                parsed = urlparse(item["url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertIn(parsed.hostname, allowed_hosts)
                self.assertIsNone(parsed.username)
                self.assertIsNone(parsed.password)
                self.assertEqual(parsed.query, "")
                self.assertEqual(parsed.fragment, "")
                self.assertEqual(item["url"], f"https://github.com/{repository}/blob/main/{path_text}")

    def test_project_links_reference_existing_canonical_projects(self) -> None:
        project_ids = {project["id"] for project in self.profile["projects"]}

        for evidence_id, item in self.registry["evidence"].items():
            with self.subTest(evidence_id=evidence_id):
                linked = item["project_ids"]
                self.assertIsInstance(linked, list)
                self.assertEqual(len(linked), len(set(linked)))
                self.assertTrue(set(linked).issubset(project_ids))

    def test_profile_skill_taxonomy_has_no_duplicate_claims(self) -> None:
        groups = self.profile["skills"]
        flattened = [skill for group in groups.values() for skill in group]
        self.assertEqual(len(flattened), len(set(flattened)))


if __name__ == "__main__":
    unittest.main()
