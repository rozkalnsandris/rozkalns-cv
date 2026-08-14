from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = '<link rel="canonical" href="https://rozkalns.net/">'
OG_URL = '<meta property="og:url" content="https://rozkalns.net/">'
OG_IMAGE = '<meta property="og:image" content="https://rozkalns.net/photo.jpg">'


class SeoCanonicalContractTest(unittest.TestCase):
    def test_source_and_generated_html_publish_one_canonical(self):
        for relative in ("frontend/index.html", "html/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(html.count(CANONICAL), 1, relative)
            self.assertEqual(html.count(OG_URL), 1, relative)
            self.assertEqual(html.count(OG_IMAGE), 1, relative)

    def test_preview_image_is_crawlable(self):
        robots = (ROOT / "html/robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertNotIn("Disallow: /photo.jpg", robots)


if __name__ == "__main__":
    unittest.main()
