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
