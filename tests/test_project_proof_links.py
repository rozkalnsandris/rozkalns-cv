import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SLOT_RE = re.compile(
    r'<span data-proof-projects="([^"]+)" data-proof-evidence-ids="([^"]+)"></span>'
)


class ProjectProofLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((ROOT / "content/evidence.json").read_text(encoding="utf-8"))
        cls.source = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        cls.slots = SLOT_RE.findall(cls.source)

    def test_featured_proof_slots_cover_three_to_five_canonical_projects(self) -> None:
        canonical = {project["id"] for project in self.profile["projects"]}
        featured: set[str] = set()
        self.assertGreaterEqual(len(self.slots), 1)
        for project_text, evidence_text in self.slots:
            project_ids = project_text.split()
            evidence_ids = evidence_text.split()
            self.assertEqual(len(project_ids), len(set(project_ids)))
            self.assertEqual(len(evidence_ids), len(set(evidence_ids)))
            self.assertTrue(set(project_ids).issubset(canonical))
            covered: set[str] = set()
            for evidence_id in evidence_ids:
                item = self.registry["evidence"][evidence_id]
                linked = set(item["project_ids"])
                self.assertTrue(linked.intersection(project_ids))
                covered.update(linked.intersection(project_ids))
            self.assertEqual(covered, set(project_ids))
            featured.update(project_ids)
        self.assertGreaterEqual(len(featured), 3)
        self.assertLessEqual(len(featured), 5)

    def test_proof_slots_reference_only_approved_stable_public_urls(self) -> None:
        allowed_hosts = set(self.registry["policy"]["allowed_url_hosts"])
        selected = {evidence_id for _, ids in self.slots for evidence_id in ids.split()}
        self.assertNotIn("https://", self.source[self.source.find("data-proof-projects"):self.source.find("data-proof-projects") + 220])
        for evidence_id in selected:
            item = self.registry["evidence"][evidence_id]
            parsed = urlparse(item["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.hostname, allowed_hosts)
            self.assertIsNone(parsed.username)
            self.assertIsNone(parsed.password)
            self.assertEqual(parsed.query, "")
            self.assertEqual(parsed.fragment, "")
            if parsed.hostname == "github.com":
                self.assertIn("/blob/main/", parsed.path)
                self.assertIsNone(re.search(r"/blob/[0-9a-f]{40}/", parsed.path))

    def test_generated_locales_resolve_registry_urls_without_localizing_urls(self) -> None:
        selected = {evidence_id for _, ids in self.slots for evidence_id in ids.split()}
        expected = {
            evidence_id: self.registry["evidence"][evidence_id]
            for evidence_id in selected
        }
        for language in ("en", "de", "lv"):
            page = (ROOT / "html" / language / "index.html").read_text(encoding="utf-8")
            with self.subTest(language=language):
                self.assertNotIn("data-proof-projects", page)
                self.assertEqual(page.count('class="tech-tag github-row project-proof-link"'), len(selected))
                for evidence_id, item in expected.items():
                    filename = Path(item["path"]).name
                    self.assertIn(f'data-proof-evidence-id="{evidence_id}"', page)
                    self.assertIn(f'href="{item["url"]}"', page)
                    self.assertIn(f'>{filename} ↗</a>', page)

    def test_project_cards_declare_the_same_canonical_ids_as_their_proof_slots(self) -> None:
        for project_text, _evidence_text in self.slots:
            self.assertIn(f'data-project-ids="{project_text}"', self.source)


if __name__ == "__main__":
    unittest.main()
