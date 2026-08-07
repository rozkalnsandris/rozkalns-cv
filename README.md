<p align="center">
  <img src="assets/branding/readme-banner.jpg" alt="rozkalns.net CV project banner" width="960">
</p>

# rozkalns.net CV

Source of truth for Andris Rožkalns' public CV/portfolio at
`https://rozkalns.net/`.

## Architecture

- Static multilingual EN/DE/LV site served by nginx
- Python CV assistant behind nginx
- Live Prometheus-derived metrics
- Docker Compose runtime on Raspberry Pi 5
- Public ingress through the shared RPi5 Cloudflare Tunnel

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
- Local: `http://192.168.0.180:8088/`
- Host ingress origin: `http://127.0.0.1:8088/`
- Public: `https://rozkalns.net/`

Every successful `main` CI run queues a serial deployment on a dedicated,
least-privilege RPi5 runner. The release helper deploys only `cv` and `cvbot`,
checks local and public application health, and automatically rolls back CV
application failures.

Real CV application secrets are stored only on the RPi5. Shared Cloudflare
credentials are outside the CV application ownership boundary.
