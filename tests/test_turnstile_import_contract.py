from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

import chat_admission
import contact
import turnstile


class SharedTurnstileImportContractTests(unittest.TestCase):
    def test_contact_and_chat_use_the_same_siteverify_helper(self) -> None:
        self.assertIs(contact.verify_siteverify, turnstile.verify_siteverify)
        self.assertIs(chat_admission.verify_siteverify, turnstile.verify_siteverify)

    def test_runtime_dockerfile_includes_shared_helper(self) -> None:
        dockerfile = (BOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("turnstile.py", dockerfile)


if __name__ == "__main__":
    unittest.main()
