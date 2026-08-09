#!/usr/bin/env python3
"""Public, sandboxed CV assistant.

The service has no tools or access to other homelab services. Requests are
validated before quota is reserved, client addresses are pseudonymized, and
rate limits survive container restarts in SQLite.
"""

from __future__ import annotations

import atexit
import ipaddress
import json
import os
import threading
import time
from typing import Any
import uuid

import requests
from flask import Flask, Response, jsonify, request, stream_with_context

from chat_policy import ProtectedContactPolicy, ProtectedContactStreamGuard
from contact import (
    ContactVerificationError,
    load_contact_config,
    normalize_token,
    verify_turnstile,
)
from provider_stream import ProviderStreamError, ProviderStreamParser
from readiness import check_local_readiness
from storage import (
    AssistantStore,
    RateDecision,
    validate_client_key_secret,
)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024


# ---------------- CONFIG ----------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
SUPPORTED_LLM_MODELS = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash").strip()
if LLM_MODEL not in SUPPORTED_LLM_MODELS:
    raise RuntimeError("LLM_MODEL must be a supported DeepSeek V4 model")
LLM_THINKING = {"type": "disabled"}
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "500"))
MAX_RESPONSE_TOKENS = int(os.getenv("MAX_RESPONSE_TOKENS", "350"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))
RATE_PER_IP_HOUR = int(os.getenv("RATE_PER_IP_HOUR", "8"))
DAILY_GLOBAL_CAP = int(os.getenv("DAILY_GLOBAL_CAP", "200"))
LLM_CONNECT_TIMEOUT = float(os.getenv("LLM_CONNECT_TIMEOUT", "5"))
LLM_READ_TIMEOUT = float(os.getenv("LLM_READ_TIMEOUT", "70"))
CHAT_RETENTION_DAYS = int(os.getenv("CHAT_RETENTION_DAYS", "0"))
DB_PATH = os.getenv("ASSISTANT_DB_PATH", "/app/data/assistant.sqlite3")
CLIENT_KEY_SECRET = validate_client_key_secret(
    os.getenv("CLIENT_KEY_SECRET", ""), LLM_API_KEY
)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID", "")
TELEGRAM_INCLUDE_CONTENT = os.getenv(
    "TELEGRAM_INCLUDE_CONTENT", "false"
).lower() in {"1", "true", "yes"}
TRUSTED_PROXY_CIDRS = tuple(
    ipaddress.ip_network(value.strip(), strict=False)
    for value in os.getenv("TRUSTED_PROXY_CIDRS", "172.19.0.10/32").split(",")
    if value.strip()
)
CONTACT_CONFIG = load_contact_config()
CHAT_OUTPUT_POLICY = ProtectedContactPolicy(
    CONTACT_CONFIG.phone_display,
    CONTACT_CONFIG.phone_uri,
)

STORE = AssistantStore(
    DB_PATH,
    per_client_hour=RATE_PER_IP_HOUR,
    daily_global_cap=DAILY_GLOBAL_CAP,
    chat_retention_days=CHAT_RETENTION_DAYS,
)
STORE.start_retention_maintenance()
atexit.register(STORE.close)


# ---------------- GENERATED KNOWLEDGE (do not edit) ----------------
# BEGIN GENERATED SYSTEM PROMPT
SYSTEM_PROMPT = """You are the CV assistant for Andris Rožkalns.
Answer only questions about this public CV, professional skills, projects, experience, education, and availability.

PUBLIC PROFILE
Name: Andris Rožkalns
Role: Junior DevOps & Linux Engineer
Location: Dortmund, Germany
Availability: 2027-01
Career goal: Junior DevOps or Linux Systems Administrator, progressing toward MLOps

PUBLIC CONTACT
Email: andris@rozkalns.net
Phone and WhatsApp: available only through the verified contact section on the public CV.
GitHub: https://github.com/rozkalnsandris
Website: https://rozkalns.net/

LANGUAGES
- Latvian: native
- English: fluent working language
- German: B1

WORK EXPERIENCE
- Warehouse Employee — Sonepar Deutschland GmbH, Region West · Dortmund, Germany (2023-07 – 2026-12 planned)
  - Processed high-volume electrical wholesale orders using scanner systems
  - Prepared cable, operated forklifts, and worked rotating logistics shifts
  - Built process discipline and reliability transferable to IT operations
- Painting Area Manager / Main Paint Sprayer — SIA Koksne · Latvia (2020-05 – 2023-06)
  - Managed daily production, warehouse workflow, and staff tasks
  - Performed precision airless coating of wooden windows and doors
- Warehouse / Shop Manager — SIA Apavu Bode · Latvia (2011-08 – 2020-04)
  - Managed receiving, stock organisation, staff coordination, and daily operations
- Early IT — self-taught — Secondary school · Riga, Latvia (2008 – 2011)
  - Administered Linux Counter-Strike 1.6 servers through SSH and FTP
  - Maintained IPB forum templates and plugins and built HTML websites

EDUCATION
- The Linux Command Line — ongoing self-study; Applied daily in the homelab
- Multimedia Communication — Rīga Stradiņš University; 2011 – 2013; partial studies, not completed
- Secondary Education — Riga 45th Secondary School; 2004 – 2011

TECHNICAL SKILLS
- Core: Linux administration, Docker, Docker Compose, Bash, Nginx, DNS, SSL/TLS, Prometheus, Grafana, systemd, Git
- Working knowledge: Python, REST APIs, Home Assistant, ESP32/IoT, YAML
- Learning: Ansible, Terraform, AWS Cloud
- Foundations: SSH/FTP, PHP/IPB forums, HTML

PROJECTS
- Production Linux server stack: Raspberry Pi 5 with NVMe storage; Docker Compose services running 24/7; Nginx, AdGuard Home, TLS, and Cloudflare Tunnel
- Hermes self-hosted AI agent: Primary and fallback LLM routing; ChromaDB vector search and persistent memory; Telegram and Home Assistant integration
- Monitoring and observability: Prometheus; Grafana; Node Exporter; live CV metrics
- Home automation: Matter devices; Home Assistant dashboards; energy-cost tracking
- Automated maintenance: controlled APT and container updates; Telegram evidence; availability checks
- Balcony irrigation: ESP32; 15 moisture sensors; relay pump; multiplexer; safety limits

INFRASTRUCTURE
- Host: Raspberry Pi 5
- Storage: NVMe SSD
- Runtime: Docker Compose
- Availability: 24/7
- Public Site: https://rozkalns.net/

RULES
- Do not answer unrelated questions.
- The dedicated recruiting email is public and may be provided directly.
- Do not reveal, infer, or guess the protected phone number; direct phone or WhatsApp requests to the verified contact section on the public CV.
- For salary expectations, say Andris is open to discussion based on the role and company.
- For the start date, say Andris is available from 2027-01.
- Keep answers concise, factual, and professional."""
# END GENERATED SYSTEM PROMPT


class RequestValidationError(ValueError):
    pass


def _valid_address(value: str | None) -> ipaddress._BaseAddress | None:
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _resolve_client_address() -> str:
    """Accept nginx's normalized address only from the fixed nginx container."""

    peer = _valid_address(request.remote_addr)
    if peer is None:
        return "unknown"
    if any(peer in network for network in TRUSTED_PROXY_CIDRS):
        forwarded = _valid_address(request.headers.get("X-Real-IP"))
        if forwarded is not None:
            return forwarded.compressed
    return peer.compressed


def _normalize_history(raw_history: Any, current_message: str) -> list[dict[str, str]]:
    if raw_history is None:
        return []
    if not isinstance(raw_history, list):
        raise RequestValidationError("History must be a list.")
    if len(raw_history) > (MAX_HISTORY_TURNS * 2) + 1:
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
        if not content or len(content) > MAX_INPUT_CHARS:
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
    return normalized[-(MAX_HISTORY_TURNS * 2) :]


def _parse_payload(data: Any) -> tuple[str, list[dict[str, str]]]:
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
    if len(message) > MAX_INPUT_CHARS:
        raise RequestValidationError(
            f"Please keep questions under {MAX_INPUT_CHARS} characters."
        )
    return message, _normalize_history(data.get("history"), message)


def _build_messages(
    message: str, history: list[dict[str, str]]
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": message},
    ]


def _rate_headers(decision: RateDecision) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(RATE_PER_IP_HOUR),
        "X-RateLimit-Remaining": str(decision.client_remaining),
        "X-RateLimit-Global-Remaining": str(decision.global_remaining),
    }
    if decision.retry_after:
        headers["Retry-After"] = str(decision.retry_after)
    return headers


def _notify_telegram(client_key: str, question: str, answer: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        text = f"CV assistant interaction\nClient: {client_key}"
        if TELEGRAM_INCLUDE_CONTENT:
            text += f"\n\nQuestion: {question[:300]}\n\nAnswer: {answer[:600]}"
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
        response.raise_for_status()
    except Exception as error:
        app.logger.error("telegram notification failed: %s", type(error).__name__)


def _provider_notice(status: str) -> str:
    return {
        "length": "\n\n[The response was truncated. Please ask a narrower question.]",
        "content_filter": "\n\n[The provider stopped this response for safety. Please rephrase.]",
        "insufficient_system_resource": (
            "\n\n[The provider is temporarily short on capacity. Please try again.]"
        ),
        "tool_calls": "\n\n[The provider returned an unsupported response. Please try again.]",
        "protocol_error": "\n\n[The provider returned an invalid stream. Please try again.]",
        "timeout": "\n\n[That took too long — please try again.]",
        "http_error": "\n\n[The provider is temporarily unavailable. Please try again.]",
    }.get(status, "\n\n[Sorry, something went wrong. Please try again.]")


def _log_provider_result(
    *,
    request_id: str,
    started_at: float,
    status: str,
    finish_reason: str | None,
    parser: ProviderStreamParser,
    decision: RateDecision,
) -> None:
    usage = parser.usage
    app.logger.info(
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


@app.get("/health")
@app.get("/health/live")
def health() -> Response:
    response = jsonify(ok=True)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health/ready")
def readiness() -> Response:
    result = check_local_readiness(
        DB_PATH,
        llm_api_key=LLM_API_KEY,
        client_key_secret=CLIENT_KEY_SECRET,
        llm_model=LLM_MODEL,
        supported_models=SUPPORTED_LLM_MODELS,
    )
    response = jsonify(ready=result.ready)
    response.headers["Cache-Control"] = "no-store"
    return response if result.ready else (response, 503)


@app.get("/contact-config")
def contact_config() -> Response:
    response = jsonify(
        configured=CONTACT_CONFIG.configured,
        sitekey=CONTACT_CONFIG.site_key if CONTACT_CONFIG.configured else "",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/contact-reveal")
def contact_reveal() -> Response:
    if not CONTACT_CONFIG.configured:
        return jsonify(error="Contact verification is not configured."), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be a JSON object."), 400
    try:
        token = normalize_token(payload.get("token"))
    except ContactVerificationError as error:
        return jsonify(error=str(error)), 400

    try:
        verified = verify_turnstile(
            token,
            _resolve_client_address(),
            CONTACT_CONFIG,
        )
    except ContactVerificationError as error:
        app.logger.error("turnstile verification failed: %s", type(error).__name__)
        return jsonify(error="Contact verification is temporarily unavailable."), 503

    if not verified:
        return jsonify(error="Verification failed. Please try again."), 403

    response = jsonify(
        email=CONTACT_CONFIG.email,
        phone=CONTACT_CONFIG.phone_display,
        phone_uri=CONTACT_CONFIG.phone_uri,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/chat")
def chat() -> Response:
    if not LLM_API_KEY or not CLIENT_KEY_SECRET:
        return jsonify(reply="The assistant isn't configured yet."), 503

    try:
        user_msg, history = _parse_payload(request.get_json(silent=True))
    except RequestValidationError as error:
        return jsonify(reply=str(error)), 400

    client_address = _resolve_client_address()
    client_key = STORE.pseudonymize(client_address, CLIENT_KEY_SECRET)
    try:
        decision = STORE.reserve(client_key)
    except Exception as error:
        app.logger.error("rate store failure: %s", type(error).__name__)
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
        return jsonify(reply=reply), 429, _rate_headers(decision)

    messages = _build_messages(user_msg, history)
    request_id = uuid.uuid4().hex[:16]

    def generate():
        full_reply: list[str] = []
        guard = ProtectedContactStreamGuard(CHAT_OUTPUT_POLICY)
        parser = ProviderStreamParser()
        started_at = time.monotonic()
        status = "protocol_error"
        finish_reason: str | None = None
        persist_answer = False
        try:
            with requests.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "max_tokens": MAX_RESPONSE_TOKENS,
                    "temperature": 0.4,
                    "thinking": LLM_THINKING,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                },
                timeout=(LLM_CONNECT_TIMEOUT, LLM_READ_TIMEOUT),
                stream=True,
            ) as upstream:
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
                        raise ProviderStreamError("missing classified finish reason")
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
            app.logger.error("LLM stream failed: %s", type(error).__name__)
            yield _provider_notice(status)
        finally:
            answer_text = "".join(full_reply).strip()
            if persist_answer and answer_text:
                try:
                    STORE.record_chat(client_key, user_msg, answer_text)
                except Exception as error:
                    app.logger.error(
                        "chat retention write failed: %s", type(error).__name__
                    )
                threading.Thread(
                    target=_notify_telegram,
                    args=(client_key, user_msg, answer_text),
                    daemon=True,
                ).start()
            _log_provider_result(
                request_id=request_id,
                started_at=started_at,
                status=status,
                finish_reason=finish_reason,
                parser=parser,
                decision=decision,
            )

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain; charset=utf-8",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-store",
            "X-Request-ID": request_id,
            **_rate_headers(decision),
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
