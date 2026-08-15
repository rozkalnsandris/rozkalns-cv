import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = (
    "Andris Rožkalns — self-taught DevOps and Linux engineer in Dortmund, "
    "building and operating a production Raspberry Pi 5 homelab."
)
SCRIPT_RE = re.compile(
    r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL
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
