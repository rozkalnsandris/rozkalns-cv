# Migration runbook — archived

> **Status: completed historical record.** The initial repository migration and
> the former GitHub-hosted deployment transport described by earlier revisions
> are no longer an operator procedure. Do not reconstruct or execute that
> retired self-hosted-runner path. For the current production model, use the
> repository `README.md` and the RPi5-owned pull-controller documentation in
> `RPi5_main`.

## What this document records

The repository was originally created by exporting the then-current RPi5 CV
runtime into a sanitized Git source tree. The migration:

1. copied application source and public assets from the old runtime directory;
2. excluded secrets, backups, logs, caches and runtime-only data;
3. preserved a historical file/hash snapshot in `MIGRATION_INVENTORY.txt`;
4. established GitHub as the source of truth;
5. moved production changes away from the old monolithic source writer; and
6. initially used a dedicated self-hosted GitHub Actions release runner.

That final deployment transport was subsequently retired. References to the old
runner, old deployment workflow, old source writer, or old Cloudflare container
inside historical inventories/commits are evidence of the migration, not
current operational instructions.

## Current post-migration architecture

- `rozkalnsandris/rozkalns-cv` is the public source repository.
- The production checkout is `/home/andris/rozkalns-cv` and the runtime is
  `/home/andris/docker/cv`.
- CV Compose owns only the application services `cv` and `cvbot`.
- The application origin is published on host loopback at
  `http://127.0.0.1:8088/`; there is no direct LAN publish.
- Shared Cloudflare ingress is host-wide infrastructure owned by `RPi5_main`
  and runs through the RPi5 systemd `cloudflared.service`.
- GitHub Actions supplies CI/security evidence. It does **not** execute the RPi5
  production deployment.
- The RPi5-owned `rozkalns-cv-pull-deploy.timer` runs the serial least-privilege
  pull controller. The controller independently resolves `origin/main`,
  requires successful exact-SHA CI, and classifies the complete
  production-to-target range before any deployment decision.
- Only an `AUTO_DEPLOY_SAFE` range without a control-plane change may proceed
  automatically. Manual, database, host and control-plane outcomes stop and
  require the corresponding explicit owner-controlled path.
- The transactional release helper deploys only `cv` and `cvbot`, verifies
  local/public application health, and rolls back CV application failures.

## Normal development now

The source workflow remains:

```text
issue -> isolated branch/worktree -> Draft PR -> CI/security evidence
      -> ready -> explicit squash merge -> exact-main verification
```

A merge is not itself proof that production changed. Deployment state is
reconciled separately by the RPi5 pull controller and its exact-SHA evidence.
Do not edit `/home/andris/docker/cv` directly as a substitute for a reviewed
source change.

## Secrets and shared infrastructure

Real CV application secrets remain only on the RPi5, including `bot/.env`.
Shared Cloudflare credentials are outside this repository's ownership boundary
and must not be copied into CV source, CI fixtures, migration evidence, or
operator notes.

`MIGRATION_INVENTORY.txt` is intentionally immutable historical evidence. It
may list files and deployment components that no longer exist in the current
architecture; do not use that inventory as a current runbook.
