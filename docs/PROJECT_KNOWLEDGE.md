# rozkalns.net CV — consolidated project knowledge

## Current purpose

`rozkalns.net` is Andris Rožkalns' public, three-language EN/DE/LV
CV/portfolio. It is itself a portfolio proof: the page is served from Andris'
Raspberry Pi 5 homelab and displays live infrastructure metrics.

## Confirmed runtime architecture

- Host: Raspberry Pi 5, Debian 12, ARM64
- Runtime directory: `/home/andris/docker/cv`
- Static web service/container: `cv`, based on nginx Alpine
- CV assistant service/container: `cvbot`
- Tunnel service/container: `cv-cloudflared`
- Docker network: `cv_default`, pinned to `172.19.0.0/16` with gateway
  `172.19.0.1` in the primary `docker-compose.yml`
- Local web endpoint: `http://192.168.0.180:8088/`
- Public endpoint: `https://rozkalns.net/`
- Cloudflare ingress for the root domain points to `http://cv:80`
- nginx serves static files and proxies the assistant API to `cvbot:5000`
- Prometheus-derived live statistics are written into `stats.json`
- `/etc/cron.d/cv-stats` historically refreshes those statistics every 5 minutes

## Docker network ownership

The application repository owns the declarative Compose network identity:

- network name: `cv_default`
- subnet: `172.19.0.0/16`
- gateway: `172.19.0.1`

The network declaration must remain in the primary `docker-compose.yml` so CI,
deploy, rollback, and diagnostics all render the same configuration. The old
`docker-compose.network.yml` override is retired and must not return.

`RPi5_main` owns host-level consumers of this contract, including UFW rules and
other infrastructure documentation. A subnet change therefore requires a
separate, coordinated infrastructure change before this application value is
changed.

## Confirmed website content/features

- English, German, and Latvian interface/content
- Responsive CV/portfolio page
- Profile image and Open Graph image metadata
- Downloadable PDF CV
- Experience, projects, skills, education, language and availability sections
- Live homelab metrics
- Embedded CV assistant
- Cloudflare Web Analytics
- `robots.txt` intentionally blocks `/photo.jpg` while allowing the rest of the site

## Historical deployment

The older `/home/andris/update.sh` was not an operating-system update script.
It was a monolithic CV generator/deployer that rewrote:

- `index.html`
- `nginx.conf`
- `docker-compose.yml`
- `bot/app.py`
- `stats.sh`

That model previously suffered from a broken heredoc and mixed source
generation with production deployment. GitHub now becomes the source of truth;
the monolithic generator must not overwrite Git-managed production files after
migration.

## Secret risk discovered in history

A Cloudflare tunnel token was historically stored both in
`~/docker/cv/cloudflared.env` and directly inside `docker-compose.yml`.
The exporter removes real env files and rejects a staged repository if a
token-like value remains. The repository contains only placeholders.

Because old chat/export material may have exposed credentials, verify that the
current tunnel token has been rotated. Never copy raw Claude/Gemini exports into
the repository.

## Deployment boundary

The `cv-cloudflared` container is part of a shared Cloudflare tunnel that also
routes other `rozkalns.net` subdomains. A routine CV code change must therefore
deploy only `cv` and `cvbot`. Tunnel changes require a separate, explicit
infrastructure change and wider health checks.

## GitHub operating model

- Private repository: `rozkalnsandris/rozkalns-cv`
- Branch workflow: issue/branch -> Draft PR -> CI -> review -> squash merge
- `main` is deployable source of truth
- Every successful push CI on `main` queues a serial production deployment
- Dedicated runner label: `rozkalns-cv-release`
- Root deployment helper: `/usr/local/sbin/rozkalns-cv-deploy-main`
- Rollback and evidence are mandatory

## Research provenance

See `docs/RESEARCH_PROVENANCE.md`. The initial Git source must come from the
current RPi5 runtime directory; histories are supporting evidence only.
