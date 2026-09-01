# Build and deploy runbook

This is the canonical quick path for rebuilding committed frontend output and preparing a production rollout. It does not grant merge or live-production authority.

## Frontend build: exact reproducible path

Repository source and generated frontend output are versioned together. Vite is build-only tooling; production does not install frontend dependencies.

Current CI build toolchain:

- Node.js: `24.18.0`
- npm: `11.16.0` with the current CI Node distribution
- Vite: pinned by `package-lock.json` (`8.2.2` at the time this runbook was added)

Start from the exact PR/head that is being validated and require a clean worktree before building:

```sh
git status --short
git rev-parse HEAD
node --version
npm --version
```

Install and build with the CI-compatible commands:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build:frontend
npm run build:frontend
npm run check:frontend
```

The build is intentionally run twice. Both runs must succeed and the committed-output contract must pass. `npm run check:frontend` must end with `FRONTEND_DIST_CONTRACT=PASS` and `CHAT_PRIVACY_RUNTIME_CONTRACT=PASS`.

Before committing generated output:

```sh
git status --short
git diff --check
```

Expected generated-output scope is `frontend-dist-manifest.json` plus files below `html/`, including localized pages and content-hashed assets. Do not hand-edit generated files or guess asset fingerprints.

Stage generated output with deletions/renames included:

```sh
git add -A -- \
  frontend-dist-manifest.json \
  html/assets \
  html/en/index.html \
  html/de/index.html \
  html/lv/index.html \
  html/index.html \
  html/smarthome.html

git diff --cached --check
git status --short
```

Commit and push to the existing PR branch only after the diff is limited to intended generated output:

```sh
git commit -m "build: refresh generated frontend dist"
git push origin HEAD
```

After push, use GitHub as the source of truth: re-read the PR exact head SHA, exact-head CI, reviews and relevant comments. Do not rely on an earlier local SHA or earlier CI run.

## Local Node installation pattern

A user-local Node tarball is sufficient; a system-wide Node mutation is not required. One safe pattern is to unpack the exact Linux archive beneath a user-owned directory and prepend its `bin` directory to `PATH` for only the current shell. Verify `node --version`, `npm --version`, `which node` and `which npm` before the build.

Do not upgrade npm during a release build just because npm prints an update notice.

## Production architecture and target

Canonical production facts from this repository:

- Production checkout: `/home/andris/rozkalns-cv`
- Runtime directory: `/home/andris/docker/cv`
- Host ingress origin: `http://127.0.0.1:8088/`
- Public endpoint: `https://rozkalns.net/`
- Direct LAN publish: none
- Runtime: Docker Compose on Raspberry Pi 5
- Shared Cloudflare Tunnel is host-wide infrastructure owned outside this repository's application deployment boundary.

GitHub Actions supplies CI evidence and does not itself deploy production.

The recurring RPi5-owned `rozkalns-cv-pull-deploy.timer` is the normal production delivery controller. Its source and lifecycle are managed in `RPi5_main`, not in this repository. The controller independently resolves current `origin/main`, requires successful exact-SHA CI and classifies the complete production-to-target range. Only an `AUTO_DEPLOY_SAFE` range with no control-plane change may invoke the transactional pull-deploy helper. Manual, database, host and control-plane outcomes fail closed.

The release helper deploys only the CV application components (`cv` and `cvbot`), verifies local and public application health, and owns application rollback behavior. This repository must not restart, reconcile or roll back the shared Cloudflare Tunnel.

## Gate order

1. Source/PR work and deterministic generated output.
2. Exact-head CI and review evidence.
3. Explicit owner `MERGE` authorization before merging to `main`.
4. Fresh post-merge exact-SHA evidence and rollout classification.
5. Separate explicit `LIVE` / Composite Live authorization before any production host/runtime/deploy mutation that is not already an independently authorized automatic controller action.

Merge authorization never implies production-deploy authorization. Read-only production/preflight evidence is not a live mutation.

## Failure handling

After an authorized mutation starts, any tool error, timeout, unexpected state, head drift or authorization uncertainty requires fail-closed handling: gather only the necessary read-only evidence and stop. Do not retry, roll back, clean up or switch mutation paths without new explicit authorization unless that behavior was explicitly pre-authorized by the governing rollout contract.
