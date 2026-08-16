from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


class GitHubProjectLinksTest(unittest.TestCase):
    def test_compact_public_repo_proof_uses_existing_profile_link(self) -> None:
        self.assertIn("https://github.com/rozkalnsandris", INDEX)
        for repo in ("hermes-tech", "RPi5_main", "hermes-deals", "control-center"):
            self.assertIn(repo, INDEX)
        self.assertNotIn("YouTube_Marcim", INDEX)
        self.assertNotIn("hermes-email-skill", INDEX)
        self.assertNotIn("api.github.com", INDEX)


if __name__ == "__main__":
    unittest.main()
