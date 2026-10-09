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

## Public contact / DB-free boundary

- Public SIMPLE-FIRST app creation does not instantiate AssistantStore.
  No database is opened on startup, passive GET or any POST /contact-reveal,
  including successful Turnstile verification or Siteverify errors.
- Contact disclosure still requires a bounded token, server-side Turnstile
  Siteverify (single-use, five-minute tokens), an allowed action and hostname.
  Invalid tokens and upstream errors fail closed without returning phone data.
- The combined-image Nginx ingress has a dedicated exact-match
  /api/contact-reveal route. Its shared-memory request limit zones use
  normalized client address (6 requests/minute, burst 3) and a global
  server cap (60 requests/minute, burst 15). Nginx returns 429 over quota.
  Both zones are in memory, across workers; restart resets these quotas.
- Source trusts CF-Connecting-IP only from 172.19.0.1/32 (reviewed source
  bridge gateway). The entire Docker subnet is NOT trusted. The actual
  source address seen by this combined-image Nginx and the upstream's
  sanitization of CF-Connecting-IP MUST be independently confirmed with
  scoped read-only RPi5/edge evidence before any deployment. If the RPi5
  Docker gateway differs or an upstream forwards arbitrary user-controlled
  CF-Connecting-IP, the LIVE contract is BLOCKED, not silently adjusted.
  Fallback to the TCP peer may aggregate all users into one rate bucket.
- The request guard is deliberately at Nginx, not the Flask route. Gunicorn
  remains bound to container loopback 127.0.0.1:5000. Exposing Gunicorn
  directly would bypass this guard and requires a separate security review.
- The full (non-public) Assistant factory retains SQLite-backed chat and
  verification quotas unchanged; no migration/deletion of existing durable
  chat data is authorized by this source change.
- Existing RPi5 target/Compose binds preserved /app/data. This PR does NOT
  remove it or delete data; that requires independent LIVE scope.

Official references:
- https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
- https://nginx.org/en/docs/http/ngx_http_realip_module.html
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
