from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from chat_admission import (  # noqa: E402
    ChatAdmissionConfig,
    issue_session,
    validate_session,
    verify_chat_turnstile,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class ChatAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ChatAdmissionConfig(
            site_key="site",
            secret_key="secret",
            hostnames=frozenset({"rozkalns.net"}),
        )

    def test_action_and_hostname_are_separate_from_contact_reveal(self) -> None:
        valid = lambda *_a, **_k: FakeResponse({
            "success": True,
            "action": "chat_admission",
            "hostname": "rozkalns.net",
        })
        contact = lambda *_a, **_k: FakeResponse({
            "success": True,
            "action": "contact_reveal",
            "hostname": "rozkalns.net",
        })
        self.assertTrue(verify_chat_turnstile("token", "203.0.113.5", self.config, post=valid))
        self.assertFalse(verify_chat_turnstile("token", "203.0.113.5", self.config, post=contact))

    def test_wrong_hostname_and_invalid_token_fail_closed(self) -> None:
        wrong = lambda *_a, **_k: FakeResponse({
            "success": True,
            "action": "chat_admission",
            "hostname": "attacker.example",
        })
        self.assertFalse(verify_chat_turnstile("token", "203.0.113.5", self.config, post=wrong))
        self.assertFalse(verify_chat_turnstile("", "203.0.113.5", self.config, post=wrong))

    def test_session_is_client_bound_and_time_bounded(self) -> None:
        secret = "A" * 43
        session = issue_session("client-a", secret, now=1000)
        self.assertTrue(validate_session(session, "client-a", secret, now=1001))
        self.assertFalse(validate_session(session, "client-b", secret, now=1001))
        self.assertFalse(validate_session(session, "client-a", secret, now=1901))

    def test_tampered_session_fails(self) -> None:
        secret = "A" * 43
        session = issue_session("client-a", secret, now=1000)
        expires, signature = session.split(".", 1)
        tampered = f"{expires}.{signature[:-1]}0"
        self.assertFalse(validate_session(tampered, "client-a", secret, now=1001))


if __name__ == "__main__":
    unittest.main()
