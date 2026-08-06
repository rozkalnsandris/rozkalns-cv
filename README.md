# rozkalns.net CV

Source of truth for Andris Rožkalns' public CV/portfolio at
`https://rozkalns.net/`.

## Architecture

- Static multilingual EN/DE/LV site served by nginx
- Python CV assistant behind nginx
- Live Prometheus-derived metrics
- Docker Compose runtime on Raspberry Pi 5
- Cloudflare Tunnel for public access

## Production

- Checkout: `/home/andris/rozkalns-cv`
- Runtime: `/home/andris/docker/cv`
- Local: `http://192.168.0.180:8088/`
- Public: `https://rozkalns.net/`

Every successful `main` CI run queues a serial deployment on a dedicated,
least-privilege RPi5 runner. The release helper deploys only `cv` and `cvbot`,
checks local and public health, and automatically rolls back failures.

Real secrets are stored only on the RPi5. `cv-cloudflared` is not restarted by
normal CV deployments because it serves a shared tunnel.
