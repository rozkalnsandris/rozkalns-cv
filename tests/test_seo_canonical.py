from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TITLE = "Andris Rožkalns · DevOps &amp; Linux Engineer"
DESCRIPTION = (
    "Andris Rožkalns — self-taught DevOps and Linux engineer in Dortmund, "
    "building and operating a production Raspberry Pi 5 homelab."
)
CANONICAL = '<link rel="canonical" href="https://rozkalns.net/">'
OG_TITLE = f'<meta property="og:title" content="{TITLE}">'
OG_URL = '<meta property="og:url" content="https://rozkalns.net/">'
OG_TYPE = '<meta property="og:type" content="website">'
OG_DESCRIPTION = f'<meta property="og:description" content="{DESCRIPTION}">'
OG_IMAGE = '<meta property="og:image" content="https://rozkalns.net/photo.jpg">'
OG_IMAGE_ALT = '<meta property="og:image:alt" content="Portrait of Andris Rožkalns">'
TWITTER_CARD = '<meta name="twitter:card" content="summary_large_image">'
TWITTER_TITLE = f'<meta name="twitter:title" content="{TITLE}">'
TWITTER_DESCRIPTION = f'<meta name="twitter:description" content="{DESCRIPTION}">'
TWITTER_IMAGE = '<meta name="twitter:image" content="https://rozkalns.net/photo.jpg">'
TWITTER_IMAGE_ALT = '<meta name="twitter:image:alt" content="Portrait of Andris Rožkalns">'
META_DESCRIPTION = f'<meta name="description" content="{DESCRIPTION}">'


class SeoCanonicalContractTest(unittest.TestCase):
    def test_source_and_generated_html_publish_complete_profile_metadata(self):
        for relative in ("frontend/index.html", "html/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            for marker in (
                META_DESCRIPTION,
                CANONICAL,
                OG_TITLE,
                OG_URL,
                OG_TYPE,
                OG_DESCRIPTION,
                OG_IMAGE,
                OG_IMAGE_ALT,
                TWITTER_CARD,
                TWITTER_TITLE,
                TWITTER_DESCRIPTION,
                TWITTER_IMAGE,
                TWITTER_IMAGE_ALT,
            ):
                self.assertEqual(html.count(marker), 1, f"{relative}: {marker}")
            self.assertLess(html.index(OG_IMAGE), html.index(OG_IMAGE_ALT), relative)
            self.assertLess(html.index(TWITTER_IMAGE), html.index(TWITTER_IMAGE_ALT), relative)

    def test_preview_image_is_crawlable(self):
        robots = (ROOT / "html/robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertNotIn("Disallow: /photo.jpg", robots)


if __name__ == "__main__":
    unittest.main()
