# SIMPLE-DEPLOY source adaptation

This document describes the source-only SIMPLE-DEPLOY v1 candidate for the CV application.
It does not authorize or perform a production cutover.

## Purpose

The current production release is a two-container application: nginx serves the committed
frontend and proxies `/api/` to the `cvbot` container. SIMPLE-DEPLOY v1 publishes one
immutable image and deploys one Compose service. The candidate image therefore packages
both application components into one non-root runtime image rather than deploying only
half of the application.

The existing production `docker-compose.yml`, pull-deploy controller and rollback path
remain unchanged until a separately reviewed and authorized runtime cutover.

## Source contract

- Manifest: `.simple-deploy.json`
- Reusable workflow: `rozkalnsandris/ops-workflows/.github/workflows/simple-deploy.yml`
  pinned to exact commit `e05ed760791a127c7c9628696806ef39c9fe329c`
- Published image: `ghcr.io/rozkalnsandris/rozkalns-cv`
- Build file: `Dockerfile.simple-deploy`
- Target alias: `rozkalns-cv-rpi5`
- Compose service: `cv`
- Liveness: `/api/health`
- Readiness: `/api/health/ready`

The `production` image tag is discovery only; the shared workflow emits an immutable
image digest as the deployment identity.

## Runtime layout

The candidate image keeps the existing request semantics:

1. nginx listens on container port `8080`, serves `/srv/cv/html`, preserves the existing
   cache/security-header behavior and proxies `/api/` to loopback.
2. gunicorn serves the existing Flask application on `127.0.0.1:5000`.
3. A minimal Python PID 1 supervisor starts both processes and terminates the sibling if
   either process exits unexpectedly.
4. The container runs as UID/GID `10001:10001`.
5. `/app/data` remains writable application state and is not baked into the image.

Because nginx and gunicorn are now in the same container, the Flask application's trusted
proxy peer becomes `127.0.0.1`. Any future host-side runtime contract must therefore set
`TRUSTED_PROXY_CIDRS=127.0.0.1/32`. This is a reviewed configuration consequence of the
single-image topology, not a credential.

## Persistence and private configuration

The consumer manifest intentionally declares no Docker named volumes. Existing CV assistant
state is currently bind-mounted, so a future trusted host-side Compose contract can bind the
preserved CV data directory to `/app/data` without database or schema migration.

Private environment values remain outside Git. The source-side Compose example accepts an
external env file and overrides only the non-secret topology values required by the combined
runtime. No production secret is copied into the image or repository.

## Activation boundary

Merging this source would make the repository capable of building and publishing the
SIMPLE-DEPLOY image on `main`; it would not by itself add the CV target to the trusted RPi5
deployer.

A future production cutover requires a separate review and explicit authorization covering
at least:

- an `RPi5_main` target/Compose contract pinned to the accepted shared workflow revision;
- preservation and binding of the existing CV assistant data directory;
- private env continuity with the loopback trusted-proxy override;
- local liveness/readiness verification and public `https://rozkalns.net/` verification;
- rollback semantics for the old two-container release versus the new single-image release.

No Cloudflare lifecycle, production credentials, database/schema mutation, unrelated host
control or other trust-boundary expansion belongs to this source adaptation.
