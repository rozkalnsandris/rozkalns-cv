# CV assistant privacy and abuse-control policy

## Data flow

The public path is Cloudflare Tunnel -> nginx (`cv`) -> Flask/Gunicorn (`cvbot`) -> OpenAI Responses API.

nginx accepts `CF-Connecting-IP` only from the pinned CV Docker network. It replaces any visitor-supplied forwarding headers before proxying to `cvbot`. `cvbot` accepts the normalized `X-Real-IP` value only from nginx's fixed `172.19.0.10` address.

For an admitted chat request, cvbot sends OpenAI only the system instructions, the validated bounded user/assistant conversation context, the current user message, and the local HMAC client pseudonym as `safety_identifier`. The raw visitor IP is not used as the OpenAI safety identifier.

The provider request sets `store=false` and does not use an OpenAI Conversation object or `previous_response_id`; conversation context remains application-managed. `store=false` is not a blanket zero-retention claim: OpenAI documents separate abuse-monitoring retention, normally up to 30 days unless account-level Modified Abuse Monitoring or Zero Data Retention controls are separately approved/configured.

Provider data-control reference: https://developers.openai.com/api/docs/guides/your-data

## Client identity

Raw visitor IP addresses are not stored by the assistant. The validated address is converted into a 24-character HMAC-SHA256 pseudonym using `CLIENT_KEY_SECRET`. The pseudonym is used for per-client limits, optional local retained-conversation association, chat-admission binding, and the OpenAI `safety_identifier` field.

`CLIENT_KEY_SECRET` is mandatory, runtime-only and separate from `LLM_API_KEY`. Startup rejects a missing, malformed, too-short, or provider-key-equal pseudonymization secret. There is no fallback from the dedicated pseudonymization key to the provider API key.

## Rate limiting

Rate state is stored in `/app/data/assistant.sqlite3`, so container restarts do not restore a visitor's or the global quota.

- malformed/empty/oversized requests are rejected before quota is reserved;
- one validated attempt sent to the LLM provider consumes quota even if the provider later times out or returns an error;
- per-client events expire after one hour;
- global usage is counted per UTC day;
- 429 responses include `Retry-After` and rate-limit metadata.

## Conversation retention

`CHAT_RETENTION_DAYS=0` is the local privacy-minimizing default. With that value, successful question/answer content is not inserted into the local `chats` table.

If `CHAT_RETENTION_DAYS` is set to a positive value, successful question/answer pairs are retained in SQLite for up to the configured number of days. The retention policy is applied at startup and by bounded maintenance cleanup; new retained chats wake the cleanup loop so the next expiry is recalculated promptly.

The client field is the HMAC pseudonym, never the raw address. See `docs/CVBOT_DATA_RETENTION.md` for the detailed local retention lifecycle.

Local `CHAT_RETENTION_DAYS=0` must never be presented as proof of zero retention by OpenAI. External-provider retention is governed by the actual OpenAI API account/data-control configuration and current OpenAI policy.

## Telegram notifications

Notifications contain only a pseudonymous client identifier by default. Question and answer content is included only when `TELEGRAM_INCLUDE_CONTENT=true` is explicitly configured. Content forwarding should remain disabled unless a documented operational need outweighs the privacy cost.

## Deletion

Delete all locally retained conversation content on the RPi5:

```bash
cd /home/andris/rozkalns-cv
sudo python3 scripts/purge-chat-data.py
```

Delete only local rows older than a chosen age:

```bash
sudo python3 scripts/purge-chat-data.py --older-than-days 2
```

The utility deletes only rows from the local `chats` table. Rate-limit state remains intact so deleting conversation content cannot reset abuse controls. These commands do not delete any provider-side abuse-monitoring data.

## Public disclosure

The frontend must disclose LLM processing and the active local retention period before the visitor sends the first message. The public Privacy / Datenschutz notice must match the actual OpenAI and Cloudflare configuration at rollout time.

Before a production rollout that changes or republishes this notice, read-only preflight evidence must confirm all of the following without exposing secret values:

- the active `CHAT_RETENTION_DAYS` value matches the local-retention wording;
- `TELEGRAM_INCLUDE_CONTENT` remains `false` if the notice says question/answer text is not forwarded in operational notifications;
- Cloudflare Web Analytics is actually enabled if the notice says it is enabled;
- no OpenAI Zero Data Retention, Modified Abuse Monitoring, or EU data-residency feature is claimed unless fresh account evidence confirms it.

A mismatch is a rollout blocker and requires a source/privacy correction or an explicitly authorized runtime-policy change before LIVE.
