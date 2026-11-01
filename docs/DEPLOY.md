# Deployment Guide

Two services: FastAPI API on **Fly.io**, React web app on **Cloudflare Pages**.

---

## 1. Generate a secret key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# e.g. Xk9mP2qR8vL3nT6wY1sA0bC5dE7fG4h
```

This is the **access key**. It lives only on the API (as a Fly secret) and in the head of whoever is allowed to use live data. It is typed into the web app's "Unlock" box and is **never** put in a build variable: anything in a Vite bundle is readable by every visitor.

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

Do **not** add `VITE_API_SECRET_KEY`. Visitors without the access key see the pre-computed demo data; the owner clicks **Unlock** and types the key to see live data.

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

(Remove `VITE_API_SECRET_KEY` from the repository secrets if it exists.)

After this, every push to `main` auto-deploys both services.

---

## Local dev (no auth)

Leave `API_SECRET_KEY` empty in `.env`. Auth is disabled when the variable is unset.

```bash
uv run uvicorn src.api.server:app --port 8000   # API
cd web && npm run dev                            # http://localhost:5173
```

---

## Security notes

- **Rotate the key if it ever shipped in a bundle.** Earlier deployments built `VITE_API_SECRET_KEY` into the public JavaScript, so that value is public. Generate a new one and set it only on Fly:

  ```bash
  fly secrets set API_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  ```

  Then redeploy the web app so the old key is no longer in the bundle, and delete the old GitHub and Cloudflare variable.
- **Production fails closed.** `fly.toml` sets `APP_ENV=production`; if `API_SECRET_KEY` is missing the API answers 503 instead of running open.
- **Key guessing is blocked.** Ten wrong keys from one address within a minute lock that address out for a minute. The address comes from the `Fly-Client-IP` header that Fly sets.
- **AI spend is capped.** Endpoints that call Claude share a daily budget (`AI_DAILY_LIMIT`, default 100 per UTC day, `0` turns them off). Also set a monthly spend limit in the Anthropic console; code limits do not replace it.
- **The Linear watcher only starts when `WATCH_LABEL` is set** (`fly.toml` sets it to `support-buddy`), and then briefs only issues carrying that label. `WATCH_TEAM` narrows it further. It still has read access to the whole workspace through `LINEAR_API_KEY`, so use a sandbox workspace only.
