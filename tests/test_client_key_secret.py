from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"


class ClientKeySecretStartupTests(unittest.TestCase):
    def _import_app(
        self, *, client_secret: str | None, provider_key: str
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.update(
                {
                    "LLM_API_KEY": provider_key,
                    "ASSISTANT_DB_PATH": str(Path(tmp) / "assistant.sqlite3"),
                    "CHAT_RETENTION_DAYS": "0",
                    "TELEGRAM_TOKEN": "",
                    "CHAT_ID": "",
                }
            )
            if client_secret is None:
                env.pop("CLIENT_KEY_SECRET", None)
            else:
                env["CLIENT_KEY_SECRET"] = client_secret
            return subprocess.run(
                [sys.executable, "-c", "import app"],
                cwd=BOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_missing_secret_fails_startup_without_provider_fallback(self) -> None:
        result = self._import_app(
            client_secret=None, provider_key="provider-secret-marker"
        )
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("CLIENT_KEY_SECRET", combined)
        self.assertNotIn("provider-secret-marker", combined)

    def test_provider_key_reuse_fails_startup(self) -> None:
        shared = "B" * 43
        result = self._import_app(client_secret=shared, provider_key=shared)
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("dedicated", combined)
        self.assertNotIn(shared, combined)

    def test_valid_dedicated_secret_allows_startup(self) -> None:
        result = self._import_app(
            client_secret="A" * 43, provider_key="provider-key"
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
