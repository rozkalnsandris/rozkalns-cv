import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMAGE_ALTS = {
    "en": "Portrait of Andris Rožkalns",
    "de": "Porträt von Andris Rožkalns",
    "lv": "Andra Rožkalna portrets",
}


class SeoPolicy398Test(unittest.TestCase):
    def test_localized_social_alt_and_profile_language(self):
        for language, image_alt in IMAGE_ALTS.items():
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(f'<meta property="og:image:alt" content="{image_alt}">', html)
            self.assertIn(f'<meta name="twitter:image:alt" content="{image_alt}">', html)
            match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            self.assertIsNotNone(match, language)
            profile = json.loads(match.group(1))
            self.assertEqual(profile.get("@type"), "ProfilePage")
            self.assertEqual(profile.get("inLanguage"), language)
            self.assertEqual(profile.get("@id"), f"https://rozkalns.net/{language}/#profile")
            self.assertEqual(profile["mainEntity"].get("@id"), "https://rozkalns.net/#person")

    def test_root_redirect_is_deliberate_and_preserves_query(self):
        nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
        root = re.search(r"location = / \{(.*?)\n    \}", nginx, re.S)
        self.assertIsNotNone(root)
        block = root.group(1)
        self.assertIn("return 308 /en/$is_args$args;", block)
        self.assertNotIn("try_files /index.html", block)

    def test_localized_pdfs_are_downloadable_but_noindex(self):
        nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn(r"location ~ ^/cv(?:-de|-lv)?\.pdf$ {", nginx)
        self.assertIn('add_header X-Robots-Tag "noindex, nofollow" always;', nginx)
        for relative in ("html/cv.pdf", "html/cv-de.pdf", "html/cv-lv.pdf"):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
