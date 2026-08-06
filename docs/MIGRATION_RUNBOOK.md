# Migration runbook

## Phase 1 — create the sanitized repository from the current RPi5 source

Copy this whole kit to the RPi5, then run as `andris`:

```bash
cd ~/rozkalns-cv-migration-kit
bash scripts/export-current-rpi5.sh
```

The script:

1. reads `/home/andris/docker/cv`;
2. copies all current source and public assets;
3. excludes secrets, backups, logs, caches, runtime `stats.json`, and `.git`;
4. sanitizes any inline tunnel-token assignment;
5. overlays CI/CD, tests, documentation, and safe examples;
6. runs syntax, source-contract, and secret scans;
7. creates `/home/andris/rozkalns-cv`.

Review the generated inventory:

```bash
cat ~/rozkalns-cv/MIGRATION_INVENTORY.txt
```

## Phase 2 — create the private GitHub repository and push the baseline

From the generated repository:

```bash
cd ~/rozkalns-cv
bash scripts/bootstrap-github.sh
```

The script creates `rozkalnsandris/rozkalns-cv` as a private repository when it
does not already exist, creates the baseline commit, and pushes `main`.

The first commit is the exact current production source, sanitized for Git.

## Phase 3 — install and activate the dedicated RPi5 release runner

Use an isolated release-control worktree:

```bash
cd ~/rozkalns-cv
git fetch --prune origin main
mkdir -p ~/rozkalns-cv-worktrees
git worktree add --detach ~/rozkalns-cv-worktrees/release-control origin/main
cd ~/rozkalns-cv-worktrees/release-control
bash runner/activate-github-main-deploy.sh
```

Activation:

- creates the unprivileged `github-cv-runner` account;
- installs a dedicated GitHub Actions runner with label
  `rozkalns-cv-release`;
- does not add the account to the Docker group;
- installs the audited root deployment helper;
- creates the narrow sudoers rule.

## Phase 4 — verify the baseline

Wait for `CI` and `Deploy merged main to RPi5` to finish, then verify:

```bash
curl -fsS http://192.168.0.180:8088/ >/dev/null
curl -fsS https://rozkalns.net/ >/dev/null
docker inspect cv cvbot --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}'
```

The baseline should normally produce either:

- `PASS`, after safely recreating `cv` and `cvbot`; or
- `NO_OP_ALREADY_CURRENT`, when the state file already binds production to the
  same SHA.

## Phase 5 — retire the old source writer

After GitHub deployment is proven:

1. remove or disable any cron/systemd entry that invokes the old CV
   `/home/andris/update.sh`;
2. do not delete the script immediately—archive it outside the Git repository;
3. keep `/etc/cron.d/cv-stats` only if the live metrics still depend on it;
4. update the host-wide RPi5 documentation so `rozkalns-cv` owns CV source and
   deployment while `RPi5_main` owns host infrastructure.

## Normal development after migration

Use the same controlled pattern as the other projects:

```text
issue -> isolated branch/worktree -> Draft PR -> CI -> ready -> squash merge
      -> successful main CI -> serial RPi5 deployment -> evidence
```

Do not edit `/home/andris/docker/cv` directly after migration.

### Host-only Compose env files

The production Compose file references `bot/.env` and `cloudflared.env`. These
files remain only on the RPi5 and are never committed. Export/CI validation
creates short-lived placeholders because Docker Compose requires referenced
`env_file` paths to exist even when only validating configuration.
