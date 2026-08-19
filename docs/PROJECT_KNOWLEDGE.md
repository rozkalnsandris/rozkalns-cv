# rozkalns.net CV — consolidated project knowledge

## Current purpose

`rozkalns.net` is Andris Rožkalns' public, three-language EN/DE/LV
CV/portfolio. It is itself a portfolio proof: the page is served from the
Raspberry Pi 5 homelab and displays live infrastructure metrics.

## Current runtime architecture

- Deployment target: Raspberry Pi 5, ARM64
- Source checkout: `/home/andris/rozkalns-cv`
- Runtime directory: `/home/andris/docker/cv`
- Application services: `cv` (nginx) and `cvbot` (Python assistant)
- Docker network: `cv_default`, pinned to `172.19.0.0/16` with gateway
  `172.19.0.1` in the primary `docker-compose.yml`
- Host-only application origin: `http://127.0.0.1:8088/`
- Direct LAN publish: none
- Public endpoint: `https://rozkalns.net/`
- nginx serves static files and proxies the assistant API to `cvbot:5000`
- Prometheus-derived live statistics are written into `stats.json`

The shared Cloudflare Tunnel connector is **not** a CV Compose service. It is
host-wide infrastructure owned by `RPi5_main` and runs as the RPi5 systemd
`cloudflared.service`. This repository does not own the shared connector token,
image, lifecycle, readiness, reconciliation, canaries or rollback.

## Docker network ownership

The application repository owns the declarative Compose network identity:

- network name: `cv_default`
- subnet: `172.19.0.0/16`
- gateway: `172.19.0.1`

The network declaration must remain in the primary `docker-compose.yml` so CI,
deploy, rollback, and diagnostics render the same configuration. The old
`docker-compose.network.yml` override is retired and must not return.

`RPi5_main` owns host-level consumers of this contract, including UFW rules and
other infrastructure documentation. A subnet change therefore requires a
separate, coordinated infrastructure change before the application value is
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

## Source and deployment ownership

The public GitHub repository `rozkalnsandris/rozkalns-cv` is the source of
truth for CV application source, content, deterministic frontend output,
application Compose configuration and the transactional CV release helper.

GitHub Actions provides CI/security evidence only; it does **not** execute the
RPi5 production deployment. The recurring RPi5-owned
`rozkalns-cv-pull-deploy.timer`, whose source and lifecycle belong to
`RPi5_main`, runs a serial least-privilege pull controller. The controller:

1. independently resolves current `origin/main`;
2. requires successful exact-SHA CI for that target;
3. classifies the complete production-to-target range; and
4. fails closed unless the result permits the requested path.

Only an `AUTO_DEPLOY_SAFE` range with no control-plane change may invoke the
transactional pull deploy helper automatically. Manual, database, host and
control-plane outcomes remain non-automatic. The release helper deploys only
`cv` and `cvbot`, checks local and public application health, and automatically
rolls back CV application failures.

The former repository-scoped self-hosted GitHub Actions release runner was a
migration-era transport and has been retired. It must not be treated as the
current deployment path.

## Historical deployment

The older `/home/andris/update.sh` was a monolithic CV generator/deployer that
rewrote application source and configuration. That model mixed source
generation with production deployment and is retired. Git-managed production
files must not be overwritten by recreating that workflow.

The initial migration also temporarily used an application-owned Cloudflare
container and a dedicated self-hosted GitHub release runner. Both are historical
architecture. `docs/MIGRATION_RUNBOOK.md` is retained only as an archived
migration record, while `MIGRATION_INVENTORY.txt` is immutable historical
evidence and may name components that no longer exist.

## Secrets and trust boundaries

Real CV application secrets are stored only on the RPi5 and are never committed.
Shared Cloudflare credentials are host-infrastructure secrets outside the CV
application ownership boundary.

A routine CV change must never restart, reconfigure or take ownership of the
shared Cloudflare connector. CV deployment may verify the public
`https://rozkalns.net/` application path, but shared ingress lifecycle and
health belong to `RPi5_main`.

## GitHub operating model

- Repository: public `rozkalnsandris/rozkalns-cv`
- Branch workflow: issue/branch -> Draft PR -> CI/security evidence -> Ready -> explicit squash merge
- `main` is the deployable source of truth
- production state is reconciled separately from source state
- exact-SHA CI and production-to-target range classification are mandatory
- rollback and evidence are mandatory for application deployment

## Research provenance

See `docs/RESEARCH_PROVENANCE.md`. Historical exports and inventories are
supporting evidence; they are not current operational instructions.
