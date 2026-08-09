from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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

    def test_remote_ip_is_normalized_before_siteverify(self) -> None:
        captured = {}

        def valid(*_args, **kwargs):
            captured.update(kwargs["data"])
            return FakeResponse({
                "success": True,
                "action": "chat_admission",
                "hostname": "rozkalns.net",
            })

        self.assertTrue(
            verify_chat_turnstile(
                "token",
                "2001:0db8:0000:0000:0000:0000:0000:0001",
                self.config,
                post=valid,
            )
        )
        self.assertEqual(captured["remoteip"], "2001:db8::1")

    def test_siteverify_replay_failure_is_fail_closed(self) -> None:
        responses = iter([
            {
                "success": True,
                "action": "chat_admission",
                "hostname": "rozkalns.net",
            },
            {
                "success": False,
                "error-codes": ["timeout-or-duplicate"],
            },
        ])

        def siteverify(*_args, **_kwargs):
            return FakeResponse(next(responses))

        self.assertTrue(
            verify_chat_turnstile("single-use-token", "203.0.113.5", self.config, post=siteverify)
        )
        self.assertFalse(
            verify_chat_turnstile("single-use-token", "203.0.113.5", self.config, post=siteverify)
        )

    def test_session_is_client_bound_and_time_bounded(self) -> None:
        secret = "A" * 43
        session = issue_session("client-a", secret, now=1000)
        self.assertTrue(validate_session(session, "client-a", secret, now=1001))
        self.assertFalse(validate_session(session, "client-b", secret, now=1001))
        self.assertFalse(validate_session(session, "client-a", secret, now=1901))

    def test_one_session_cannot_be_reused_across_many_rotating_clients_in_parallel(self) -> None:
        secret = "A" * 43
        owner = "client-for-203.0.113.1"
        session = issue_session(owner, secret, now=1000)
        client_keys = [owner] + [f"client-for-203.0.113.{index}" for index in range(2, 202)]

        with ThreadPoolExecutor(max_workers=32) as executor:
            results = list(
                executor.map(
                    lambda client_key: validate_session(
                        session,
                        client_key,
                        secret,
                        now=1001,
                    ),
                    client_keys,
                )
            )

        self.assertEqual(sum(results), 1)
        self.assertTrue(results[0])
        self.assertFalse(any(results[1:]))

    def test_tampered_session_fails(self) -> None:
        secret = "A" * 43
        session = issue_session("client-a", secret, now=1000)
        expires, signature = session.split(".", 1)
        replacement = "0" if signature[-1] != "0" else "1"
        tampered = f"{expires}.{signature[:-1]}{replacement}"
        self.assertFalse(validate_session(tampered, "client-a", secret, now=1001))


if __name__ == "__main__":
    unittest.main()
