from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


class GitHubProjectLinksTest(unittest.TestCase):
    def test_public_repo_proof_uses_sidebar_and_excludes_private_repos(self) -> None:
        self.assertIn('<div class=skill-row id=github-projects>', INDEX)
        self.assertNotIn('<section id="github-projects">', INDEX)
        self.assertIn('rel=me>GitHub</a>', INDEX)
        start = INDEX.index('<div class=skill-row id=github-projects>')
        block = INDEX[start:INDEX.index('</dl>', start)]
        selected = (
            "linux-operations-lab",
            "RPi5_main",
            "rozkalns-cv",
            "dashboard_RPi5",
            "rozkalns-control-center",
        )
        for repo in selected:
            self.assertIn(f"//github.com/rozkalnsandris/{repo}", block)
        self.assertEqual(block.count('class="tech-tag has-tech-icon github-row"'), 5)
        self.assertNotIn('<details', block)
        self.assertNotIn('<summary', block)
        self.assertIn('<dt>GitHub <span data-i18n=projects_title>Projects</span></dt>', block)
        for repo in ("hermes-tech", "hermes-deals", "home-assistant-config", "balcony-irrigation-esp32", "ops-workflows"):
            self.assertNotIn(repo, block)
        self.assertNotIn("YouTube_Marcim", INDEX)
        self.assertNotIn("hermes-email-skill", INDEX)
        self.assertNotIn("api.github.com", INDEX)

if __name__ == "__main__":
    unittest.main()
