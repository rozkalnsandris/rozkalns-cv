# CV assistant privacy and abuse-control policy

## Data flow

The public path is Cloudflare Tunnel -> nginx (`cv`) -> Flask/Gunicorn
(`cvbot`) -> the configured LLM provider.

nginx accepts `CF-Connecting-IP` only from the pinned CV Docker network. It
replaces any visitor-supplied forwarding headers before proxying to `cvbot`.
`cvbot` accepts the normalized `X-Real-IP` value only from nginx's fixed
`172.19.0.10` address.

## Client identity

Raw visitor IP addresses are not stored by the assistant. The validated address
is converted into a 24-character HMAC-SHA256 pseudonym using
`CLIENT_KEY_SECRET`. The pseudonym exists only to apply per-client limits and
associate short-lived retained conversations.

Use a long random `CLIENT_KEY_SECRET` that is separate from other credentials.
For migration compatibility, the application falls back to `LLM_API_KEY` when
the dedicated secret is missing, but production should set the dedicated value.

## Rate limiting

Rate state is stored in `/app/data/assistant.sqlite3`, so container restarts do
not restore a visitor's or the global quota.

- malformed/empty/oversized requests are rejected before quota is reserved;
- one validated attempt sent to the LLM provider consumes quota even if the
  provider later times out or returns an error;
- per-client events expire after one hour;
- global usage is counted per UTC day;
- 429 responses include `Retry-After` and rate-limit metadata.

## Conversation retention

Successful question/answer pairs are retained in SQLite for
`CHAT_RETENTION_DAYS` (default: 7). Cleanup occurs when a new successful chat is
recorded. Set `CHAT_RETENTION_DAYS=0` to disable conversation-content storage.

The client field is the HMAC pseudonym, never the raw address.

## Telegram notifications

Notifications contain only a pseudonymous client identifier by default.
Question and answer content is included only when
`TELEGRAM_INCLUDE_CONTENT=true` is explicitly configured. Content forwarding
should remain disabled unless a documented operational need outweighs the
privacy cost.

## Deletion

Delete all retained conversation content on the RPi5:

```bash
cd /home/andris/rozkalns-cv
sudo python3 scripts/purge-chat-data.py
```

Delete only rows older than a chosen age:

```bash
sudo python3 scripts/purge-chat-data.py --older-than-days 2
```

The utility deletes only rows from the `chats` table. Rate-limit state remains
intact so deleting conversation content cannot reset abuse controls.

## Public disclosure

The frontend must disclose the retention period and LLM processing before the
visitor sends the first message. That UI work is tracked separately and this
policy is not a substitute for the visible notice.
