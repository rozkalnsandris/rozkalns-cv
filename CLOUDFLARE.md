# Putting Cloudflare in front of your CV (Tunnel method)

This hides your home IP, adds free SSL + CDN + DDoS protection, and needs **no
port-forwarding** and **no static IP**. The tunnel makes an *outbound* connection
from your Pi to Cloudflare, so nothing inbound is ever opened on your router.

## ⚠️ Prerequisite: your own domain

Cloudflare cannot proxy `*.duckdns.org` — you don't own `duckdns.org`, so it
can't sit on Cloudflare's nameservers. You need a domain you own, e.g.
`rozkalns.dev`, `andris.cloud`, `andris-devops.com` (~€8–12/year). Cheapest:
buy it directly at **Cloudflare Registrar** (at-cost pricing, auto-configured).

> Keep DuckDNS for your internal/other services — just use the new domain for
> the public CV.

## 1. Add the domain to Cloudflare (free plan)

1. Create a free Cloudflare account.
2. **Add a site** → enter your domain → choose the **Free** plan.
3. If you bought it at Cloudflare Registrar it's already wired. If bought
   elsewhere, change the nameservers at your registrar to the two Cloudflare
   gives you (propagates in minutes–hours).

## 2. Create the tunnel

1. Cloudflare dashboard → **Zero Trust** → **Networks** → **Tunnels**.
2. **Create a tunnel** → type **Cloudflared** → name it `rpi5-cv`.
3. On the install screen, copy the **token** (long `eyJ...` string).

## 3. Run the tunnel container on the Pi

```bash
cp ~/docker/cv/cloudflared.env.example ~/docker/cv/cloudflared.env
nano ~/docker/cv/cloudflared.env        # paste CF_TUNNEL_TOKEN
cd ~/docker/cv
docker compose --profile cloudflare up -d
docker logs cv-cloudflared --tail 20    # should show "Registered tunnel connection"
```

## 4. Point a hostname at the CV container

Back in the tunnel page → **Public Hostnames** → **Add a public hostname**:

- **Subdomain:** `cv`   **Domain:** `yourdomain.com`
- **Type:** `HTTP`
- **URL:** `cv:80`   ← the nginx container's name on the compose network

Save. Open `https://cv.yourdomain.com` — it loads over Cloudflare with SSL,
your home IP nowhere in sight.

## 5. (Recommended) lock the origin down

Since all traffic now comes through the tunnel, you can **close the old
port-forwards (80/443)** on your router that you used for DuckDNS+NPM — the CV
no longer needs them. NPM stays for your internal/other services.

---

## What you get

| | |
|---|---|
| 🔒 Home IP hidden from visitors & bots | ✅ |
| 🌍 Global CDN + caching (fast worldwide, smooths brief home outages) | ✅ |
| 🔐 Free automatic SSL | ✅ |
| 🛡️ DDoS protection | ✅ |
| 🚪 No inbound ports opened on your router | ✅ |
| 💶 Cost | domain only (~€10/yr) |

## Verifying your IP is hidden

```bash
# from any machine — should return a Cloudflare IP, NOT your home IP:
dig +short cv.yourdomain.com
```
