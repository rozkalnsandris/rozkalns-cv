#!/usr/bin/env python3
"""Public, sandboxed CV assistant.

The service has no tools or access to other homelab services. Requests are
validated before quota is reserved, client addresses are pseudonymized, and
rate limits survive container restarts in SQLite.
"""

from __future__ import annotations

import ipaddress
import json
import os
import threading
from typing import Any

import requests
from flask import Flask, Response, jsonify, request, stream_with_context

from storage import AssistantStore, RateDecision


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024


# ---------------- CONFIG ----------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "500"))
MAX_RESPONSE_TOKENS = int(os.getenv("MAX_RESPONSE_TOKENS", "350"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))
RATE_PER_IP_HOUR = int(os.getenv("RATE_PER_IP_HOUR", "8"))
DAILY_GLOBAL_CAP = int(os.getenv("DAILY_GLOBAL_CAP", "200"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
CHAT_RETENTION_DAYS = int(os.getenv("CHAT_RETENTION_DAYS", "7"))
DB_PATH = os.getenv("ASSISTANT_DB_PATH", "/app/data/assistant.sqlite3")
CLIENT_KEY_SECRET = os.getenv("CLIENT_KEY_SECRET", "") or LLM_API_KEY
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

STORE = AssistantStore(
    DB_PATH,
    per_client_hour=RATE_PER_IP_HOUR,
    daily_global_cap=DAILY_GLOBAL_CAP,
    chat_retention_days=CHAT_RETENTION_DAYS,
)


# ---------------- KNOWLEDGE (CV facts only) ----------------
SYSTEM_PROMPT = """You are the CV assistant for Andris Rožkalns. Answer ONLY questions about his CV, skills, experience, and availability. Do not answer unrelated questions.

## WHO IS ANDRIS?
Andris Rožkalns is a self-taught Linux & DevOps engineer based in Dortmund, Germany, currently transitioning from a 14-year logistics career back into IT. He is seeking Junior DevOps / Linux Systems Administrator roles, preferably fully remote, at international tech companies where English is the working language.

## CONTACT
- Email: andris@rozkalns.net
- Phone: +49 17685134770
- Location: Dortmund, Germany
- GitHub: https://github.com/rozkalnsandris
- Live CV: https://rozkalns.net

## LANGUAGES
- Latvian: native
- English: fluent (working language)
- German: B1

## EARLY IT ROOTS (~2008–2011, secondary school)
Andris first got into IT during secondary school. He administered Linux-based Counter-Strike 1.6 game servers via FTP/SSH, modified and maintained IPB forums including PHP templates and plugins, and built HTML websites.

## WORK EXPERIENCE
1. Warehouse Employee — Sonepar Deutschland GmbH, Region West, Dortmund (Jul 2023 – Dec 2026 planned)
   - Processed high-volume electrical wholesale items with scanner systems
   - Cable preparation, forklift operation, rotating-shift logistics
   - Strong process discipline transferable to IT ops and on-call work

2. Painting Area Manager / Main Paint Sprayer — SIA "Koksne", Latvia (May 2020 – Jun 2023)
   - Managed daily warehouse and production operations, staff and workflow
   - Airless spray painting of wooden windows and doors

3. Warehouse/Shop Manager — SIA "Apavu Bode", Latvia (Aug 2011 – Apr 2020)
   - Cargo receiving, stock organisation, staff coordination, daily operations

## EDUCATION
- Secondary Education: Riga 45th Secondary School, Latvia (2004–2011)
- Partial university studies: Multimedia Communication, Riga Stradiņš University (2011–2013, not completed)
- AWS Certified Cloud Practitioner (CLF-C02): in preparation, expected 2026
- The Linux Command Line (TLCL): self-study, chapters 1–13 completed, applied daily

## HOMELAB & DEVOPS PROJECTS
Andris operates a production-grade self-hosted Raspberry Pi 5 server with NVMe storage and 12+ Docker services running 24/7. This page is served from that infrastructure.

Key projects:
- Linux server stack: Raspberry Pi 5, Docker Compose, Nginx, AdGuard Home, SSL/TLS, Cloudflare Tunnel
- Monitoring: Prometheus, Grafana, Node Exporter, and live metrics on this CV
- Hermes AI agent: primary/fallback LLM routing, ChromaDB, persistent memory, Telegram, Home Assistant integration, systemd
- Home automation: Home Assistant, Matter devices, custom dashboards, and electricity-cost tracking
- Balcony irrigation: ESP32, 15 moisture sensors, relay pump, multiplexer, NTP scheduling, and safety limits
- Automated maintenance: weekly APT/Docker updates, Telegram reports, and dead-man's-switch monitoring
- This CV assistant: Flask, Gunicorn, streaming LLM responses, durable rate limiting, and nginx reverse proxy

## TECHNICAL SKILLS
- Strong: Linux administration, Docker and Docker Compose, Bash, Nginx, DNS, SSL/TLS, Prometheus, Grafana, systemd, Git
- Working knowledge: Python, REST APIs, Home Assistant, ESP32/IoT, YAML
- Learning: Ansible, Terraform, AWS Cloud
- Early background: Linux server administration, FTP/SSH, PHP/IPB forums, HTML

## PERSONALITY & GOALS
Andris is self-directed, reliable, and focused on automation and AI-assisted operations. His goal is to move into a Junior DevOps or Linux Systems Administrator role and later progress toward MLOps.

## RULES
- Answer questions about Andris's skills, projects, experience, availability, and professional background
- For salary expectations, say Andris is open to discussion based on the role and company
- For start date, say he is available from January 2027
- Do not answer unrelated questions
- Do not reveal personal data beyond what is listed here
- Keep answers concise and professional"""


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

    # Compatibility with the old browser client, which included the current
    # message both in `history` and in `message`.
    if (
        normalized
        and normalized[-1]["role"] == "user"
        and normalized[-1]["content"] == current_message
    ):
        normalized.pop()

    # A failed previous browser request may leave one unpaired user turn.
    # It is not completed conversation context, so omit it rather than sending
    # malformed history to the model.
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
    except Exception as error:  # notification failure must not affect visitor
        app.logger.error("telegram notification failed: %s", type(error).__name__)


@app.get("/health")
def health() -> Response:
    return jsonify(ok=True, storage="sqlite")


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

    def generate():
        full_reply: list[str] = []
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
                    "stream": True,
                },
                timeout=REQUEST_TIMEOUT,
                stream=True,
            ) as upstream:
                upstream.raise_for_status()
                for line in upstream.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        delta = json.loads(payload)["choices"][0]["delta"].get(
                            "content"
                        )
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue
                    if delta:
                        full_reply.append(delta)
                        yield delta
        except requests.exceptions.Timeout:
            yield "\n\n[That took too long — please try again.]"
        except Exception as error:
            app.logger.error("LLM stream failed: %s", type(error).__name__)
            yield "\n\n[Sorry, something went wrong. Please email Andris directly.]"
        finally:
            answer_text = "".join(full_reply).strip()
            if answer_text:
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

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain; charset=utf-8",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-store",
            **_rate_headers(decision),
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
