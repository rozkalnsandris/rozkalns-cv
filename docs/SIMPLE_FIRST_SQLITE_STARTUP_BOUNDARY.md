# SIMPLE-FIRST public CV SQLite startup boundary

The public SIMPLE-DEPLOY image now starts "chat_entry:create_public_app()"
through "deploy/simple-deploy/supervise.py". The regular Assistant entrypoint
"chat_entry:create_app()" stays unchanged for all non-public runtimes.

## Passive requests (no SQLite mutation)

- Cold public startup does not create or open the Assistant SQLite file, enable
  WAL, initialize Assistant chat/rate tables, purge chat content or start the
  retention janitor. Existing chat content must survive all public restarts.
- GET /health, /health/live, /health/ready and /contact-config have no storage
  access. Public readiness describes the contact-only process health, not
  LLM readiness or SQLite write availability.
- No Assistant chat/config/admission routes are registered on the public
  application, in addition to the image's Nginx 404 rules.

## Contact attempt boundary

- A real, validated POST /contact-reveal invokes the existing Turnstile
  verification and pseudonymous per-client/global quota checks. Only this
  explicit request can lazily create the quota's verification_events table
  and indexes in the existing SQLite location, prune expired verification
  attempt records, and insert one attempt.
- Invalid requests never open SQLite. On quota/storage failure the endpoint
  returns 503 (fail-closed), not a verification bypass.
- Quota state is durable across requests and restarts. No chat table creation,
  chat-content DELETE or automatic Assistant retention is performed by the
  public-only application. Full Assistant behavior remains unchanged.
- The request-triggered quota writes are separate from startup but are still
  application-data mutations requiring a separate owner decision before
  LIVE rollout, in accordance with the RPi5 target's forbidden-operation
  registry. This source issue does not authorize those LIVE writes.

Official SQLite WAL semantics: https://www.sqlite.org/wal.html
