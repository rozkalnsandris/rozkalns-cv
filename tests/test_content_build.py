from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("build_content", ROOT / "scripts" / "build-content.py")
syncer = load_module(
    "sync_system_prompt", ROOT / "scripts" / "sync-system-prompt.py"
)


class CanonicalContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = builder.load_json(ROOT / "content" / "profile.json")

    def test_current_profile_and_translations_are_valid(self) -> None:
        profile = builder.validate_profile(self.profile)
        translations, raw = builder.load_translations()
        self.assertEqual(set(translations), {"en", "de", "lv"})
        self.assertEqual(set(raw), {"en", "de", "lv"})
        self.assertEqual(set(translations["en"]), set(translations["de"]))
        self.assertEqual(set(translations["en"]), set(translations["lv"]))
        self.assertEqual(profile["identity"]["name"], "Andris Rožkalns")

    def test_duplicate_ids_are_rejected(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["projects"][1]["id"] = profile["projects"][0]["id"]
        with self.assertRaises(builder.ContentError):
            builder.validate_profile(profile)

    def test_non_public_contact_is_rejected(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["contact"]["email"]["visibility"] = "private"
        with self.assertRaises(builder.ContentError):
            builder.validate_profile(profile)

    def test_source_digest_is_semantic_and_stable(self) -> None:
        profile = builder.validate_profile(copy.deepcopy(self.profile))
        translations, _ = builder.load_translations()
        reordered = {key: profile[key] for key in reversed(tuple(profile))}
        self.assertEqual(
            builder.source_digest(profile, translations),
            builder.source_digest(reordered, translations),
        )

    def test_generated_prompt_uses_canonical_facts(self) -> None:
        prompt = builder.build_system_prompt(
            builder.validate_profile(copy.deepcopy(self.profile))
        )
        self.assertIn("Andris Rožkalns", prompt)
        self.assertIn("2027-01", prompt)
        self.assertIn("Raspberry Pi 5", prompt)
        self.assertIn("Do not answer unrelated questions.", prompt)

    def test_prompt_sync_enforces_single_resource_owner(self) -> None:
        app_text = (
            "from system_prompt import load_system_prompt\n"
            "def create_app():\n"
            "    prompt = load_system_prompt()\n"
        )
        loader_text = (
            "from pathlib import Path\n"
            'DEFAULT_PROMPT_PATH = Path(__file__).with_name("system_prompt.txt")\n'
            'prompt = DEFAULT_PROMPT_PATH.read_text(encoding="utf-8")\n'
        )
        syncer.validate_prompt_boundary(app_text, "new prompt\n", loader_text)
        with self.assertRaises(syncer.PromptSyncError):
            syncer.validate_prompt_boundary(
                app_text + 'SYSTEM_PROMPT = """duplicate"""\n',
                "new prompt\n",
                loader_text,
            )


if __name__ == "__main__":
    unittest.main()
