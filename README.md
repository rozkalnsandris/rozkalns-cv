<p align="center">
  <img src="assets/branding/readme-banner.jpg" alt="rozkalns.net CV project banner" width="960">
</p>

# rozkalns.net CV

Source of truth for Andris Rožkalns' public CV/portfolio at
`https://rozkalns.net/`.

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

Every successful `main` CI run queues a serial deployment on a dedicated,
least-privilege RPi5 runner. The release helper deploys only `cv` and `cvbot`,
checks local and public application health, and automatically rolls back CV
application failures.

Real CV application secrets are stored only on the RPi5. Shared Cloudflare
credentials are outside the CV application ownership boundary.
