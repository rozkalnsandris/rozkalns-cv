from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from config import Settings, SettingsError


BASE = {
    "LLM_API_KEY": "provider-test-key",
    "CLIENT_KEY_SECRET": "A" * 43,
    "LLM_MODEL": "deepseek-v4-flash",
    "ASSISTANT_DB_PATH": "/tmp/cvbot-test.sqlite3",
    "TRUSTED_PROXY_CIDRS": "172.19.0.10/32",
}


class SettingsTests(unittest.TestCase):
    def test_valid_settings_are_parsed_once(self) -> None:
        settings = Settings.from_env(BASE)
        self.assertEqual(settings.llm_model, "deepseek-v4-flash")
        self.assertEqual(settings.rate_per_ip_hour, 8)
        self.assertEqual(settings.llm_max_concurrent_streams, 3)
        self.assertEqual(settings.trusted_proxy_cidrs[0].compressed, "172.19.0.10/32")

    def test_invalid_integer_is_sanitized(self) -> None:
        env = {**BASE, "RATE_PER_IP_HOUR": "not-a-number"}
        with self.assertRaisesRegex(SettingsError, "RATE_PER_IP_HOUR") as caught:
            Settings.from_env(env)
        self.assertNotIn("provider-test-key", str(caught.exception))
        self.assertNotIn("A" * 43, str(caught.exception))

    def test_out_of_range_value_fails_closed(self) -> None:
        with self.assertRaisesRegex(SettingsError, "MAX_HISTORY_TURNS"):
            Settings.from_env({**BASE, "MAX_HISTORY_TURNS": "999"})

    def test_provider_stream_limit_is_bounded(self) -> None:
        self.assertEqual(
            Settings.from_env({**BASE, "LLM_MAX_CONCURRENT_STREAMS": "1"}).llm_max_concurrent_streams,
            1,
        )
        with self.assertRaisesRegex(SettingsError, "LLM_MAX_CONCURRENT_STREAMS"):
            Settings.from_env({**BASE, "LLM_MAX_CONCURRENT_STREAMS": "0"})
        with self.assertRaisesRegex(SettingsError, "LLM_MAX_CONCURRENT_STREAMS"):
            Settings.from_env({**BASE, "LLM_MAX_CONCURRENT_STREAMS": "33"})

    def test_base_url_requires_clean_https_origin(self) -> None:
        for value in (
            "http://api.deepseek.com",
            "https://user:pass@api.deepseek.com",
            "https://api.deepseek.com/v1",
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(SettingsError, "LLM_BASE_URL"):
                    Settings.from_env({**BASE, "LLM_BASE_URL": value})

    def test_proxy_cidrs_are_validated(self) -> None:
        with self.assertRaisesRegex(SettingsError, "TRUSTED_PROXY_CIDRS"):
            Settings.from_env({**BASE, "TRUSTED_PROXY_CIDRS": "not-a-cidr"})

    def test_unsupported_model_fails_closed(self) -> None:
        with self.assertRaisesRegex(SettingsError, "LLM_MODEL"):
            Settings.from_env({**BASE, "LLM_MODEL": "deepseek-chat"})


if __name__ == "__main__":
    unittest.main()
