from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"


class LoggingConfigTests(unittest.TestCase):
    def test_entrypoint_emits_provider_info_once_without_sensitive_fields(self) -> None:
        script = r'''
import logging
import time

import chat_entry
from app import _log_provider_result
from provider_stream import ProviderStreamParser, ProviderUsage
from storage import RateDecision

chat_entry._configure_application_logging()
chat_entry._configure_application_logging()

logger = logging.getLogger(chat_entry.create_base_app.__module__)
parser = ProviderStreamParser()
parser.usage = ProviderUsage(
    prompt_tokens=11,
    completion_tokens=7,
    total_tokens=18,
)
decision = RateDecision(
    allowed=True,
    reason=None,
    retry_after=0,
    client_remaining=7,
    global_remaining=199,
)

print(f"LOGGER_LEVEL={logging.getLevelName(logger.level)}")
print(f"LOGGER_HANDLER_COUNT={len(logger.handlers)}")

_log_provider_result(
    logger=logger,
    request_id="synthetic-request-330",
    started_at=time.monotonic(),
    status="success",
    finish_reason="stop",
    parser=parser,
    decision=decision,
)
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=BOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("LOGGER_LEVEL=INFO", result.stdout)
        self.assertIn("LOGGER_HANDLER_COUNT=1", result.stdout)
        self.assertEqual(result.stderr.count('"event":"cvbot_provider_result"'), 1)
        self.assertIn('"request_id":"synthetic-request-330"', result.stderr)
        self.assertIn('"status":"success"', result.stderr)
        self.assertIn('"finish_reason":"stop"', result.stderr)
        self.assertIn('"prompt_tokens":11', result.stderr)
        self.assertIn('"completion_tokens":7', result.stderr)
        self.assertIn('"total_tokens":18', result.stderr)
        self.assertIn('"quota_client_remaining":7', result.stderr)
        self.assertIn('"quota_global_remaining":199', result.stderr)

        for forbidden in (
            '"message"',
            '"answer"',
            '"client_key"',
            '"remote_addr"',
            '"api_key"',
            '"token"',
            '"phone"',
        ):
            self.assertNotIn(forbidden, result.stderr)


if __name__ == "__main__":
    unittest.main()
