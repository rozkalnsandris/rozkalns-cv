#!/usr/bin/env python3
"""Public, sandboxed CV assistant application factory.

The service has no tools or access to other homelab services. Requests are
validated before quota is reserved, client addresses are pseudonymized, and
rate limits survive container restarts in SQLite.
"""

from __future__ import annotations

import atexit
import ipaddress
import json
from pathlib import Path
import time
from typing import Any
import uuid

import requests
from flask import Flask, Response, jsonify, request, stream_with_context

from chat_admission import (
    ChatAdmissionConfig,
    ChatAdmissionError,
    issue_session,
    validate_session,
    verify_chat_turnstile,
)
from chat_policy import ProtectedContactPolicy, ProtectedContactStreamGuard
from config import SUPPORTED_LLM_MODELS, Settings, VerificationRateConfig
from contact import (
    ContactVerificationError,
    load_contact_config,
    normalize_token,
    verify_turnstile,
)
from notifier import TelegramNotifier
from provider import DeepSeekProvider
from provider_capacity import ProviderStreamCapacity
from provider_stream import ProviderStreamError, ProviderStreamParser
from readiness import check_local_readiness
from storage import AssistantStore, RateDecision
from system_prompt import load_system_prompt


class RequestValidationError(ValueError):
    pass


def _valid_address(value: str | None) -> ipaddress._BaseAddress | None:
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _resolve_client_address(
    trusted_proxy_cidrs: tuple[ipaddress._BaseNetwork, ...] | None = None,
) -> str:
    """Accept nginx's normalized address only from explicitly trusted peers."""

    networks = (
        _legacy_settings().trusted_proxy_cidrs
        if trusted_proxy_cidrs is None
        else trusted_proxy_cidrs
    )
    peer = _valid_address(request.remote_addr)
    if peer is None:
        return "unknown"
    if any(peer in network for network in networks):
        forwarded = _valid_address(request.headers.get("X-Real-IP"))
        if forwarded is not None:
            return forwarded.compressed
    return peer.compressed


def _normalize_history(
    raw_history: Any,
    current_message: str,
    *,
    max_history_turns: int | None = None,
    max_input_chars: int | None = None,
) -> list[dict[str, str]]:
    settings = None
    if max_history_turns is None or max_input_chars is None:
        settings = _legacy_settings()
    history_limit = (
        settings.max_history_turns if max_history_turns is None else max_history_turns
    )
    input_limit = settings.max_input_chars if max_input_chars is None else max_input_chars

    if raw_history is None:
        return []
    if not isinstance(raw_history, list):
        raise RequestValidationError("History must be a list.")
    if len(raw_history) > (history_limit * 2) + 1:
        raise RequestValidationError("Conversation history is too long.")

    normalized: list[dict[str, str]] = []
    for turn in raw_history:
        if not isinstance(turn, dict):
            raise RequestValidationError("History entries must be objects.")
        role = turn.get("role")
        content = turn.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            raise RequestValidationError("History contains an invalid turn.")
        content = content.strip()
        if not content or len(content) > input_limit:
            raise RequestValidationError("History contains invalid content.")
        normalized.append({"role": role, "content": content})

    if (
        normalized
        and normalized[-1]["role"] == "user"
        and normalized[-1]["content"] == current_message
    ):
        normalized.pop()
    if normalized and normalized[-1]["role"] == "user":
        normalized.pop()
    if len(normalized) % 2:
        raise RequestValidationError("History must contain completed turns.")
    for index in range(0, len(normalized), 2):
        if (
            normalized[index]["role"] != "user"
            or normalized[index + 1]["role"] != "assistant"
        ):
            raise RequestValidationError("History must alternate roles.")
    return normalized[-(history_limit * 2) :]


def _parse_payload(data: Any, settings: Settings | None = None) -> tuple[str, list[dict[str, str]]]:
    active = _legacy_settings() if settings is None else settings
    if not isinstance(data, dict):
        raise RequestValidationError("Request body must be a JSON object.")
    message = data.get("message")
    if not isinstance(message, str):
        raise RequestValidationError("Message must be text.")
    message = message.strip()
    if not message:
        raise RequestValidationError(
            "Ask me anything about Andris's experience or skills."
        )
    if len(message) > active.max_input_chars:
        raise RequestValidationError(
            f"Please keep questions under {active.max_input_chars} characters."
        )
    return message, _normalize_history(
        data.get("history"),
        message,
        max_history_turns=active.max_history_turns,
        max_input_chars=active.max_input_chars,
    )


def _build_messages(
    message: str,
    history: list[dict[str, str]],
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    prompt = load_system_prompt() if system_prompt is None else system_prompt
    return [
        {"role": "system", "content": prompt},
        *history,
        {"role": "user", "content": message},
    ]


def _rate_headers(decision: RateDecision, rate_limit: int | None = None) -> dict[str, str]:
    limit = _legacy_settings().rate_per_ip_hour if rate_limit is None else rate_limit
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(decision.client_remaining),
        "X-RateLimit-Global-Remaining": str(decision.global_remaining),
    }
    if decision.retry_after:
        headers["Retry-After"] = str(decision.retry_after)
    return headers


_PROVIDER_NOTICE_KEYS = frozenset({
    "length",
    "content_filter",
    "insufficient_system_resource",
    "tool_calls",
    "protocol_error",
    "timeout",
    "http_error",
    "internal_error",
})
_PROVIDER_NOTICES_PATH = Path(__file__).with_name("provider_notices.json")
_PROVIDER_NOTICES = json.loads(_PROVIDER_NOTICES_PATH.read_text(encoding="utf-8"))
if (
    not isinstance(_PROVIDER_NOTICES, dict)
    or set(_PROVIDER_NOTICES) != _PROVIDER_NOTICE_KEYS
    or not all(
        isinstance(value, str) and value
        for value in _PROVIDER_NOTICES.values()
    )
):
    raise RuntimeError("provider notice contract is invalid")


def _provider_notice(status: str) -> str:
    return _PROVIDER_NOTICES.get(status, _PROVIDER_NOTICES["internal_error"])


def _log_provider_result(
    *,
    logger,
    request_id: str,
    started_at: float,
    status: str,
    finish_reason: str | None,
    parser: ProviderStreamParser,
    decision: RateDecision,
) -> None:
    usage = parser.usage
    logger.info(
        json.dumps(
            {
                "event": "cvbot_provider_result",
                "request_id": request_id,
                "duration_ms": max(0, int((time.monotonic() - started_at) * 1000)),
                "status": status,
                "finish_reason": finish_reason,
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
                "quota_client_remaining": decision.client_remaining,
                "quota_global_remaining": decision.global_remaining,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def create_app(
    settings: Settings | None = None,
    *,
    store: AssistantStore | None = None,
    provider: DeepSeekProvider | None = None,
    notifier: TelegramNotifier | None = None,
    contact_config=None,
    system_prompt: str | None = None,
    verification_rate: VerificationRateConfig | None = None,
    start_maintenance: bool = True,
) -> Flask:
    """Create one isolated cvbot application instance and its service graph."""

    active = Settings.from_env() if settings is None else settings
    active_verification_rate = (
        VerificationRateConfig.from_env()
        if verification_rate is None
        else verification_rate
    )
    contacts = load_contact_config() if contact_config is None else contact_config
    prompt = load_system_prompt() if system_prompt is None else system_prompt
    active_store = store or AssistantStore(
        active.db_path,
        per_client_hour=active.rate_per_ip_hour,
        daily_global_cap=active.daily_global_cap,
        chat_retention_days=active.chat_retention_days,
    )
    if start_maintenance:
        active_store.start_retention_maintenance()
    active_provider = provider or DeepSeekProvider(
        base_url=active.llm_base_url,
        api_key=active.llm_api_key,
        model=active.llm_model,
        max_response_tokens=active.max_response_tokens,
        connect_timeout=active.llm_connect_timeout,
        read_timeout=active.llm_read_timeout,
        http=requests,
    )
    provider_capacity = ProviderStreamCapacity(active.llm_max_concurrent_streams)
    active_notifier = notifier or TelegramNotifier(
        token=active.telegram_token,
        chat_id=active.telegram_chat_id,
        include_content=active.telegram_include_content,
    )
    output_policy = ProtectedContactPolicy(
        contacts.phone_display,
        contacts.phone_uri,
    )
    admission_config = ChatAdmissionConfig(
        site_key=contacts.site_key,
        secret_key=contacts.secret_key,
        hostnames=contacts.hostnames,
    )

    flask_app = Flask(__name__)
    flask_app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
    flask_app.config["TRUSTED_HOSTS"] = list(active.trusted_hosts)
    flask_app.extensions["cvbot"] = {
        "settings": active,
        "store": active_store,
        "provider": active_provider,
        "provider_capacity": provider_capacity,
        "notifier": active_notifier,
        "contact_config": contacts,
        "system_prompt": prompt,
        "verification_rate": active_verification_rate,
    }

    def client_identity() -> tuple[str, str]:
        address = _resolve_client_address(active.trusted_proxy_cidrs)
        return address, active_store.pseudonymize(address, active.client_key_secret)

    def verification_gate(
        client_key: str,
        *,
        response_key: str,
    ) -> tuple[Response, int] | None:
        try:
            decision = active_store.reserve_verification(
                client_key,
                per_client_hour=active_verification_rate.per_client_hour,
                global_hour=active_verification_rate.global_hour,
            )
        except Exception as error:
            flask_app.logger.error(
                "verification rate store failure: %s", type(error).__name__
            )
            return jsonify(
                **{response_key: "Verification is temporarily unavailable."}
            ), 503
        if decision.allowed:
            return None
        response = jsonify(
            **{
                response_key: (
                    "Too many verification attempts. Please try again later."
                )
            }
        )
        response.headers["Retry-After"] = str(decision.retry_after)
        return response, 429

    @flask_app.get("/health")
    @flask_app.get("/health/live")
    def health() -> Response:
        response = jsonify(ok=True)
        response.headers["Cache-Control"] = "no-store"
        return response

    @flask_app.get("/health/ready")
    def readiness() -> Response:
        result = check_local_readiness(
            active.db_path,
            llm_api_key=active.llm_api_key,
            client_key_secret=active.client_key_secret,
            llm_model=active.llm_model,
            supported_models=SUPPORTED_LLM_MODELS,
        )
        response = jsonify(ready=result.ready)
        response.headers["Cache-Control"] = "no-store"
        return response if result.ready else (response, 503)

    @flask_app.get("/contact-config")
    def contact_config_route() -> Response:
        response = jsonify(
            configured=contacts.configured,
            sitekey=contacts.site_key if contacts.configured else "",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @flask_app.post("/contact-reveal")
    def contact_reveal() -> Response:
        if not contacts.configured:
            return jsonify(error="Contact verification is not configured."), 503
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Request body must be a JSON object."), 400
        try:
            token = normalize_token(payload.get("token"))
        except ContactVerificationError:
            return jsonify(error="Turnstile token is invalid."), 400
        address, client_key = client_identity()
        limited = verification_gate(client_key, response_key="error")
        if limited is not None:
            return limited
        try:
            verified = verify_turnstile(
                token,
                address,
                contacts,
            )
        except ContactVerificationError as error:
            flask_app.logger.error(
                "turnstile verification failed: %s", type(error).__name__
            )
            return jsonify(error="Contact verification is temporarily unavailable."), 503
        if not verified:
            return jsonify(error="Verification failed. Please try again."), 403
        response = jsonify(
            email=contacts.email,
            phone=contacts.phone_display,
            phone_uri=contacts.phone_uri,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @flask_app.get("/chat-config")
    def chat_config() -> Response:
        response = jsonify(
            configured=admission_config.configured,
            sitekey=admission_config.site_key if admission_config.configured else "",
            action="chat_admission",
            retention_days=active.chat_retention_days,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @flask_app.post("/chat-admission")
    def chat_admission() -> Response:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(reply="Verification is required before chat."), 400
        if not admission_config.configured:
            return jsonify(
                reply=(
                    "Chat verification is temporarily unavailable. "
                    "Please email Andris instead."
                )
            ), 503
        try:
            token = normalize_token(payload.get("token"))
        except ContactVerificationError:
            return jsonify(reply="Chat verification failed. Please try again."), 403
        address, client_key = client_identity()
        limited = verification_gate(client_key, response_key="reply")
        if limited is not None:
            return limited
        try:
            valid = verify_chat_turnstile(token, address, admission_config)
        except ChatAdmissionError as error:
            flask_app.logger.error(
                "chat admission unavailable: %s", type(error).__name__
            )
            return jsonify(
                reply=(
                    "Chat verification is temporarily unavailable. "
                    "Please email Andris instead."
                )
            ), 503
        if not valid:
            return jsonify(reply="Chat verification failed. Please try again."), 403
        response = jsonify(
            session=issue_session(client_key, active.client_key_secret)
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @flask_app.post("/chat")
    def chat() -> Response:
        _address, client_key = client_identity()
        session = request.headers.get("X-Chat-Admission", "")
        if not validate_session(session, client_key, active.client_key_secret):
            return jsonify(reply="Chat verification is required or has expired."), 401
        if not active.llm_api_key:
            return jsonify(reply="The assistant isn't configured yet."), 503
        try:
            user_msg, history = _parse_payload(request.get_json(silent=True), active)
        except RequestValidationError:
            return jsonify(
                reply=(
                    "Invalid chat request: message or conversation history is "
                    "invalid or too long."
                )
            ), 400
        try:
            decision = active_store.reserve(client_key)
        except Exception as error:
            flask_app.logger.error("rate store failure: %s", type(error).__name__)
            return jsonify(reply="The assistant is temporarily unavailable."), 503
        if not decision.allowed:
            if decision.reason == "global":
                reply = (
                    "The assistant has reached today's usage limit. "
                    "Please email Andris instead."
                )
            else:
                reply = (
                    "You've sent several messages — please wait a bit, "
                    "or email Andris directly."
                )
            return jsonify(reply=reply), 429, _rate_headers(
                decision, active.rate_per_ip_hour
            )

        messages = _build_messages(user_msg, history, prompt)
        request_id = uuid.uuid4().hex[:16]
        stream_lease = provider_capacity.try_acquire()
        if stream_lease is None:
            return (
                jsonify(
                    reply=(
                        "The assistant is busy right now. "
                        "Please try again shortly."
                    )
                ),
                503,
                {
                    "Retry-After": "1",
                    **_rate_headers(decision, active.rate_per_ip_hour),
                },
            )

        def generate():
            full_reply: list[str] = []
            guard = ProtectedContactStreamGuard(output_policy)
            parser = ProviderStreamParser()
            started_at = time.monotonic()
            status = "protocol_error"
            finish_reason: str | None = None
            persist_answer = False
            try:
                with active_provider.open_stream(messages) as upstream:
                    upstream.raise_for_status()
                    for line in upstream.iter_lines(decode_unicode=True):
                        for event in parser.feed_line(line):
                            if event.kind == "content":
                                for safe_chunk in guard.feed(event.content):
                                    full_reply.append(safe_chunk)
                                    yield safe_chunk
                                if guard.blocked:
                                    status = "policy_blocked"
                                    persist_answer = True
                                    break
                            elif event.kind == "terminal":
                                finish_reason = event.finish_reason
                        if guard.blocked:
                            break

                    if guard.blocked:
                        status = "policy_blocked"
                    else:
                        parser.finish_eof()
                        finish_reason = parser.finish_reason
                        if finish_reason == "stop":
                            for safe_chunk in guard.finish():
                                full_reply.append(safe_chunk)
                                yield safe_chunk
                            status = "success"
                            persist_answer = True
                        elif finish_reason == "length":
                            for safe_chunk in guard.finish():
                                full_reply.append(safe_chunk)
                                yield safe_chunk
                            status = "length"
                            yield _provider_notice(status)
                        elif finish_reason in {
                            "content_filter",
                            "insufficient_system_resource",
                            "tool_calls",
                        }:
                            status = finish_reason
                            yield _provider_notice(status)
                        else:
                            raise ProviderStreamError(
                                "missing classified finish reason"
                            )
            except GeneratorExit:
                status = "browser_disconnect"
                raise
            except requests.exceptions.Timeout:
                status = "timeout"
                yield _provider_notice(status)
            except requests.exceptions.HTTPError as error:
                status_code = getattr(error.response, "status_code", None)
                status = (
                    f"http_{status_code // 100}xx"
                    if isinstance(status_code, int) and 400 <= status_code < 600
                    else "http_error"
                )
                yield _provider_notice("http_error")
            except ProviderStreamError:
                status = "protocol_error"
                yield _provider_notice(status)
            except Exception as error:
                status = "internal_error"
                flask_app.logger.error("LLM stream failed: %s", type(error).__name__)
                yield _provider_notice(status)
            finally:
                stream_lease.release()
                answer_text = "".join(full_reply).strip()
                if persist_answer and answer_text:
                    try:
                        active_store.record_chat(client_key, user_msg, answer_text)
                    except Exception as error:
                        flask_app.logger.error(
                            "chat retention write failed: %s", type(error).__name__
                        )
                    active_notifier.submit(client_key, user_msg, answer_text)
                _log_provider_result(
                    logger=flask_app.logger,
                    request_id=request_id,
                    started_at=started_at,
                    status=status,
                    finish_reason=finish_reason,
                    parser=parser,
                    decision=decision,
                )

        response = Response(
            stream_with_context(generate()),
            mimetype="text/plain; charset=utf-8",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-store",
                "X-Request-ID": request_id,
                **_rate_headers(decision, active.rate_per_ip_hour),
            },
        )
        response.call_on_close(stream_lease.release)
        return response

    return flask_app


def close_app_services(flask_app: Flask) -> None:
    services = flask_app.extensions.get("cvbot") or {}
    notifier = services.get("notifier")
    store = services.get("store")
    if notifier is not None:
        notifier.close()
    if store is not None:
        store.close()


_legacy_settings_cache: Settings | None = None
_legacy_app_cache: Flask | None = None


def _legacy_settings() -> Settings:
    global _legacy_settings_cache
    if _legacy_settings_cache is None:
        _legacy_settings_cache = Settings.from_env()
    return _legacy_settings_cache


def _legacy_app() -> Flask:
    global _legacy_app_cache
    if _legacy_app_cache is None:
        _legacy_app_cache = create_app(_legacy_settings())
    return _legacy_app_cache


def __getattr__(name: str):
    if name == "app":
        return _legacy_app()
    if name == "STORE":
        return _legacy_app().extensions["cvbot"]["store"]
    if name == "CONTACT_CONFIG":
        return _legacy_app().extensions["cvbot"]["contact_config"]
    if name == "SYSTEM_PROMPT":
        return _legacy_app().extensions["cvbot"]["system_prompt"]
    settings = _legacy_settings()
    mapping = {
        "LLM_BASE_URL": settings.llm_base_url,
        "LLM_API_KEY": settings.llm_api_key,
        "LLM_MODEL": settings.llm_model,
        "LLM_THINKING": {"type": "disabled"},
        "MAX_INPUT_CHARS": settings.max_input_chars,
        "MAX_RESPONSE_TOKENS": settings.max_response_tokens,
        "MAX_HISTORY_TURNS": settings.max_history_turns,
        "RATE_PER_IP_HOUR": settings.rate_per_ip_hour,
        "DAILY_GLOBAL_CAP": settings.daily_global_cap,
        "LLM_CONNECT_TIMEOUT": settings.llm_connect_timeout,
        "LLM_READ_TIMEOUT": settings.llm_read_timeout,
        "LLM_MAX_CONCURRENT_STREAMS": settings.llm_max_concurrent_streams,
        "CHAT_RETENTION_DAYS": settings.chat_retention_days,
        "DB_PATH": settings.db_path,
        "CLIENT_KEY_SECRET": settings.client_key_secret,
        "TELEGRAM_TOKEN": settings.telegram_token,
        "TELEGRAM_CHAT_ID": settings.telegram_chat_id,
        "TELEGRAM_INCLUDE_CONTENT": settings.telegram_include_content,
        "TRUSTED_PROXY_CIDRS": settings.trusted_proxy_cidrs,
        "TRUSTED_HOSTS": settings.trusted_hosts,
    }
    if name in mapping:
        return mapping[name]
    raise AttributeError(name)


if __name__ == "__main__":
    development_app = create_app()
    atexit.register(close_app_services, development_app)
    development_app.run(host="0.0.0.0", port=5000, threaded=True)
