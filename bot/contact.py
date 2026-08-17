from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable

import requests

from turnstile import (
    MAX_TOKEN_CHARS,
    SITEVERIFY_URL,
    SiteverifyError,
    normalize_siteverify_token,
    verify_siteverify,
)


TURNSTILE_ACTION = "contact_reveal"


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
        email=os.getenv("CONTACT_EMAIL", "").strip(),
        phone_display=os.getenv("CONTACT_PHONE_DISPLAY", "").strip(),
        phone_uri=os.getenv("CONTACT_PHONE_URI", "").strip(),
        hostnames=hostnames,
    )


def normalize_token(value: object) -> str:
    if not isinstance(value, str):
        raise ContactVerificationError("Turnstile token must be text.")
    token = normalize_siteverify_token(value)
    if token is None:
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
        payload = verify_siteverify(
            token,
            remote_ip,
            config.secret_key,
            post=post,
            timeout=timeout,
        )
    except SiteverifyError as error:
        raise ContactVerificationError("Turnstile verification is unavailable.") from error

    if payload.get("success") is not True:
        return False
    if payload.get("action") != TURNSTILE_ACTION:
        return False
    hostname = payload.get("hostname")
    if not isinstance(hostname, str) or hostname.lower() not in config.hostnames:
        return False
    return True
