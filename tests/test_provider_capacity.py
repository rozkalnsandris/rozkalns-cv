from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import requests

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from chat_admission import issue_session  # noqa: E402
from config import Settings  # noqa: E402
from contact import ContactConfig  # noqa: E402
from provider_capacity import ProviderStreamCapacity  # noqa: E402

APP_SPEC = importlib.util.spec_from_file_location("cv_app_capacity_test", BOT / "app.py")
if APP_SPEC is None or APP_SPEC.loader is None:
    raise RuntimeError("could not load app.py")
APP = importlib.util.module_from_spec(APP_SPEC)
APP_SPEC.loader.exec_module(APP)


SUCCESS_LINES = [
    'data: {"choices":[{"delta":{"content":"' + ("safe " * 80) + '"},"finish_reason":null}]}',
    'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
    'data: {"choices":[],"usage":{"prompt_tokens":2,"completion_tokens":2,"total_tokens":4}}',
    "data: [DONE]",
]


class FakeResponse:
    def __init__(self, *, lines=None, error=None, http_status=None) -> None:
        self.lines = SUCCESS_LINES if lines is None else lines
        self.error = error
        self.http_status = http_status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        if self.http_status is not None:
            response = requests.Response()
            response.status_code = self.http_status
            raise requests.exceptions.HTTPError(response=response)

    def iter_lines(self, decode_unicode: bool = False):
        if self.error is not None:
            raise self.error
        return iter(self.lines)


class FakeProvider:
    def __init__(self, response: FakeResponse | None = None) -> None:
        self.calls = 0
        self.response = response or FakeResponse()

    def open_stream(self, messages):
        self.calls += 1
        return self.response


class ProviderCapacityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _settings(self, limit: int = 3) -> Settings:
        return Settings.from_env(
            {
                "LLM_API_KEY": "provider-test-key",
                "CLIENT_KEY_SECRET": "A" * 43,
                "LLM_MODEL": "deepseek-v4-flash",
                "ASSISTANT_DB_PATH": str(Path(self.tmp.name) / "assistant.sqlite3"),
                "TRUSTED_PROXY_CIDRS": "172.19.0.10/32",
                "LLM_MAX_CONCURRENT_STREAMS": str(limit),
                "RATE_PER_IP_HOUR": "100",
                "DAILY_GLOBAL_CAP": "1000",
            }
        )

    @staticmethod
    def _contacts() -> ContactConfig:
        return ContactConfig(
            site_key="site",
            secret_key="secret",
            email="recruiting@example.invalid",
            phone_display="+49 000 0000000",
            phone_uri="+490000000000",
            hostnames=frozenset({"rozkalns.net"}),
        )

    def _app(self, provider: FakeProvider | None = None, *, limit: int = 3):
        active_provider = provider or FakeProvider()
        flask_app = APP.create_app(
            self._settings(limit),
            provider=active_provider,
            contact_config=self._contacts(),
            start_maintenance=False,
        )
        self.addCleanup(APP.close_app_services, flask_app)
        return flask_app, active_provider

    @staticmethod
    def _admission_header(flask_app, address: str = "203.0.113.50"):
        services = flask_app.extensions["cvbot"]
        settings = services["settings"]
        store = services["store"]
        client_key = store.pseudonymize(address, settings.client_key_secret)
        return {
            "X-Chat-Admission": issue_session(client_key, settings.client_key_secret)
        }

    @staticmethod
    def _assert_all_capacity_available(flask_app, limit: int = 3) -> None:
        capacity = flask_app.extensions["cvbot"]["provider_capacity"]
        leases = [capacity.try_acquire() for _ in range(limit)]
        if any(lease is None for lease in leases):
            raise AssertionError("provider capacity was not fully returned")
        if capacity.try_acquire() is not None:
            raise AssertionError("provider capacity exceeded configured maximum")
        for lease in leases:
            assert lease is not None
            lease.release()

    def _post_chat(self, flask_app, *, buffered: bool = True):
        return flask_app.test_client().post(
            "/chat",
            json={"message": "provider capacity test", "history": []},
            headers=self._admission_header(flask_app),
            environ_base={"REMOTE_ADDR": "203.0.113.50"},
            buffered=buffered,
        )

    def test_bounded_lease_is_nonblocking_and_release_is_idempotent(self) -> None:
        capacity = ProviderStreamCapacity(2)
        first = capacity.try_acquire()
        second = capacity.try_acquire()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsNone(capacity.try_acquire())
        assert first is not None
        self.assertTrue(first.release())
        self.assertFalse(first.release())
        replacement = capacity.try_acquire()
        self.assertIsNotNone(replacement)
        assert second is not None and replacement is not None
        second.release()
        replacement.release()

    def test_saturation_fails_fast_without_provider_and_health_stays_serviceable(self) -> None:
        flask_app, provider = self._app(limit=3)
        capacity = flask_app.extensions["cvbot"]["provider_capacity"]
        leases = [capacity.try_acquire() for _ in range(3)]
        self.assertTrue(all(lease is not None for lease in leases))

        client = flask_app.test_client()
        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.get("/health/ready").status_code, 200)
        response = self._post_chat(flask_app)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "1")
        self.assertIn("busy", response.get_json()["reply"].lower())
        self.assertEqual(provider.calls, 0)

        for lease in leases:
            assert lease is not None
            lease.release()
        self._assert_all_capacity_available(flask_app)

    def test_capacity_returns_after_success_timeout_http_and_protocol_failure(self) -> None:
        cases = (
            ("success", FakeResponse()),
            ("timeout", FakeResponse(error=requests.exceptions.Timeout())),
            ("http", FakeResponse(http_status=503)),
            ("protocol", FakeResponse(lines=["data: not-json"])),
        )
        for name, upstream in cases:
            with self.subTest(name=name):
                flask_app, provider = self._app(FakeProvider(upstream), limit=1)
                response = self._post_chat(flask_app)
                self.assertEqual(response.status_code, 200)
                response.get_data()
                self.assertEqual(provider.calls, 1)
                self._assert_all_capacity_available(flask_app, limit=1)

    def test_capacity_returns_on_generator_close_and_double_close(self) -> None:
        flask_app, provider = self._app(limit=1)
        response = self._post_chat(flask_app, buffered=False)
        iterator = iter(response.response)
        first_chunk = next(iterator)
        self.assertTrue(first_chunk)
        self.assertEqual(provider.calls, 1)
        response.close()
        response.close()
        self._assert_all_capacity_available(flask_app, limit=1)


if __name__ == "__main__":
    unittest.main()
