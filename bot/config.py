from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from typing import Mapping
from urllib.parse import urlparse

from storage import validate_client_key_secret

SUPPORTED_LLM_MODELS = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})


class SettingsError(ValueError):
    """Sanitized runtime configuration error."""


def _integer(env: Mapping[str, str], name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = env.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise SettingsError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise SettingsError(f"{name} is outside the allowed range")
    return value


def _number(env: Mapping[str, str], name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = env.get(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as error:
        raise SettingsError(f"{name} must be a number") from error
    if not minimum <= value <= maximum:
        raise SettingsError(f"{name} is outside the allowed range")
    return value


def _https_url(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(name, default).strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise SettingsError(f"{name} must be an HTTPS origin")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise SettingsError(f"{name} must not include path, query, or fragment")
    return value


def _trusted_proxy_cidrs(env: Mapping[str, str]) -> tuple[ipaddress._BaseNetwork, ...]:
    raw = env.get("TRUSTED_PROXY_CIDRS", "172.19.0.10/32")
    networks: list[ipaddress._BaseNetwork] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError as error:
            raise SettingsError("TRUSTED_PROXY_CIDRS contains an invalid CIDR") from error
    if not networks:
        raise SettingsError("TRUSTED_PROXY_CIDRS must contain at least one CIDR")
    return tuple(networks)


@dataclass(frozen=True, slots=True)
class VerificationRateConfig:
    per_client_hour: int
    global_hour: int

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None
    ) -> "VerificationRateConfig":
        source = os.environ if env is None else env
        return cls(
            per_client_hour=_integer(
                source,
                "TURNSTILE_VERIFY_PER_IP_HOUR",
                60,
                minimum=1,
                maximum=1000,
            ),
            global_hour=_integer(
                source,
                "TURNSTILE_VERIFY_GLOBAL_HOUR",
                600,
                minimum=1,
                maximum=100000,
            ),
        )


@dataclass(frozen=True, slots=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    max_input_chars: int
    max_response_tokens: int
    max_history_turns: int
    rate_per_ip_hour: int
    daily_global_cap: int
    llm_connect_timeout: float
    llm_read_timeout: float
    chat_retention_days: int
    db_path: str
    client_key_secret: str
    telegram_token: str
    telegram_chat_id: str
    telegram_include_content: bool
    trusted_proxy_cidrs: tuple[ipaddress._BaseNetwork, ...]

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = os.environ if env is None else env
        llm_api_key = source.get("LLM_API_KEY", "").strip()
        client_secret = validate_client_key_secret(
            source.get("CLIENT_KEY_SECRET", ""), llm_api_key
        )
        model = source.get("LLM_MODEL", "deepseek-v4-flash").strip()
        if model not in SUPPORTED_LLM_MODELS:
            raise SettingsError("LLM_MODEL must be a supported DeepSeek V4 model")
        db_path = source.get("ASSISTANT_DB_PATH", "/app/data/assistant.sqlite3").strip()
        if not db_path:
            raise SettingsError("ASSISTANT_DB_PATH must not be empty")
        return cls(
            llm_base_url=_https_url(source, "LLM_BASE_URL", "https://api.deepseek.com"),
            llm_api_key=llm_api_key,
            llm_model=model,
            max_input_chars=_integer(source, "MAX_INPUT_CHARS", 500, minimum=1, maximum=4000),
            max_response_tokens=_integer(source, "MAX_RESPONSE_TOKENS", 350, minimum=1, maximum=4096),
            max_history_turns=_integer(source, "MAX_HISTORY_TURNS", 6, minimum=0, maximum=20),
            rate_per_ip_hour=_integer(source, "RATE_PER_IP_HOUR", 8, minimum=1, maximum=1000),
            daily_global_cap=_integer(source, "DAILY_GLOBAL_CAP", 200, minimum=1, maximum=100000),
            llm_connect_timeout=_number(source, "LLM_CONNECT_TIMEOUT", 5, minimum=0.1, maximum=30),
            llm_read_timeout=_number(source, "LLM_READ_TIMEOUT", 70, minimum=1, maximum=300),
            chat_retention_days=_integer(source, "CHAT_RETENTION_DAYS", 0, minimum=0, maximum=365),
            db_path=db_path,
            client_key_secret=client_secret,
            telegram_token=source.get("TELEGRAM_TOKEN", "").strip(),
            telegram_chat_id=source.get("CHAT_ID", "").strip(),
            telegram_include_content=source.get("TELEGRAM_INCLUDE_CONTENT", "false").lower() in {"1", "true", "yes"},
            trusted_proxy_cidrs=_trusted_proxy_cidrs(source),
        )
