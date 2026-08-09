from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import ipaddress
import time
from typing import Callable

import requests

from contact import MAX_TOKEN_CHARS, SITEVERIFY_URL

CHAT_ADMISSION_ACTION = "chat_admission"
SESSION_TTL_SECONDS = 15 * 60


class ChatAdmissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatAdmissionConfig:
    site_key: str
    secret_key: str
    hostnames: frozenset[str]

    @property
    def configured(self) -> bool:
        return bool(self.site_key and self.secret_key and self.hostnames)


def verify_chat_turnstile(
    token: object,
    remote_ip: str,
    config: ChatAdmissionConfig,
    *,
    post: Callable[..., requests.Response] = requests.post,
    timeout: float = 8.0,
) -> bool:
    if not config.configured:
        raise ChatAdmissionError("Chat verification is not configured.")
    if not isinstance(token, str):
        return False
    token = token.strip()
    if not token or len(token) > MAX_TOKEN_CHARS:
        return False
    data = {"secret": config.secret_key, "response": token}
    try:
        data["remoteip"] = ipaddress.ip_address(remote_ip).compressed
    except ValueError:
        pass
    try:
        response = post(SITEVERIFY_URL, data=data, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise ChatAdmissionError("Chat verification is unavailable.") from error
    except ValueError as error:
        raise ChatAdmissionError("Chat verification returned invalid JSON.") from error
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return False
    if payload.get("action") != CHAT_ADMISSION_ACTION:
        return False
    hostname = payload.get("hostname")
    return isinstance(hostname, str) and hostname.lower() in config.hostnames


def issue_session(client_key: str, secret: str, *, now: int | None = None) -> str:
    current = int(time.time() if now is None else now)
    expires = current + SESSION_TTL_SECONDS
    payload = f"{client_key}.{expires}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def validate_session(
    token: object,
    client_key: str,
    secret: str,
    *,
    now: int | None = None,
) -> bool:
    if not isinstance(token, str) or len(token) > 256:
        return False
    try:
        expires_text, signature = token.strip().split(".", 1)
        expires = int(expires_text)
    except (ValueError, AttributeError):
        return False
    current = int(time.time() if now is None else now)
    if expires < current or expires > current + SESSION_TTL_SECONDS:
        return False
    payload = f"{client_key}.{expires}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
