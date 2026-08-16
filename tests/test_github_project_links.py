from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


class GitHubProjectLinksTest(unittest.TestCase):
    def test_public_repo_proof_uses_sidebar_and_excludes_private_repos(self) -> None:
        self.assertIn('<div class=skill-row id=github-projects>', INDEX)
        self.assertNotIn('<section id="github-projects">', INDEX)
        self.assertIn('rel=me>GitHub</a>', INDEX)
        selected = ("hermes-tech", "RPi5_main", "hermes-deals", "rozkalns-control-center", "dashboard_RPi5")
        remaining = ("home-assistant-config", "balcony-irrigation-esp32", "rozkalns-cv", "ops-workflows")
        for repo in selected:
            self.assertIn(f"//github.com/rozkalnsandris/{repo}", INDEX)
        for repo in remaining:
            self.assertIn(repo, INDEX)
        self.assertIn('<details class=project-list>', INDEX)
        self.assertIn('<dt>GitHub <span data-i18n=projects_title>Projects</span></dt>', INDEX)
        self.assertIn('<summary class="tech-tag">+ 4 <span data-i18n=projects_title>Projects</span></summary>', INDEX)
        self.assertNotIn("YouTube_Marcim", INDEX)
        self.assertNotIn("hermes-email-skill", INDEX)
        self.assertNotIn("api.github.com", INDEX)


if __name__ == "__main__":
    unittest.main()
