<p align="center">
  <img src="assets/branding/project-logo.svg" alt="rozkalns.net CV project logo" width="128" height="128">
</p>

<h1 align="center">rozkalns.net CV</h1>

<p align="center">
  <strong>A source-controlled multilingual CV and portfolio, built deterministically and deployed to a self-hosted Raspberry Pi 5.</strong>
</p>

<p align="center">
  <a href="https://rozkalns.net/">Live site</a>
  ·
  <a href="content/profile.json">Canonical CV data</a>
  ·
  <a href="frontend/">Frontend source</a>
  ·
  <a href="https://github.com/rozkalnsandris/rozkalns-cv/actions">Actions</a>
</p>

<p align="center">
  <a href="https://github.com/rozkalnsandris/rozkalns-cv/actions/workflows/ci.yml">
    <img src="https://github.com/rozkalnsandris/rozkalns-cv/actions/workflows/ci.yml/badge.svg?branch=main" alt="rozkalns.net CV CI status">
  </a>
</p>

This repository is the source of truth for Andris Rožkalns' public CV and
portfolio at `https://rozkalns.net/`. Human-readable profile data, translations,
frontend source, deterministic build output and the CV assistant are reviewed
and versioned together before deployment.

| | |
|---|---|
| **Frontend** | Vite-built static site · multilingual EN / DE / LV |
| **CV data** | `content/profile.json` · versioned translations |
| **Assistant** | Python CV assistant behind Nginx |
| **Runtime** | Docker Compose · Raspberry Pi 5 · shared Cloudflare Tunnel |

## Architecture

- Human-readable frontend source in `frontend/`
- Deterministic Vite build output committed under `html/` for nginx deployment
- Canonical CV data in `content/profile.json` and `content/translations/*.json`
- Static multilingual EN/DE/LV site served by nginx
- Python CV assistant behind nginx
- Live Prometheus-derived metrics
- Docker Compose runtime on Raspberry Pi 5
- Public ingress through the shared RPi5 Cloudflare Tunnel

Vite is build-only tooling. Production does not run a Vite development server
and the RPi5 deployment does not install frontend dependencies. CI uses the
pinned npm lockfile, regenerates the frontend twice, verifies byte-identical
output plus `frontend-dist-manifest.json`, and rejects stale committed `html/`
artifacts. Content-hashed assets are generated automatically; the app module's
`?cfg=<nginx-sha>` representation key is also generated automatically so an
nginx MIME/security-header configuration change invalidates its immutable URL.

Local frontend verification:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build:frontend
npm run check:frontend
```

The shared Cloudflare Tunnel connector is host-wide infrastructure owned by
`RPi5_main` and runs as the RPi5 systemd `cloudflared.service`. This repository
does not own its token, container/image, lifecycle, readiness, canaries,
reconciliation or rollback.

**Permanent boundary:** CV Compose and CV deployment/rollback code must never
reintroduce an application-owned `cloudflared` service, shared Tunnel credential,
connector restart/reconciliation, connector canary, or connector rollback. CV
may verify `https://rozkalns.net/`, but shared ingress health and lifecycle are
host-infrastructure responsibilities.

## Production

- Checkout: `/home/andris/rozkalns-cv`
- Runtime: `/home/andris/docker/cv`
- Host ingress origin: `http://127.0.0.1:8088/`
- Direct LAN publish: none
- Public: `https://rozkalns.net/`

GitHub Actions in this repository supplies CI evidence; it does not execute the
RPi5 production deployment. The recurring RPi5-owned
`rozkalns-cv-pull-deploy.timer`, whose source and lifecycle are managed in
`RPi5_main`, runs a serial least-privilege pull controller. The controller
independently resolves current `origin/main`, requires successful exact-SHA CI
and classifies the complete production-to-target range. Only an
`AUTO_DEPLOY_SAFE` range with no control-plane change may invoke the
transactional pull deploy helper; manual, database, host and control-plane
outcomes remain non-automatic and fail closed. The release helper deploys only
`cv` and `cvbot`, checks local and public application health, and automatically
rolls back CV application failures.

Real CV application secrets are stored only on the RPi5. Shared Cloudflare
credentials are outside the CV application ownership boundary.
