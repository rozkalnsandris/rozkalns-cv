#!/usr/bin/env python3
"""
CV assistant — a SANDBOXED, STREAMING chatbot for the public CV page.

Hard safety boundaries (by design):
  * No tools, no function calling, no email, no Home Assistant, no ChromaDB.
  * Knows ONLY the CV facts baked into SYSTEM_PROMPT below.
  * Per-IP and global daily rate limits; capped input length & response tokens.
Responses are STREAMED token-by-token so the page feels real-time.
This is deliberately NOT your Hermes agent. It cannot touch anything.
"""

import os
import json
import time
import threading
from collections import defaultdict, deque

import requests
from flask import Flask, request, jsonify, Response, stream_with_context

app = Flask(__name__)

# ---------------- CONFIG (via environment / .env) ----------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "")
LLM_MODEL    = os.getenv("LLM_MODEL", "deepseek-chat")

MAX_INPUT_CHARS     = int(os.getenv("MAX_INPUT_CHARS", "500"))
MAX_RESPONSE_TOKENS = int(os.getenv("MAX_RESPONSE_TOKENS", "350"))
MAX_HISTORY_TURNS   = int(os.getenv("MAX_HISTORY_TURNS", "6"))
RATE_PER_IP_HOUR    = int(os.getenv("RATE_PER_IP_HOUR", "8"))
DAILY_GLOBAL_CAP    = int(os.getenv("DAILY_GLOBAL_CAP", "200"))
REQUEST_TIMEOUT     = int(os.getenv("REQUEST_TIMEOUT", "60"))

# ---------------- LOGGING / TELEGRAM NOTIFICATIONS ----------------
LOG_DIR = os.getenv("CHAT_LOG_DIR", "/app/data")
LOG_FILE = os.path.join(LOG_DIR, "chat_log.jsonl")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID", "")


def _log_chat(ip: str, question: str, answer: str):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ip": ip,
            "question": question,
            "answer": answer,
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        app.logger.error(f"chat log write failed: {e}")


def _notify_telegram(ip: str, question: str, answer: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        q = question[:300]
        a = answer[:600]
        text = f"CV asistents\nIP: {ip}\n\nJautajums: {q}\n\nAtbilde: {a}"
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
    except Exception as e:
        app.logger.error(f"telegram notify failed: {e}")


# ---------------- KNOWLEDGE (CV facts only) ----------------
SYSTEM_PROMPT = """You are the CV assistant for Andris Rožkalns. Answer ONLY questions about his CV, skills, experience, and availability. Do not answer unrelated questions.

## WHO IS ANDRIS?
Andris Rožkalns is a self-taught Linux & DevOps engineer based in Dortmund, Germany, currently transitioning from a 14-year logistics career back into IT. He is seeking Junior DevOps / Linux Systems Administrator roles, preferably fully remote, at international tech companies where English is the working language (e.g. Zalando, HelloFresh, etc.).

## CONTACT
- Email: andris@rozkalns.net
- Phone: +49 17685134770
- Location: Meylantstr. 10, 44319 Dortmund, Germany
- GitHub: https://github.com/rozkalnsandris
- Live CV: https://rozkalns.net

## LANGUAGES
- Latvian: native
- English: fluent (working language)
- German: B1

## EARLY IT ROOTS (~2008–2011, secondary school)
Andris first got into IT during secondary school (grades 9–12 at Riga 45th Secondary School, graduating 2011). He administered Linux-based Counter-Strike 1.6 game servers via FTP/SSH, modified and maintained IPB (Invision Power Board) forums including PHP templates and plugins, and built HTML websites. This was his first hands-on experience with Linux servers and web technologies.

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

## HOMELAB & DEVOPS PROJECTS (production infrastructure running 24/7)
Andris operates a production-grade self-hosted server on Raspberry Pi 5 with NVMe SSD running 12+ Docker services around the clock. This page is served directly from that infrastructure.

Key projects:
- **Linux Server Stack**: Raspberry Pi 5, Docker Compose, Nginx Proxy Manager, AdGuard Home DNS filtering, DuckDNS + Let's Encrypt wildcard SSL, Cloudflare Tunnel
- **Monitoring & Observability**: Prometheus (30-day retention), Grafana dashboards, Node Exporter, Speedtest Exporter — the live stats on this page come from this stack
- **AI Agent (Hermes Gateway)**: Production AI agent with primary/fallback LLM routing (DeepSeek → Claude Haiku → Claude Sonnet), ChromaDB vector database, SQLite memory, Home Assistant MCP integration, Telegram bot interface, systemd-managed service
- **Home Automation**: Home Assistant with Matter protocol (KE100/KH100 thermostats instant response), custom glassmorphism YAML dashboard, electricity cost tracking with utility meters and ApexCharts
- **Balcony Irrigation System**: ESP32 + 15 soil moisture sensors + relay-controlled pump + CD74HC4067 MUX, Telegram bot control, NTP-synced scheduling
- **Automated Maintenance**: Weekly update pipeline (APT + Docker), Telegram before/after reporting, dead man's switch via healthchecks.io
- **This CV chatbot**: Flask + gunicorn, streaming LLM responses, rate limiting, moderation filter, served via nginx reverse proxy

## TECHNICAL SKILLS
- **Strong**: Linux administration (Debian/Ubuntu/RPi OS), Docker & Docker Compose, Bash scripting, Nginx, DNS, SSL/TLS, Prometheus, Grafana, systemd, Git
- **Working knowledge**: Python, REST APIs, Home Assistant, ESP32/IoT, YAML configuration
- **Learning**: Ansible, Terraform, AWS Cloud (CLF-C02 prep)
- **Early background**: Linux server admin, FTP/SSH, PHP (IPB forums), HTML

## PERSONALITY & GOALS
Andris is highly motivated, self-directed, and passionate about automation and AI integration. He is making a deliberate career transition — not just a job change — returning to IT roots that date back to his school years. His homelab represents real production DevOps experience: he designs, deploys, monitors, and maintains infrastructure that serves real users 24/7. His long-term goal is MLOps (Junior DevOps first, then MLOps after 2–3 years of professional experience).

## WHAT YOU SHOULD AND SHOULD NOT DO
- Answer questions about Andris's skills, projects, experience, availability, and background
- If asked about salary expectations, say Andris is open to discussion based on the role and company
- If asked about start date, say he is available from January 2027 (current contract ends December 2026)
- Do NOT answer questions unrelated to Andris's CV or professional profile
- Do NOT reveal personal data beyond what is listed above
- Keep answers concise and professional; you are a CV assistant, not a general chatbot"""

# ---------------- RATE LIMITING (in-memory) ----------------
_lock = threading.Lock()
_ip_hits = defaultdict(deque)
_day = {"date": time.strftime("%Y-%m-%d"), "count": 0}


def _allowed(ip: str):
    now = time.time()
    today = time.strftime("%Y-%m-%d")
    with _lock:
        if _day["date"] != today:
            _day["date"], _day["count"] = today, 0
        if _day["count"] >= DAILY_GLOBAL_CAP:
            return False, "The assistant has reached today's usage limit. Please email Andris instead."
        dq = _ip_hits[ip]
        while dq and now - dq[0] > 3600:
            dq.popleft()
        if len(dq) >= RATE_PER_IP_HOUR:
            return False, "You've sent several messages — please wait a bit, or email Andris directly."
        dq.append(now)
        _day["count"] += 1
        return True, None


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.post("/chat")
def chat():
    if not LLM_API_KEY:
        return jsonify(reply="The assistant isn't configured yet."), 503

    ip = request.headers.get("X-Real-IP", request.remote_addr or "unknown")
    ok, msg = _allowed(ip)
    if not ok:
        return jsonify(reply=msg), 429

    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_msg:
        return jsonify(reply="Ask me anything about Andris's experience or skills."), 400
    if len(user_msg) > MAX_INPUT_CHARS:
        return jsonify(reply=f"Please keep questions under {MAX_INPUT_CHARS} characters."), 400

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history[-(MAX_HISTORY_TURNS * 2):]:
        role = turn.get("role")
        content = (turn.get("content") or "")[:MAX_INPUT_CHARS]
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_msg})

    def generate():
        full_reply = []
        try:
            with requests.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}",
                         "Content-Type": "application/json"},
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "max_tokens": MAX_RESPONSE_TOKENS,
                    "temperature": 0.4,
                    "stream": True,
                },
                timeout=REQUEST_TIMEOUT,
                stream=True,
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        delta = json.loads(payload)["choices"][0]["delta"].get("content")
                        if delta:
                            full_reply.append(delta)
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except requests.exceptions.Timeout:
            yield "\n\n[That took too long — please try again.]"
        except Exception as e:
            app.logger.error(f"LLM stream error: {e}")
            yield "\n\n[Sorry, something went wrong. Please email Andris directly.]"
        finally:
            answer_text = "".join(full_reply).strip()
            if answer_text:
                _log_chat(ip, user_msg, answer_text)
                threading.Thread(
                    target=_notify_telegram,
                    args=(ip, user_msg, answer_text),
                    daemon=True,
                ).start()

    return Response(stream_with_context(generate()),
                    mimetype="text/plain; charset=utf-8",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
