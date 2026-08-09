from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from system_prompt import load_system_prompt  # noqa: E402


class SystemPromptResourceTests(unittest.TestCase):
    def test_generated_prompt_loads_from_resource(self) -> None:
        prompt = load_system_prompt()
        self.assertIn("Andris Rožkalns", prompt)
        self.assertIn("Do not answer unrelated questions.", prompt)

    def test_empty_prompt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompt.txt"
            path.write_text("\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "generated system prompt is empty"):
                load_system_prompt(path)


if __name__ == "__main__":
    unittest.main()
