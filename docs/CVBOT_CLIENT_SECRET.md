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

The #113 product tree is stacked on ready #124 head `682a66a7db419cf151502224646c4d0437f2b9c5`. Bounded finalizer run `31272192094` applied the dedicated-secret policy, ran the focused startup, storage, retention, contact-privacy and deploy-contract regressions plus source validation, guarded the diff scope, removed its temporary bootstrap files, and published product head `0769c4649c8dcc7b581c16016c65a36d08f4fec2` successfully.

No production secret was generated or rotated, no SQLite state was cleared, and no deployment or production runtime mutation occurred during that validation.
