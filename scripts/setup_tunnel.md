# Setting Up a Permanent Public URL

## Option A — Quick Tunnel (no account, URL changes each run)

This is the fastest way to get a public URL right now:

```bash
cloudflared tunnel --url http://localhost:3000
```

A URL like `https://random-words.trycloudflare.com` will be printed.
Open it anywhere. It works until you stop the process.

---

## Option B — Named Tunnel (permanent URL, free Cloudflare account)

This gives you a fixed URL like `https://llresearch.yourdomain.com` that
never changes, even across restarts.

### Prerequisites
- A free Cloudflare account: https://dash.cloudflare.com/sign-up
- A domain managed by Cloudflare (can be any domain, even a free one)

### One-time setup

**1. Authenticate cloudflared with your Cloudflare account:**
```bash
cloudflared tunnel login
# Opens a browser window — select your domain and authorize
```

**2. Create a named tunnel:**
```bash
cloudflared tunnel create llresearch
# Saves credentials to ~/.cloudflared/<tunnel-id>.json
```

**3. Create a DNS record pointing to the tunnel:**
```bash
cloudflared tunnel route dns llresearch llresearch.yourdomain.com
```

**4. Create a config file at `~/.cloudflared/config.yml`:**
```yaml
tunnel: llresearch
credentials-file: /home/<your-user>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: llresearch.yourdomain.com
    service: http://localhost:3000
  - service: http_status:404
```

**5. Run the tunnel:**
```bash
cloudflared tunnel run llresearch
```

Your UI is now accessible at `https://llresearch.yourdomain.com` from anywhere.

### Starting everything at once

With a named tunnel configured, edit `scripts/start_all.sh` and replace
the `cloudflared tunnel --url` line with:
```bash
cloudflared tunnel run llresearch &
```

---

## Option C — Run on same network (no tunnel needed)

If you only need access from your phone/laptop on the same WiFi:

1. Find your machine's local IP: `ip addr show | grep 'inet '`
2. Visit `http://<your-local-ip>:3000` on any device on the network
3. Make sure your firewall allows port 3000

---

## Security note

The quick tunnel and named tunnel both use HTTPS (Cloudflare handles the cert).
The FastAPI backend stays on localhost — only the Next.js port is exposed.
