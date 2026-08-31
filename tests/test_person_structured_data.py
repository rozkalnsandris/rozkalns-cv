import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RE = re.compile(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL)


def load_profile_page(relative):
    html = (ROOT / relative).read_text(encoding="utf-8")
    matches = SCRIPT_RE.findall(html)
    if len(matches) != 1:
        raise AssertionError(f"{relative}: expected exactly one JSON-LD script, got {len(matches)}")
    return json.loads(matches[0])


class ProfilePageStructuredDataContractTest(unittest.TestCase):
    def assert_privacy_boundary(self, profile):
        serialized = json.dumps(profile, sort_keys=True)
        for forbidden in ("telephone", "streetAddress", "postalCode", "birthDate", "spouse", "children", "familyName"):
            self.assertNotIn(f'"{forbidden}"', serialized)

    def test_root_alias_uses_english_canonical_profile_identity(self):
        for relative in ("frontend/index.html", "html/index.html"):
            profile = load_profile_page(relative)
            self.assertEqual(profile["@context"], "https://schema.org")
            self.assertEqual(profile["@type"], "ProfilePage")
            self.assertEqual(profile["@id"], "https://rozkalns.net/en/#profile")
            self.assertEqual(profile["url"], "https://rozkalns.net/en/")
            person = profile["mainEntity"]
            self.assertEqual(person["@id"], "https://rozkalns.net/#person")
            self.assertEqual(person["url"], "https://rozkalns.net/en/")
            self.assertEqual(person["name"], "Andris Rožkalns")
            self.assertEqual(person["image"], "https://rozkalns.net/photo.jpg")
            self.assertEqual(person["sameAs"], ["https://github.com/rozkalnsandris"])
            self.assert_privacy_boundary(profile)

    def test_localized_profile_pages_match_visible_locale(self):
        expected_roles = {
            "en": "Junior DevOps & Linux Engineer",
            "de": "Junior DevOps Engineer / Linux-Systemadministrator",
            "lv": "Junior DevOps un Linux inženieris",
        }
        for language, role in expected_roles.items():
            profile = load_profile_page(f"html/{language}/index.html")
            self.assertEqual(profile["@id"], f"https://rozkalns.net/{language}/#profile")
            self.assertEqual(profile["url"], f"https://rozkalns.net/{language}/")
            person = profile["mainEntity"]
            self.assertEqual(person["@id"], "https://rozkalns.net/#person")
            self.assertEqual(person["url"], "https://rozkalns.net/en/")
            self.assertEqual(person["jobTitle"], role)
            self.assertIn("Dortmund", person["description"])
            address = person["homeLocation"]["address"]
            self.assertEqual(address["addressLocality"], "Dortmund")
            self.assertEqual(address["addressCountry"], "DE")
            self.assertEqual([item["alternateName"] for item in person["knowsLanguage"]], ["lv", "en", "de"])
            self.assert_privacy_boundary(profile)


if __name__ == "__main__":
    unittest.main()
