from __future__ import annotations

from pathlib import Path
import sys
import unittest
import uuid

import requests

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

import chat_admission
import contact
import turnstile


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, json_error=None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class SiteverifyTransportTests(unittest.TestCase):
    def test_contact_and_chat_share_one_transport_helper(self) -> None:
        self.assertIs(contact.verify_siteverify, turnstile.verify_siteverify)
        self.assertIs(chat_admission.verify_siteverify, turnstile.verify_siteverify)

    def test_transient_transport_retry_reuses_uuid_and_token(self) -> None:
        for transient in (
            requests.Timeout("timeout"),
            requests.ConnectionError("connection"),
        ):
            with self.subTest(transient=type(transient).__name__):
                calls = []
                fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")

                def post(url, **kwargs):
                    calls.append((url, kwargs))
                    if len(calls) == 1:
                        raise transient
                    return FakeResponse({"success": True})

                payload = turnstile.verify_siteverify(
                    " token ",
                    "2001:0db8:0000:0000:0000:0000:0000:0001",
                    "secret",
                    post=post,
                    timeout=8.0,
                    uuid_factory=lambda: fixed_uuid,
                )

                self.assertEqual(payload, {"success": True})
                self.assertEqual(len(calls), 2)
                self.assertEqual(
                    calls[0][1]["data"]["idempotency_key"],
                    str(fixed_uuid),
                )
                self.assertEqual(calls[0][1]["data"], calls[1][1]["data"])
                self.assertEqual(calls[0][1]["data"]["response"], "token")
                self.assertEqual(calls[0][1]["data"]["remoteip"], "2001:db8::1")
                self.assertEqual(calls[0][1]["timeout"], (2.0, 2.0))
                self.assertEqual(calls[1][1]["timeout"], (2.0, 2.0))

    def test_5xx_retries_once_with_same_idempotency_key(self) -> None:
        calls = []
        fixed_uuid = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")

        def post(url, **kwargs):
            calls.append((url, kwargs))
            if len(calls) == 1:
                return FakeResponse({"success": False}, status_code=503)
            return FakeResponse({"success": True})

        self.assertEqual(
            turnstile.verify_siteverify(
                "token",
                "203.0.113.10",
                "secret",
                post=post,
                uuid_factory=lambda: fixed_uuid,
            ),
            {"success": True},
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            calls[0][1]["data"]["idempotency_key"],
            calls[1][1]["data"]["idempotency_key"],
        )

    def test_non_transient_4xx_does_not_retry(self) -> None:
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse({"success": False}, status_code=400)

        with self.assertRaises(turnstile.SiteverifyError):
            turnstile.verify_siteverify(
                "token",
                "203.0.113.10",
                "secret",
                post=post,
            )
        self.assertEqual(len(calls), 1)

    def test_cloudflare_failure_payload_is_returned_without_retry(self) -> None:
        calls = []
        failure = {
            "success": False,
            "error-codes": ["timeout-or-duplicate"],
        }

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse(failure)

        self.assertEqual(
            turnstile.verify_siteverify(
                "token",
                "203.0.113.10",
                "secret",
                post=post,
            ),
            failure,
        )
        self.assertEqual(len(calls), 1)

    def test_invalid_or_oversized_token_never_reaches_siteverify(self) -> None:
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse({"success": True})

        for value in (
            None,
            "",
            " ",
            "x" * (turnstile.MAX_TOKEN_CHARS + 1),
        ):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(turnstile.SiteverifyError):
                    turnstile.verify_siteverify(
                        value,
                        "203.0.113.10",
                        "secret",
                        post=post,
                    )
        self.assertEqual(calls, [])

    def test_invalid_json_is_not_retried(self) -> None:
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse(json_error=ValueError("bad json"))

        with self.assertRaises(turnstile.SiteverifyError):
            turnstile.verify_siteverify(
                "token",
                "203.0.113.10",
                "secret",
                post=post,
            )
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
