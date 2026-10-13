# Live statistics pipeline

`stats.sh` is the stable cron entrypoint. It launches
`scripts/generate-stats.py`, which reads Prometheus and Docker counters and
publishes `/home/andris/docker/cv/html/stats.json`.

## Safety contract

- one non-blocking lock prevents overlapping refreshes;
- curl has bounded connect and total timeouts plus a fixed retry count;
- each PromQL expression aggregates to at most one series;
- empty results become `null` while malformed, multi-series, non-finite, or
  non-numeric results fail the refresh;
- Docker commands have a ten-second process timeout;
- the complete snapshot is validated against the committed field contract;
- JSON is written, fsynced, re-read, and validated in a temporary file on the
  destination filesystem before an atomic replacement;
- every failure leaves the previous valid `stats.json` untouched.

## Manual validation

Run without replacing production output:

```bash
cd /home/andris/rozkalns-cv
python3 scripts/generate-stats.py \
  --output /tmp/rozkalns-cv-stats.json \
  --lock /tmp/rozkalns-cv-stats.lock
python3 -m json.tool /tmp/rozkalns-cv-stats.json >/dev/null
```

The public browser cache policy for `stats.json` remains `no-store`. Frontend
stale/future timestamp behavior is maintained with the frontend application.

## SIMPLE-DEPLOY presentation boundary

The RPi5-owned Compose adapter (tracked by `rozkalnsandris/RPi5_main#997`)
reuses the existing host data-path interpolation to mount the **directory**
containing the generated `stats.json` read-only at `/srv/cv/host-stats`,
outside the image web root `/srv/cv/html`. The directory mount is deliberate:
a bind mount of one file would remain attached to an old inode after the
atomic `os.replace` used by `generate-stats.py`.

SIMPLE-DEPLOY Nginx exposes only the exact `/stats.json` file by `alias`
and sends `Cache-Control: no-store`. The rest of the host directory has no
public URL. If the mount/snapshot is absent, that URL returns 404 and the
frontend shows unavailable metrics rather than inventing numbers. The host
stats timer remains independently owned; this source change neither installs
nor changes it. The companion host-adapter source change must be reviewed and
merged separately, followed by an owner-authorized LIVE deploy before the
public metrics can resume.

When separately authorized to verify production, check both the exact
`/stats.json` response and freshness of its `updated` timestamp (frontend
marks snapshots older than 15 minutes stale); `/api/health/ready` returning
200 alone does not prove live metrics delivery.
