# Deployment Guide

Two services: FastAPI API on **Fly.io**, React web app on **Cloudflare Pages**.

---

## 1. Generate a secret key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# e.g. Xk9mP2qR8vL3nT6wY1sA0bC5dE7fG4h
```

Keep this — you'll need it in both Fly.io and GitHub Actions secrets.

---

## 2. Deploy the API to Fly.io

### Install Fly CLI and log in

```bash
brew install flyctl
fly auth login
```

### Launch the app (first time only)

```bash
fly launch --name support-buddy-api --region nrt --no-deploy
```

This creates the app on Fly.io. Answer "yes" to use the existing `fly.toml`.

### Create a persistent volume for the database

```bash
fly volumes create support_buddy_data --size 1 --region nrt
```

### Set secrets

```bash
fly secrets set \
  API_SECRET_KEY="<your-key>" \
  ANTHROPIC_API_KEY="<your-anthropic-key>" \
  LINEAR_API_KEY="<your-linear-key>"
```

### Deploy

```bash
fly deploy
```

### Verify

```bash
curl https://support-buddy-api.fly.dev/api/v1/health
# → {"status":"ok","knowledge_docs":0}
```

---

## 3. Deploy the web app to Cloudflare Pages

### Create the Pages project (first time only)

1. Go to Cloudflare Dashboard → Workers & Pages → Create application → Pages
2. Connect your GitHub repo (`ella-yschoi/support-buddy`)
3. Framework preset: **None** (Vite)
4. Build command: `npm run build`
5. Build output directory: `dist`
6. Root directory: `web`

### Set environment variables in Cloudflare Pages

In Pages → Settings → Environment variables (Production):

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://support-buddy-api.fly.dev` |
| `VITE_API_SECRET_KEY` | `<your-key>` |

### Trigger a deploy

Push to `main` — GitHub Actions handles it automatically after setup below.

---

## 4. Set GitHub Actions secrets

In GitHub repo → Settings → Secrets and variables → Actions:

| Secret | Where to get it |
|---|---|
| `FLY_API_TOKEN` | `fly tokens create deploy` |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Dashboard → My Profile → API Tokens → Create Token (use "Edit Cloudflare Workers" template) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Dashboard → right sidebar |
| `VITE_API_URL` | `https://support-buddy-api.fly.dev` |

After this, every push to `main` auto-deploys both services.

---

## Local dev (no auth)

Leave `API_SECRET_KEY` empty in `.env`. Auth is disabled when the variable is unset.

```bash
uv run uvicorn src.api.server:app --port 8000   # API
cd web && npm run dev                            # http://localhost:5173
```
