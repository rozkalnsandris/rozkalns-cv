# rozkalns.net CV — consolidated project knowledge

## Purpose and evidence

`rozkalns.net` is a public EN/DE/LV CV and portfolio from a Raspberry Pi 5
homelab. The public repository `rozkalnsandris/rozkalns-cv` is authoritative
for application source; `content/profile.json` governs CV facts.

This file documents reviewed **source and ownership contracts**, not live
installation facts. Dated RPi5 observations (installed revision/digest,
health, timer state and known provenance limits) are in
[canonical handoff #347](https://github.com/rozkalnsandris/rozkalns-cv/issues/347).
A successful workflow or promoted image does not prove host deployment.

## SIMPLE-DEPLOY source architecture

- `.simple-deploy.json` and `Dockerfile.simple-deploy` define a
  `linux/arm64` combined Nginx + Python image published to
  `ghcr.io/rozkalnsandris/rozkalns-cv`. The immutable digest identifies
  a candidate; the mutable `production` tag is for discovery only.
- Single-image runtime: one Compose service `cv`, declared in
  `deploy/simple-deploy/docker-compose.yml`, with UID/GID `10001:10001`,
  read-only root filesystem, limited tmpfs and preserved application
  data bind mount at `/app/data`.
- `deploy/simple-deploy/supervise.py` starts Nginx on port `8080` and
  Gunicorn on container-loopback `127.0.0.1:5000` using
  `chat_entry:create_public_app()`. Nginx serves generated `html/`
  and proxies contact and health APIs over the loopback boundary.
- Declared host-only origin: `127.0.0.1:8088:8080` (no direct LAN
  publish). Public HTTPS ingress at `https://rozkalns.net/` depends on
  the shared, `RPi5_main`-owned Cloudflare Tunnel.
- The public CV Assistant is deferred: `/api/chat`, `/api/chat-config`
  and `/api/chat-admission` return 404. Public contact verification and
  health APIs remain available; passive public startup and health reads
  must not open or mutate the Assistant SQLite database.
- `cv_default` subnet `172.19.0.0/16` and gateway `172.19.0.1` are
  declared in source Compose, **not verified live network facts**.
  Host network topology and ingress provenance require direct evidence.

The root `docker-compose.yml` and `nginx.conf` retain a **legacy,
separate two-container** `cv` + `cvbot` lane. Do not treat this older
Compose model as installed SIMPLE-DEPLOY runtime or execute its
two-container release/rollback procedure against the combined image.
Host/network changes require separately scoped approval and coordination
with `RPi5_main`.

## Public site and authored frontend

UI v2 includes EN/DE/LV CV/PDF, evidence-led engineering projects,
localized Linux Operations Lab, skills, experience, education,
protected phone/WhatsApp contact, Cloudflare Web Analytics and
Prometheus-derived public `stats.json`. The public CV Assistant is
**paused**, not an active embedded chat feature.

Edit `frontend/` and canonical `content/`; Vite builds committed
`html/` and `frontend-dist-manifest.json`. See
[FRONTEND.md](FRONTEND.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
Data and metrics must not be invented for presentation.

## Delivery and runtime ownership

- Reviewed source in `main` follows focused PR, exact-head CI/security,
  review and explicit owner squash merge. GitHub Actions provides
  build/security and GHCR image publication evidence.
- The `SIMPLE-DEPLOY CV` GitHub Actions workflow builds, publishes and
  promotes the image on qualifying main pushes. It **does not**
  itself install it on the RPi5 or authorize LIVE mutation.
- Production installation requires a separate owner-gated LIVE operation:
  pin the verified image/source revision, inspect baseline/drift,
  deploy through the approved SIMPLE-DEPLOY procedure and verify
  local health and public EN/DE/LV routes.
- The `rozkalns-simple-deployer.timer` state is a **dated observation**
  in #347, not a guarantee of current scheduling. Production update
  initiator and Cloudflare route provenance remain unproven there.

The RPi5-owned `rozkalns-cv-pull-deploy.timer` and `AUTO_DEPLOY_SAFE`
classifier describe the older **legacy pull-deploy lane**, not proof that
it is currently active. The retired GitHub self-hosted release runner,
the historical `/home/andris/update.sh` and the legacy two-container
rollback path must not be reactivated for SIMPLE-DEPLOY.

## Shared host / privacy boundary

The Tunnel connector is host-wide `RPi5_main` infrastructure running as
the `cloudflared.service` systemd unit, not CV application Compose.
Neither CV source work nor an application rollout authorizes modifying
that service, Cloudflare/DNS, credentials, secrets, permissions,
application data or production DB state.

Do not publish private addresses, protected phone data, secrets,
account details, private job-search context or invented personal facts
to public GitHub. Protected contact uses verified Turnstile disclosure;
sensitive runtime configuration stays off GitHub.

## GitHub workflow and provenance

FAST-LANE: branch -> Draft PR -> exact-head CI/reviews -> Ready ->
explicit MERGE. Merge never authorizes LIVE. Fail closed after any
authorized mutation error; no implicit retry, rollback or cleanup.
See [handoff #347](https://github.com/rozkalnsandris/rozkalns-cv/issues/347),
[research provenance](RESEARCH_PROVENANCE.md) and the historical
[migration runbook](MIGRATION_RUNBOOK.md).

