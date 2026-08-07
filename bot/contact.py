from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable

import requests


SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TURNSTILE_ACTION = "contact_reveal"
MAX_TOKEN_CHARS = 2048


class ContactVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ContactConfig:
    site_key: str
    secret_key: str
    email: str
    phone_display: str
    phone_uri: str
    hostnames: frozenset[str]

    @property
    def configured(self) -> bool:
        return bool(
            self.site_key
            and self.secret_key
            and self.email
            and self.phone_display
            and self.phone_uri
            and self.hostnames
        )


def load_contact_config() -> ContactConfig:
    hostnames = frozenset(
        item.strip().lower()
        for item in os.getenv("TURNSTILE_HOSTNAMES", "rozkalns.net").split(",")
        if item.strip()
    )
    return ContactConfig(
        site_key=os.getenv("TURNSTILE_SITE_KEY", "").strip(),
        secret_key=os.getenv("TURNSTILE_SECRET_KEY", "").strip(),
        email=os.getenv("CONTACT_EMAIL", "andris@rozkalns.net").strip(),
        phone_display=os.getenv("CONTACT_PHONE_DISPLAY", "+49 176 8513 4770").strip(),
        phone_uri=os.getenv("CONTACT_PHONE_URI", "+4917685134770").strip(),
        hostnames=hostnames,
    )


def normalize_token(value: object) -> str:
    if not isinstance(value, str):
        raise ContactVerificationError("Turnstile token must be text.")
    token = value.strip()
    if not token or len(token) > MAX_TOKEN_CHARS:
        raise ContactVerificationError("Turnstile token is invalid.")
    return token


def verify_turnstile(
    token: str,
    remote_ip: str,
    config: ContactConfig,
    *,
    post: Callable[..., requests.Response] = requests.post,
    timeout: float = 8.0,
) -> bool:
    if not config.configured:
        raise ContactVerificationError("Contact verification is not configured.")
    token = normalize_token(token)
    try:
        response = post(
            SITEVERIFY_URL,
            data={
                "secret": config.secret_key,
                "response": token,
                "remoteip": remote_ip,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise ContactVerificationError("Turnstile verification is unavailable.") from error
    except ValueError as error:
        raise ContactVerificationError("Turnstile returned invalid JSON.") from error

    if not isinstance(payload, dict) or payload.get("success") is not True:
        return False
    if payload.get("action") != TURNSTILE_ACTION:
        return False
    hostname = payload.get("hostname")
    if not isinstance(hostname, str) or hostname.lower() not in config.hostnames:
        return False
    return True
