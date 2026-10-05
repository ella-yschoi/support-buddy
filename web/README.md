# Support Buddy web

Static React app (Vite + TypeScript). It shows the Overnight Queue and briefing details.

## Run locally

```bash
cd web
npm install
npm run dev          # http://localhost:5173
```

With only this, the app shows the **pre-computed demo briefings** (`public/demo/briefings.json`)
and labels them "Demo data". No API key, no backend.

### With the live backend

In a second terminal, from the repo root:

```bash
uv run uvicorn src.api.server:app --port 8000
```

The dev server proxies `/api` to it, and the "Demo data" badge disappears. Create briefings with:

```bash
curl -X POST localhost:8000/api/v1/briefings -H 'content-type: application/json' \
  -d '{"inquiry": "How do I enable two-factor authentication?", "plan": "pro"}'
```

### Regenerate the demo data

```bash
uv run python -m src.cli demo-data      # writes web/public/demo/briefings.json
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm test` | Unit and component tests (Vitest, Testing Library) |
| `npm run typecheck` | TypeScript check |
| `npm run build` | Typecheck and production build into `dist/` |

Set `VITE_API_URL` at build time to point a deployed site at a remote backend.
