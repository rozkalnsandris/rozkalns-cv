from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProviderRuntimeContractTests(unittest.TestCase):
    def test_timeout_budget_is_ordered_and_source_example_match(self) -> None:
        config = (ROOT / "bot/config.py").read_text(encoding="utf-8")
        example = (ROOT / "bot/.env.example").read_text(encoding="utf-8")
        dockerfile = (ROOT / "bot/Dockerfile").read_text(encoding="utf-8")
        nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")

        connect = float(
            re.search(r'_number\(source, "LLM_CONNECT_TIMEOUT", ([0-9.]+),', config).group(1)
        )
        read = float(
            re.search(r'_number\(source, "LLM_READ_TIMEOUT", ([0-9.]+),', config).group(1)
        )
        worker = int(re.search(r'\"--timeout\", \"(\d+)\"', dockerfile).group(1))
        proxy = int(re.search(r"proxy_read_timeout\s+(\d+)s", nginx).group(1))

        self.assertIn(f"LLM_CONNECT_TIMEOUT={connect:g}", example)
        self.assertIn(f"LLM_READ_TIMEOUT={read:g}", example)
        self.assertNotIn("REQUEST_TIMEOUT=", example)
        self.assertNotIn("REQUEST_TIMEOUT", config)
        self.assertGreater(connect, 0)
        self.assertGreater(read, connect)
        self.assertGreater(worker, read)
        self.assertGreater(proxy, worker)

    def test_provider_uses_explicit_connect_and_idle_read_tuple(self) -> None:
        provider = (ROOT / "bot/provider.py").read_text(encoding="utf-8")
        self.assertIn("timeout=(self._connect_timeout, self._read_timeout)", provider)
        self.assertIn('"stream_options": {"include_usage": True}', provider)
        self.assertIn('"thinking": {"type": "disabled"}', provider)

    def test_runtime_image_contains_every_local_app_import(self) -> None:
        dockerfile = (ROOT / "bot/Dockerfile").read_text(encoding="utf-8")
        for module in (
            "app.py",
            "chat_admission.py",
            "chat_entry.py",
            "chat_policy.py",
            "config.py",
            "contact.py",
            "notifier.py",
            "provider.py",
            "provider_stream.py",
            "readiness.py",
            "storage.py",
            "system_prompt.py",
            "system_prompt.txt",
        ):
            with self.subTest(module=module):
                self.assertIn(module, dockerfile)

    def test_telemetry_contract_excludes_sensitive_fields(self) -> None:
        app = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        block = app.split("def _log_provider_result(", 1)[1].split("def create_app(", 1)[0]
        for forbidden in (
            "user_msg",
            "question",
            "answer",
            "client_address",
            "LLM_API_KEY",
            "TELEGRAM_TOKEN",
            "CONTACT_CONFIG",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, block)
        for required in (
            '"request_id"',
            '"duration_ms"',
            '"status"',
            '"finish_reason"',
            '"total_tokens"',
            '"quota_global_remaining"',
        ):
            self.assertIn(required, block)


if __name__ == "__main__":
    unittest.main()
