from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
JSON_LD_PATTERN = re.compile(
    r'<script type="application/ld\+json">([\s\S]*?)</script>'
)
PUBLIC_PAGES = (
    ROOT / "frontend" / "index.html",
    ROOT / "html" / "en" / "index.html",
    ROOT / "html" / "de" / "index.html",
    ROOT / "html" / "lv" / "index.html",
)


def load_profile() -> dict:
    return json.loads((ROOT / "content" / "profile.json").read_text(encoding="utf-8"))


def load_json_ld(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    matches = JSON_LD_PATTERN.findall(source)
    if len(matches) != 1:
        raise AssertionError(
            f"{path.relative_to(ROOT)} must contain exactly one JSON-LD block"
        )
    value = json.loads(matches[0])
    if not isinstance(value, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} JSON-LD must be an object")
    return value


def nested_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(nested_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(nested_keys(child))
    return keys


class MachineReadableProfileTests(unittest.TestCase):
    def test_json_ld_stable_identity_matches_canonical_profile(self) -> None:
        profile = load_profile()
        identity = profile["identity"]
        expected_github = profile["contact"]["github"]["value"]
        expected_languages = [row["name"] for row in profile["languages"]]
        expected_locality = identity["location"].split(",", 1)[0].strip()

        for path in PUBLIC_PAGES:
            with self.subTest(path=str(path.relative_to(ROOT))):
                document = load_json_ld(path)
                self.assertEqual(document.get("@type"), "ProfilePage")
                person = document.get("mainEntity")
                self.assertIsInstance(person, dict)
                self.assertEqual(person.get("@type"), "Person")
                self.assertEqual(person.get("name"), identity["name"])
                self.assertEqual(person.get("sameAs"), [expected_github])
                self.assertEqual(
                    [row.get("name") for row in person.get("knowsLanguage", [])],
                    expected_languages,
                )
                self.assertEqual(
                    person.get("homeLocation", {})
                    .get("address", {})
                    .get("addressLocality"),
                    expected_locality,
                )

    def test_json_ld_person_does_not_publish_contact_fields(self) -> None:
        profile = load_profile()
        self.assertEqual(
            profile["contact"]["phone"],
            {"visibility": "runtime-protected"},
        )

        for path in PUBLIC_PAGES:
            with self.subTest(path=str(path.relative_to(ROOT))):
                person = load_json_ld(path)["mainEntity"]
                keys = {key.lower() for key in nested_keys(person)}
                self.assertNotIn("telephone", keys)
                self.assertNotIn("email", keys)


if __name__ == "__main__":
    unittest.main()
