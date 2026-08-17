from __future__ import annotations

import ipaddress
import math
from typing import Callable
import uuid

import requests


SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
MAX_TOKEN_CHARS = 2048
MAX_ATTEMPTS = 2
DEFAULT_TOTAL_TIMEOUT = 8.0


class SiteverifyError(RuntimeError):
    pass


def normalize_siteverify_token(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token or len(token) > MAX_TOKEN_CHARS:
        return None
    return token


def verify_siteverify(
    token: object,
    remote_ip: str,
    secret_key: str,
    *,
    post: Callable[..., requests.Response] = requests.post,
    timeout: float = DEFAULT_TOTAL_TIMEOUT,
    uuid_factory: Callable[[], uuid.UUID] = uuid.uuid4,
) -> dict[str, object]:
    normalized_token = normalize_siteverify_token(token)
    if normalized_token is None or not secret_key:
        raise SiteverifyError("Turnstile verification request is invalid.")

    try:
        total_timeout = float(timeout)
    except (TypeError, ValueError) as error:
        raise SiteverifyError("Turnstile verification timeout is invalid.") from error
    if not math.isfinite(total_timeout) or total_timeout <= 0:
        raise SiteverifyError("Turnstile verification timeout is invalid.")

    try:
        idempotency_key = str(uuid.UUID(str(uuid_factory())))
    except (AttributeError, TypeError, ValueError) as error:
        raise SiteverifyError("Turnstile idempotency key is invalid.") from error

    data = {
        "secret": secret_key,
        "response": normalized_token,
        "idempotency_key": idempotency_key,
    }
    try:
        data["remoteip"] = ipaddress.ip_address(remote_ip).compressed
    except ValueError:
        pass

    # Two attempts share one logical eight-second budget. Requests applies the
    # tuple independently to connect and read phases, so each retry gets a
    # conservative quarter of the caller-provided total for each phase.
    phase_timeout = total_timeout / (MAX_ATTEMPTS * 2)
    request_timeout = (phase_timeout, phase_timeout)
    last_error: BaseException | None = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = post(
                SITEVERIFY_URL,
                data=data,
                timeout=request_timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            if attempt + 1 < MAX_ATTEMPTS:
                continue
            raise SiteverifyError("Turnstile verification is unavailable.") from error
        except requests.RequestException as error:
            raise SiteverifyError("Turnstile verification is unavailable.") from error

        status_code = getattr(response, "status_code", 200)
        if isinstance(status_code, int) and 500 <= status_code <= 599:
            last_error = SiteverifyError(
                f"Turnstile verification returned HTTP {status_code}."
            )
            if attempt + 1 < MAX_ATTEMPTS:
                continue
            raise SiteverifyError("Turnstile verification is unavailable.") from last_error
        if not isinstance(status_code, int) or not 200 <= status_code <= 299:
            raise SiteverifyError("Turnstile verification was rejected by the service.")

        try:
            payload = response.json()
        except ValueError as error:
            raise SiteverifyError("Turnstile verification returned invalid JSON.") from error
        if not isinstance(payload, dict):
            raise SiteverifyError("Turnstile verification returned an invalid payload.")
        return payload

    raise SiteverifyError("Turnstile verification is unavailable.") from last_error
