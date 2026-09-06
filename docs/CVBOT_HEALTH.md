# CV assistant health contract

cvbot separates process liveness from application readiness.

## Liveness

`GET /health` and `GET /health/live` are cheap process checks. They return only `{"ok": true}` and do not touch SQLite or any external provider.

## Readiness

`GET /health/ready` verifies only local prerequisites required before cvbot may receive traffic:

- the configured LLM API key is present;
- the dedicated client pseudonymization secret is present;
- the selected model is the source-supported `gpt-5.6-luna` model;
- the SQLite database opens successfully;
- SQLite `quick_check(1)` reports healthy storage;
- SQLite can acquire a write transaction on the persistent database path.

The writeability probe creates a table only inside a transaction that is always rolled back, so a successful readiness request leaves no readiness table or application row behind.

Readiness never calls OpenAI, Telegram, Turnstile, Cloudflare, DNS, or another homelab service. An external-provider outage therefore does not make Docker restart an otherwise healthy cvbot process. Provider reachability is exercised by real chat traffic and release/public verification, not by the container health endpoint.

## Deployment and public surface

Docker health checks `http://localhost:5000/health/ready`. The release helper waits for Docker to report cvbot healthy before starting/reloading the Nginx frontend, so deployment cannot proceed to public acceptance while local cvbot storage/config prerequisites are failing.

The endpoint returns only `{"ready": true}` or the same boolean with HTTP 503. It never exposes which configuration value or storage check failed. The existing `/api/health` path remains a cheaper liveness signal.

No secret value, database content, file path, provider payload, or detailed failure reason is returned by either endpoint.
