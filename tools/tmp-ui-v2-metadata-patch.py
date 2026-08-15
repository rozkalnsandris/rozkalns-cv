from pathlib import Path

DESCRIPTION = (
    "Andris Rožkalns — self-taught DevOps and Linux engineer in Dortmund, "
    "building and operating a production Raspberry Pi 5 homelab."
)

index = Path("frontend/index.html")
html = index.read_text(encoding="utf-8")

replacements = {
    '<meta name="description" content="Andris Rožkalns — self-taught DevOps and Linux engineer. This portfolio runs live from a Raspberry Pi 5 homelab.">':
        f'<meta name="description" content="{DESCRIPTION}">',
    '<meta property="og:description" content="Self-hosted multilingual CV with live homelab metrics and a sandboxed CV assistant.">':
        f'<meta property="og:description" content="{DESCRIPTION}">',
    '    "jobTitle": "Junior DevOps & Linux Engineer",':
        '    "jobTitle": "Junior DevOps & Linux Engineer",\n'
        f'    "description": "{DESCRIPTION}",',
    '  <meta name="twitter:card" content="summary_large_image">':
        '  <meta name="twitter:card" content="summary_large_image">\n'
        '  <meta name="twitter:title" content="Andris Rožkalns · DevOps &amp; Linux Engineer">\n'
        f'  <meta name="twitter:description" content="{DESCRIPTION}">\n'
        '  <meta name="twitter:image" content="https://rozkalns.net/photo.jpg">\n'
        '  <meta name="twitter:image:alt" content="Portrait of Andris Rožkalns">',
}

for old, new in replacements.items():
    if old not in html:
        raise SystemExit(f"expected metadata source fragment missing: {old}")
    html = html.replace(old, new, 1)
index.write_text(html, encoding="utf-8")

Path("tests/test_seo_canonical.py").write_text(
    '''from pathlib import Path
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
''',
    encoding="utf-8",
)

Path("tests/test_person_structured_data.py").write_text(
    '''import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = (
    "Andris Rožkalns — self-taught DevOps and Linux engineer in Dortmund, "
    "building and operating a production Raspberry Pi 5 homelab."
)
SCRIPT_RE = re.compile(
    r'<script type="application/ld\\+json">\\s*(.*?)\\s*</script>', re.DOTALL
)


def load_profile_page(relative):
    html = (ROOT / relative).read_text(encoding="utf-8")
    matches = SCRIPT_RE.findall(html)
    if len(matches) != 1:
        raise AssertionError(
            f"{relative}: expected exactly one JSON-LD script, got {len(matches)}"
        )
    return json.loads(matches[0])


class ProfilePageStructuredDataContractTest(unittest.TestCase):
    def test_source_and_generated_profile_data_match(self):
        source = load_profile_page("frontend/index.html")
        generated = load_profile_page("html/index.html")
        self.assertEqual(source, generated)
        self.assertEqual(source["@context"], "https://schema.org")
        self.assertEqual(source["@type"], "ProfilePage")
        self.assertEqual(source["@id"], "https://rozkalns.net/#profile")
        self.assertEqual(source["url"], "https://rozkalns.net/")

        person = source["mainEntity"]
        self.assertEqual(person["@type"], "Person")
        self.assertEqual(person["@id"], "https://rozkalns.net/#person")
        self.assertEqual(person["name"], "Andris Rožkalns")
        self.assertEqual(person["url"], "https://rozkalns.net/")
        self.assertEqual(person["image"], "https://rozkalns.net/photo.jpg")
        self.assertEqual(person["jobTitle"], "Junior DevOps & Linux Engineer")
        self.assertEqual(person["description"], DESCRIPTION)
        self.assertEqual(person["sameAs"], ["https://github.com/rozkalnsandris"])

    def test_description_is_visible_profile_truth(self):
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        self.assertIn("self-taught Linux and DevOps engineer based in Dortmund", html)
        self.assertIn("design, deploy and operate a production Raspberry Pi 5 homelab", html)
        self.assertEqual(html.count(f'content="{DESCRIPTION}"'), 3)

    def test_location_languages_and_privacy_boundary(self):
        profile = load_profile_page("frontend/index.html")
        person = profile["mainEntity"]
        address = person["homeLocation"]["address"]
        self.assertEqual(address["addressLocality"], "Dortmund")
        self.assertEqual(address["addressCountry"], "DE")
        self.assertEqual(
            [language["alternateName"] for language in person["knowsLanguage"]],
            ["lv", "en", "de"],
        )
        serialized = json.dumps(profile, sort_keys=True)
        for forbidden in (
            "telephone",
            "streetAddress",
            "postalCode",
            "birthDate",
            "spouse",
            "children",
            "familyName",
        ):
            self.assertNotIn(f'"{forbidden}"', serialized)


if __name__ == "__main__":
    unittest.main()
''',
    encoding="utf-8",
)
