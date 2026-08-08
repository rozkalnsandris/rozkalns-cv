from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EMAIL_LIKE = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("privacy_build_content", ROOT / "scripts" / "build-content.py")
syncer = load_module("privacy_prompt_sync", ROOT / "scripts" / "sync-system-prompt.py")


class CurrentContactPrivacyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))

    def test_protected_channels_have_metadata_only(self) -> None:
        self.assertEqual(self.profile["schema_version"], 2)
        for channel in ("email", "phone"):
            self.assertEqual(
                self.profile["contact"][channel],
                {"visibility": "runtime-protected"},
            )
        for channel in ("github", "website"):
            entry = self.profile["contact"][channel]
            self.assertEqual(entry.get("visibility"), "public")
            self.assertIsInstance(entry.get("value"), str)
            self.assertTrue(entry["value"].strip())

    def test_schema_documents_protected_contact_shape(self) -> None:
        schema = json.loads((ROOT / "content/profile.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 2)
        contact = schema["properties"]["contact"]["properties"]
        self.assertEqual(contact["email"], {"$ref": "#/$defs/protectedValue"})
        self.assertEqual(contact["phone"], {"$ref": "#/$defs/protectedValue"})
        protected = schema["$defs"]["protectedValue"]
        self.assertEqual(protected.get("additionalProperties"), False)
        self.assertEqual(protected.get("required"), ["visibility"])
        self.assertEqual(
            protected["properties"]["visibility"],
            {"const": "runtime-protected"},
        )

    def test_generated_assistant_knowledge_excludes_protected_contact_values(self) -> None:
        profile = builder.validate_profile(self.profile)
        expected_prompt = builder.build_system_prompt(profile)
        self.assertNotIn("Email:", expected_prompt)
        self.assertNotIn("Phone:", expected_prompt)
        self.assertIn("verified contact section", expected_prompt.lower())
        prompt = (ROOT / "bot/system_prompt.txt").read_text(encoding="utf-8")
        self.assertEqual(prompt, expected_prompt)
        app = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        self.assertEqual(syncer.expected_app_text(app, prompt), app)

    def test_bootstrap_requires_external_git_author_email_when_unconfigured(self) -> None:
        source = (ROOT / "scripts/bootstrap-github.sh").read_text(encoding="utf-8")
        email_lines = [line.strip() for line in source.splitlines() if "user.email" in line]
        self.assertEqual(len(email_lines), 1)
        self.assertIn("GIT_AUTHOR_EMAIL", email_lines[0])
        self.assertIsNone(EMAIL_LIKE.search(email_lines[0]))


if __name__ == "__main__":
    unittest.main()
