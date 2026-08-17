#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected one match in {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


provider_capacity = '''from __future__ import annotations

from threading import BoundedSemaphore, Lock


class ProviderStreamLease:
    """One idempotently releasable provider-stream capacity lease."""

    __slots__ = ("_semaphore", "_lock", "_released")

    def __init__(self, semaphore: BoundedSemaphore) -> None:
        self._semaphore = semaphore
        self._lock = Lock()
        self._released = False

    def release(self) -> bool:
        with self._lock:
            if self._released:
                return False
            self._semaphore.release()
            self._released = True
            return True


class ProviderStreamCapacity:
    """Non-blocking bounded admission for synchronous provider streams."""

    __slots__ = ("limit", "_semaphore")

    def __init__(self, limit: int) -> None:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("provider stream limit must be a positive integer")
        self.limit = limit
        self._semaphore = BoundedSemaphore(limit)

    def try_acquire(self) -> ProviderStreamLease | None:
        if not self._semaphore.acquire(blocking=False):
            return None
        return ProviderStreamLease(self._semaphore)
'''
(ROOT / "bot/provider_capacity.py").write_text(provider_capacity, encoding="utf-8")

replace_once(
    "bot/config.py",
    "    trusted_proxy_cidrs: tuple[ipaddress._BaseNetwork, ...]\n",
    "    trusted_proxy_cidrs: tuple[ipaddress._BaseNetwork, ...]\n"
    "    llm_max_concurrent_streams: int = 3\n",
)
replace_once(
    "bot/config.py",
    "            trusted_proxy_cidrs=_trusted_proxy_cidrs(source),\n",
    "            trusted_proxy_cidrs=_trusted_proxy_cidrs(source),\n"
    "            llm_max_concurrent_streams=_integer(\n"
    "                source,\n"
    "                \"LLM_MAX_CONCURRENT_STREAMS\",\n"
    "                3,\n"
    "                minimum=1,\n"
    "                maximum=32,\n"
    "            ),\n",
)
replace_once(
    "bot/.env.example",
    "LLM_READ_TIMEOUT=70\n",
    "LLM_READ_TIMEOUT=70\nLLM_MAX_CONCURRENT_STREAMS=3\n",
)
replace_once(
    "bot/Dockerfile",
    "    notifier.py provider.py provider_notices.json provider_stream.py readiness.py storage.py \\\n",
    "    notifier.py provider.py provider_capacity.py provider_notices.json provider_stream.py readiness.py storage.py \\\n",
)
replace_once(
    "scripts/build-input-id.py",
    '    "bot/provider.py",\n',
    '    "bot/provider.py",\n    "bot/provider_capacity.py",\n',
)
replace_once(
    "bot/app.py",
    "from provider import DeepSeekProvider\n",
    "from provider import DeepSeekProvider\nfrom provider_capacity import ProviderStreamCapacity\n",
)
replace_once(
    "bot/app.py",
    "    active_notifier = notifier or TelegramNotifier(\n",
    "    provider_capacity = ProviderStreamCapacity(active.llm_max_concurrent_streams)\n"
    "    active_notifier = notifier or TelegramNotifier(\n",
)
replace_once(
    "bot/app.py",
    '        "provider": active_provider,\n',
    '        "provider": active_provider,\n        "provider_capacity": provider_capacity,\n',
)
replace_once(
    "bot/app.py",
    "        messages = _build_messages(user_msg, history, prompt)\n"
    "        request_id = uuid.uuid4().hex[:16]\n\n"
    "        def generate():\n",
    "        messages = _build_messages(user_msg, history, prompt)\n"
    "        request_id = uuid.uuid4().hex[:16]\n"
    "        stream_lease = provider_capacity.try_acquire()\n"
    "        if stream_lease is None:\n"
    "            return (\n"
    "                jsonify(\n"
    "                    reply=(\n"
    "                        \"The assistant is busy right now. \"\n"
    "                        \"Please try again shortly.\"\n"
    "                    )\n"
    "                ),\n"
    "                503,\n"
    "                {\n"
    "                    \"Retry-After\": \"1\",\n"
    "                    **_rate_headers(decision, active.rate_per_ip_hour),\n"
    "                },\n"
    "            )\n\n"
    "        def generate():\n",
)
replace_once(
    "bot/app.py",
    "            finally:\n"
    "                answer_text = \"\".join(full_reply).strip()\n",
    "            finally:\n"
    "                stream_lease.release()\n"
    "                answer_text = \"\".join(full_reply).strip()\n",
)
replace_once(
    "bot/app.py",
    "        return Response(\n"
    "            stream_with_context(generate()),\n"
    "            mimetype=\"text/plain; charset=utf-8\",\n"
    "            headers={\n"
    "                \"X-Accel-Buffering\": \"no\",\n"
    "                \"Cache-Control\": \"no-store\",\n"
    "                \"X-Request-ID\": request_id,\n"
    "                **_rate_headers(decision, active.rate_per_ip_hour),\n"
    "            },\n"
    "        )\n",
    "        response = Response(\n"
    "            stream_with_context(generate()),\n"
    "            mimetype=\"text/plain; charset=utf-8\",\n"
    "            headers={\n"
    "                \"X-Accel-Buffering\": \"no\",\n"
    "                \"Cache-Control\": \"no-store\",\n"
    "                \"X-Request-ID\": request_id,\n"
    "                **_rate_headers(decision, active.rate_per_ip_hour),\n"
    "            },\n"
    "        )\n"
    "        response.call_on_close(stream_lease.release)\n"
    "        return response\n",
)
replace_once(
    "bot/app.py",
    '        "LLM_READ_TIMEOUT": settings.llm_read_timeout,\n',
    '        "LLM_READ_TIMEOUT": settings.llm_read_timeout,\n'
    '        "LLM_MAX_CONCURRENT_STREAMS": settings.llm_max_concurrent_streams,\n',
)

replace_once(
    "tests/test_settings.py",
    "        self.assertEqual(settings.rate_per_ip_hour, 8)\n",
    "        self.assertEqual(settings.rate_per_ip_hour, 8)\n"
    "        self.assertEqual(settings.llm_max_concurrent_streams, 3)\n",
)
replace_once(
    "tests/test_settings.py",
    "    def test_base_url_requires_clean_https_origin(self) -> None:\n",
    "    def test_provider_stream_limit_is_bounded(self) -> None:\n"
    "        self.assertEqual(\n"
    "            Settings.from_env({**BASE, \"LLM_MAX_CONCURRENT_STREAMS\": \"1\"}).llm_max_concurrent_streams,\n"
    "            1,\n"
    "        )\n"
    "        with self.assertRaisesRegex(SettingsError, \"LLM_MAX_CONCURRENT_STREAMS\"):\n"
    "            Settings.from_env({**BASE, \"LLM_MAX_CONCURRENT_STREAMS\": \"0\"})\n"
    "        with self.assertRaisesRegex(SettingsError, \"LLM_MAX_CONCURRENT_STREAMS\"):\n"
    "            Settings.from_env({**BASE, \"LLM_MAX_CONCURRENT_STREAMS\": \"33\"})\n\n"
    "    def test_base_url_requires_clean_https_origin(self) -> None:\n",
)

test_capacity = '''from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import requests

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from app import close_app_services, create_app  # noqa: E402
from chat_admission import issue_session  # noqa: E402
from config import Settings  # noqa: E402
from contact import ContactConfig  # noqa: E402
from provider_capacity import ProviderStreamCapacity  # noqa: E402


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
        flask_app = create_app(
            self._settings(limit),
            provider=active_provider,
            contact_config=self._contacts(),
            start_maintenance=False,
        )
        self.addCleanup(close_app_services, flask_app)
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
'''
(ROOT / "tests/test_provider_capacity.py").write_text(test_capacity, encoding="utf-8")

print("PHASE318_MATERIALIZE=PASS")
'''
