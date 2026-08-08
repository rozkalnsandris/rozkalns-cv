# CV assistant pseudonymization secret

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

## Validation provenance

After #112 was squash-merged to `main` as `0149bed2b84803f6fd8c191920191730c7a887cb`, #113 was transplanted onto a clean current-main branch from previously full-CI-validated source head `449d9f5f21bad356e653ee8ea65d7c3b84aeaedf`. Bounded transplant run `31272628232` preserved the merged retention and public-contact contracts, reran the focused secret, storage, retention, contact, deploy, content and source validations, guarded exact diff scope, removed its temporary workflow, and published clean product head `5f9b96a2412c315b2a3190ddc2fac21c56da923b` successfully.

No production secret was generated or rotated, no SQLite state was cleared, and no deployment or production runtime mutation occurred during that validation.
