#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str, label: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"C113_PATCH=FAIL anchor={label} count={count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_storage() -> None:
    replace_once(
        "bot/storage.py",
        "from dataclasses import dataclass\n",
        "import base64\nimport binascii\nfrom dataclasses import dataclass\n",
        "storage-imports",
    )
    replace_once(
        "bot/storage.py",
        "LOGGER = logging.getLogger(__name__)\n\n\n@dataclass(frozen=True)\n",
        '''LOGGER = logging.getLogger(__name__)

CLIENT_KEY_SECRET_MIN_BYTES = 32
_CLIENT_KEY_SECRET_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


class ClientKeySecretError(RuntimeError):
    """Raised when the dedicated pseudonymization key is unsafe to use."""


def validate_client_key_secret(value: str, provider_key: str = "") -> str:
    """Validate a dedicated URL-safe HMAC key without exposing its value."""

    if not isinstance(value, str) or not value:
        raise ClientKeySecretError("CLIENT_KEY_SECRET is required")
    if not value.isascii() or any(
        character not in _CLIENT_KEY_SECRET_ALPHABET for character in value
    ):
        raise ClientKeySecretError("CLIENT_KEY_SECRET has invalid format")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(
            value + padding, altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as error:
        raise ClientKeySecretError(
            "CLIENT_KEY_SECRET has invalid format"
        ) from error
    if len(decoded) < CLIENT_KEY_SECRET_MIN_BYTES:
        raise ClientKeySecretError("CLIENT_KEY_SECRET is too short")
    if provider_key and hmac.compare_digest(value, provider_key):
        raise ClientKeySecretError(
            "CLIENT_KEY_SECRET must be dedicated to pseudonymization"
        )
    return value


@dataclass(frozen=True)
''',
        "storage-validator",
    )


def patch_app_and_examples() -> None:
    replace_once(
        "bot/app.py",
        "from storage import AssistantStore, RateDecision\n",
        "from storage import (\n    AssistantStore,\n    RateDecision,\n    validate_client_key_secret,\n)\n",
        "app-storage-import",
    )
    replace_once(
        "bot/app.py",
        'CLIENT_KEY_SECRET = os.getenv("CLIENT_KEY_SECRET", "") or LLM_API_KEY\n',
        'CLIENT_KEY_SECRET = validate_client_key_secret(\n    os.getenv("CLIENT_KEY_SECRET", ""), LLM_API_KEY\n)\n',
        "app-no-provider-fallback",
    )
    replace_once(
        "bot/.env.example",
        "CLIENT_KEY_SECRET=replace-with-a-long-random-secret\n",
        "CLIENT_KEY_SECRET=!generate-with-secrets-token-urlsafe-32!\n",
        "env-example",
    )


def patch_tests() -> None:
    replace_once(
        "tests/test_storage.py",
        "from storage import AssistantStore\n",
        "from storage import (\n    AssistantStore,\n    ClientKeySecretError,\n    validate_client_key_secret,\n)\n",
        "storage-test-import",
    )
    replace_once(
        "tests/test_storage.py",
        "    def test_pseudonym_is_stable_and_does_not_contain_address(self) -> None:\n",
        '''    def test_dedicated_client_key_secret_contract(self) -> None:
        dedicated = "A" * 43
        self.assertEqual(
            validate_client_key_secret(dedicated, "provider-key"), dedicated
        )
        for invalid in ("", "short", "!" + dedicated):
            with self.subTest(invalid=bool(invalid)):
                with self.assertRaises(ClientKeySecretError):
                    validate_client_key_secret(invalid, "provider-key")

    def test_provider_key_cannot_be_reused_for_pseudonymization(self) -> None:
        shared = "B" * 43
        with self.assertRaises(ClientKeySecretError):
            validate_client_key_secret(shared, shared)

    def test_pseudonym_is_stable_and_does_not_contain_address(self) -> None:
''',
        "storage-secret-tests",
    )
    for path in ("tests/test_bot.py", "tests/test_bot_failures.py"):
        replace_once(
            path,
            '"CLIENT_KEY_SECRET": "test-client-secret",',
            '"CLIENT_KEY_SECRET": "A" * 43,',
            f"{path}-secret-fixture",
        )

    startup_test = '''from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"


class ClientKeySecretStartupTests(unittest.TestCase):
    def _import_app(
        self, *, client_secret: str | None, provider_key: str
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.update(
                {
                    "LLM_API_KEY": provider_key,
                    "ASSISTANT_DB_PATH": str(Path(tmp) / "assistant.sqlite3"),
                    "CHAT_RETENTION_DAYS": "0",
                    "TELEGRAM_TOKEN": "",
                    "CHAT_ID": "",
                }
            )
            if client_secret is None:
                env.pop("CLIENT_KEY_SECRET", None)
            else:
                env["CLIENT_KEY_SECRET"] = client_secret
            return subprocess.run(
                [sys.executable, "-c", "import app"],
                cwd=BOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_missing_secret_fails_startup_without_provider_fallback(self) -> None:
        result = self._import_app(
            client_secret=None, provider_key="provider-secret-marker"
        )
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("CLIENT_KEY_SECRET", combined)
        self.assertNotIn("provider-secret-marker", combined)

    def test_provider_key_reuse_fails_startup(self) -> None:
        shared = "B" * 43
        result = self._import_app(client_secret=shared, provider_key=shared)
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("dedicated", combined)
        self.assertNotIn(shared, combined)

    def test_valid_dedicated_secret_allows_startup(self) -> None:
        result = self._import_app(
            client_secret="A" * 43, provider_key="provider-key"
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
'''
    (ROOT / "tests/test_client_key_secret.py").write_text(
        startup_test, encoding="utf-8"
    )

    deploy_test = ROOT / "tests/test_deploy_contract.py"
    text = deploy_test.read_text(encoding="utf-8")
    anchor = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
    addition = '''
    def test_cvbot_client_secret_is_validated_without_disclosure(self) -> None:
        helper = read(HELPER)
        for marker in (
            "validate_cvbot_runtime_secret()",
            'values.get("CLIENT_KEY_SECRET", "")',
            "len(decoded) < 32",
            "hmac.compare_digest(secret, provider)",
            "CVBOT_CLIENT_KEY_SECRET=PASS",
            "validate_cvbot_runtime_secret || return 1",
        ):
            self.assertIn(marker, helper)
        for forbidden in (
            'echo "$CLIENT_KEY_SECRET"',
            'echo "$LLM_API_KEY"',
            'printf "%s" "$CLIENT_KEY_SECRET"',
            'printf "%s" "$LLM_API_KEY"',
        ):
            self.assertNotIn(forbidden, helper)
'''
    if text.count(anchor) != 1:
        raise SystemExit(
            f"C113_PATCH=FAIL anchor=deploy-test count={text.count(anchor)}"
        )
    deploy_test.write_text(text.replace(anchor, addition + anchor, 1), encoding="utf-8")


def patch_deploy() -> None:
    deploy = ROOT / "runner/release/rozkalns-cv-deploy-main"
    text = deploy.read_text(encoding="utf-8")
    anchor = "\nprepare_cvbot_data() {\n"
    validator = r'''
validate_cvbot_runtime_secret() {
    local env_file="$RUNTIME/bot/.env"
    [[ -f "$env_file" && ! -L "$env_file" ]] || return 1
    python3 - "$env_file" <<'PY_SECRET'
from __future__ import annotations

import base64
import binascii
import hmac
from pathlib import Path
import sys

path = Path(sys.argv[1])
values: dict[str, str] = {}
for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    key, separator, value = line.partition("=")
    key = key.strip()
    if not separator or key not in {"CLIENT_KEY_SECRET", "LLM_API_KEY"}:
        continue
    if key in values:
        raise SystemExit("cvbot secret contract failed: duplicate key")
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    values[key] = value

secret = values.get("CLIENT_KEY_SECRET", "")
allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
if not secret or not secret.isascii() or any(
    character not in allowed for character in secret
):
    raise SystemExit("cvbot client pseudonymization secret contract failed")
padding = "=" * ((4 - len(secret) % 4) % 4)
try:
    decoded = base64.b64decode(secret + padding, altchars=b"-_", validate=True)
except (binascii.Error, ValueError):
    raise SystemExit(
        "cvbot client pseudonymization secret contract failed"
    ) from None
if len(decoded) < 32:
    raise SystemExit("cvbot client pseudonymization secret contract failed")
provider = values.get("LLM_API_KEY", "")
if provider and hmac.compare_digest(secret, provider):
    raise SystemExit("cvbot client pseudonymization secret must be dedicated")
print("CVBOT_CLIENT_KEY_SECRET=PASS")
PY_SECRET
}

prepare_cvbot_data() {
'''
    if text.count(anchor) != 1:
        raise SystemExit(
            f"C113_PATCH=FAIL anchor=deploy-validator count={text.count(anchor)}"
        )
    text = text.replace(anchor, "\n" + validator, 1)

    runtime_anchor = '''deploy_runtime() {
    normalize_managed_permissions "$RUNTIME" || return 1
    prepare_cvbot_data || return 1
'''
    runtime_new = '''deploy_runtime() {
    normalize_managed_permissions "$RUNTIME" || return 1
    validate_cvbot_runtime_secret || return 1
    prepare_cvbot_data || return 1
'''
    if text.count(runtime_anchor) != 1:
        raise SystemExit(
            f"C113_PATCH=FAIL anchor=deploy-runtime count={text.count(runtime_anchor)}"
        )
    deploy.write_text(
        text.replace(runtime_anchor, runtime_new, 1), encoding="utf-8"
    )


def write_docs() -> None:
    docs = '''# CV assistant pseudonymization secret

`CLIENT_KEY_SECRET` is a dedicated runtime-only HMAC key for visitor pseudonyms. It must never fall back to or equal `LLM_API_KEY`.

## Generate

Generate a fresh URL-safe token from 32 random bytes on the production host, for example:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Store the resulting value only in the protected production `bot/.env` as `CLIENT_KEY_SECRET`. The tracked `.env.example` intentionally contains an invalid placeholder so copying it unchanged fails closed.

## Startup and deploy contract

Startup rejects a missing, empty, malformed, too-short, or provider-key-equal value with a sanitized error that never includes either secret. Deployment checks the same presence, URL-safe encoding, decoded minimum length, and domain-separation contract before starting cvbot. Deploy evidence records only `CVBOT_CLIENT_KEY_SECRET=PASS`.

## Rotation

Pseudonyms are deterministic only while this secret is unchanged. Rotating it changes future HMAC pseudonyms, so existing per-client rate-limit rows and any retained rows keyed by the old pseudonym will no longer correlate to new requests. Rotation does not automatically delete SQLite state. Existing rate events age out under the rate-limit policy and raw chat rows follow `CHAT_RETENTION_DAYS`.

If old pseudonymous identity state must be cleared for an operational reason, that is a separate, explicit maintenance action with its own authorization and evidence. Secret rotation itself must not silently delete rate-limit or retained-chat rows.

The runtime `.env` is excluded from source synchronization, application backups, manifests, logs, and normal deployment evidence; no secret value belongs in tracked files.
'''
    (ROOT / "docs/CVBOT_CLIENT_SECRET.md").write_text(docs, encoding="utf-8")


def main() -> int:
    patch_storage()
    patch_app_and_examples()
    patch_tests()
    patch_deploy()
    write_docs()
    print("C113_SOURCE_PATCH=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
