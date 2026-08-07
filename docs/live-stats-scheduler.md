# Live homelab statistics scheduler

Production Nginx serves `/home/andris/docker/cv/html/stats.json`. The deploy
helper preserves that file across application deploys because it is live host
state, not a build artifact.

The canonical refresh scheduler is the host systemd timer:

- `rozkalns-cv-stats.timer` — fires once per minute;
- `rozkalns-cv-stats.service` — runs the GitHub-managed production runtime
  `/home/andris/docker/cv/stats.sh` as user `andris`;
- the generator writes atomically and keeps the previous valid JSON if refresh
  generation fails;
- the timer is independent from application containers, so a normal CV deploy
  does not need systemd privileges.

## One-time production install

After this change has deployed to the RPi5 runtime, install or reconcile the
host timer with:

```bash
sudo bash /home/andris/docker/cv/scripts/install-live-stats-systemd.sh
```

The installer is idempotent. It installs the two committed units, removes only
legacy CV stats entries from Andris's crontab, enables the timer, executes an
immediate refresh, and fails if the resulting `stats.json` is not fresh.

## Verification

```bash
systemctl status rozkalns-cv-stats.timer --no-pager
systemctl status rozkalns-cv-stats.service --no-pager
journalctl -u rozkalns-cv-stats.service -n 50 --no-pager
cat /home/andris/docker/cv/html/stats.json
```

The timer should stay `active (waiting)` and the `updated` timestamp in
`stats.json` should advance every minute.
