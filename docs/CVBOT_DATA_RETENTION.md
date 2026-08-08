# CV assistant data retention

The CV assistant keeps rate-limit state and optional raw conversation retention as separate concerns in the same SQLite database.

## Default policy

`CHAT_RETENTION_DAYS=0` is the privacy-minimizing default.

With that value:

- completed question/answer text is not inserted into the `chats` table;
- startup maintenance removes any raw chat rows left by an earlier nonzero policy;
- pseudonymous rate-limit events and daily usage counters remain intact so abuse limits still survive container restarts.

Changing the production runtime from a nonzero retention value to `0` therefore has a data-deletion effect on existing raw chat rows at the next cvbot start. That runtime-policy change and any production deployment remain separate owner-controlled operations; this source change does not itself delete production data.

## Optional nonzero retention

A positive `CHAT_RETENTION_DAYS` value explicitly opts into temporary storage of:

- pseudonymous `client_key`;
- question text;
- answer text;
- insertion timestamp.

Expiry no longer depends on another successful chat. `AssistantStore` applies the configured policy at startup and a single bounded maintenance janitor continues checking the oldest row while the process is idle. New chat inserts wake the janitor so the next expiry is recalculated promptly. Cleanup uses SQLite `BEGIN IMMEDIATE`, the existing `chats(occurred_at)` index, and the same WAL database as rate limiting.

The maintenance log records only an exception type when cleanup fails. It must not print retained questions, answers, raw addresses, secrets, provider payloads, or contact values.

## Rate-limit state

Rate limiting does not require raw conversation text. It uses:

- `rate_events`: pseudonymous client key plus timestamp;
- `daily_usage`: UTC day plus aggregate request count.

Raw-chat cleanup never deletes these tables. Their lifecycle is governed by the rate-limit logic, not `CHAT_RETENTION_DAYS`.

## Telegram boundary

Telegram is a separate external system and is not controlled by SQLite retention.

By default `TELEGRAM_INCLUDE_CONTENT=false`, so notifications contain only the interaction marker and pseudonymous client key. If an operator explicitly enables `TELEGRAM_INCLUDE_CONTENT=true`, truncated question/answer content is sent to Telegram and Telegram's own retention/account policy applies independently. A short SQLite retention period does not delete a message already sent to Telegram.

## Backup and rollback boundary

The runtime SQLite database lives on the persistent `/app/data` volume. Application image rollback must reuse that volume rather than restore an older copy of `assistant.sqlite3`; otherwise expired rows could be resurrected. Deployment/rollback evidence must therefore continue to treat cvbot data as persistent runtime state, not as a versioned application artifact.
