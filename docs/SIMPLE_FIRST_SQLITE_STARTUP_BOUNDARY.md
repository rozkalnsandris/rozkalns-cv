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
- The combined-image Nginx ingress has an exact-match /api/contact-reveal
  route and a global 60 requests/minute, burst 15 shared-memory backstop.
  Excess is 429. Restart resets the local bucket. It is NOT per-visitor-IP:
  a Docker host-to-container connection usually presents the bridge gateway.
- Observed RPi5 CV network on 2026-10-09: gateway 172.23.0.1/16.
  Previous 172.19.0.1/32 assumption was incorrect. Neither gateway IP
  authenticates CF-Connecting-IP, because direct host-loopback callers could
  submit the same header. Therefore Nginx has NO real_ip_header or
  set_real_ip_from rule, and strips CF-Connecting-IP and client-supplied
  X-Forwarded-For before forwarding to Gunicorn.
- The public Siteverify call omits the optional remoteip field rather than
  reporting Docker gateway as the visitor. Token, action and hostname checks
  remain required; the full Assistant code retains normal client IP handling.
- Real per-visitor-IP rate limiting belongs at the Cloudflare edge using
  a verified ruleset with the native ip.src characteristic; see
  RPi5_main docs/CV_CONTACT_EDGE_RATE_LIMIT_V1.md. The rule cannot be
  established by this CV image, and the Cloudflare plan/phase/counter
  capabilities and absence of route conflict MUST be verified before any
  owner-gated LIVE activation. Without edge activation, only the local
  shared global rate cap and Turnstile protect contact attempts.
- A Docker or host ingress allowing direct use of /api/contact-reveal bypasses
  edge per-client limiting, so production acceptance must independently
  verify loopback-only origin binding and route provenance.
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
