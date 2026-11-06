# Health endpoint latency spike: investigation notes

Status: **cause not confirmed.** Nothing in the code has been changed because of this. Read the
"Verified" and "Hypotheses" sections separately; do not treat a hypothesis as a finding.

First observed: 2026-11-04 21:02 MST (2026-11-05 04:02 UTC), by an external synthetic check.

## Summary

An API check run from outside (Checkly, location N. Virginia) called `GET /api/v1/health` on the
deployed API once and waited **18.25 s** for a `200 OK`. Every other run before and after was
100-200 ms. The time was spent waiting for the first byte from the server, not on DNS, TCP or
download. The cause is not known. The code offers one plausible explanation (the health endpoint
lazily builds the knowledge engine on its first call), but that has not been tested.

## Verified (observed or read directly)

Observed in the monitoring tool:

- The slow run: N. Virginia, HTTP 200, total 18.25 s.
  - DNS 7 ms, TCP 88 ms, **first byte 18.15 s**, download 1 ms.
- Other runs of the same check from the same monitoring project:
  - N. Virginia: 109 ms, 116 ms, 105 ms.
  - Frankfurt: 203 ms, 192 ms (about twice as slow as Virginia; distance to the `sjc` region is
    a likely reason, not verified).
- Check settings: runs every 10 minutes from two locations, maximum response time 10 s. The slow run
  therefore also produced a "Max response time limit exceeded" error.
- A separate manual measurement from a development machine, about 13 minutes later: three requests
  at 0.16-0.20 s total.
- Of 7 runs in the window, 1 was slow. (Availability on the dashboard was 71.42 percent, but 1 of the
  2 failures in that window was a deliberately broken assertion used to test alert emails, so
  availability is not a measure of this problem.)

Read in this repository (line numbers may drift):

- `src/api/server.py`: `health()` calls `get_engine()` and returns `engine.doc_count()`.
  `get_engine()` creates the knowledge engine on the **first call** and runs
  `ingest_directory(KNOWLEDGE_DIR)`. If that fails, `health()` still answers `status: ok` with
  `knowledge_docs: 0` for an `HTTPException`.
- `src/core/knowledge/store.py`: uses a ChromaDB `PersistentClient` and the ONNX MiniLM embedding
  function.
- `fly.toml`: `auto_stop_machines = 'suspend'`, `auto_start_machines = true`,
  `min_machines_running = 1`, 1 shared CPU, 1 GB memory, primary region `sjc`. The data directory
  `/app/data/db` is a mounted volume (`BRIEFING_DB_PATH`, `CHROMA_PERSIST_DIR`).
- `start.sh`: runs the Linear watcher in the background and uvicorn in the foreground. Its comment
  says the watcher "safely resumes after machine suspend/restart".

## Hypotheses (not verified)

1. **Process restart, then lazy init.** The process restarted shortly before the slow run, so the
   first request had to build the engine and ingest the knowledge documents inside that request.
   Supported by: `health()` depends on `get_engine()`; one slow run followed by fast ones.
   Not supported or contradicted by: nothing yet, but no restart has been shown.
2. **Resume from suspend.** The machine was suspended and took a long time to resume.
   Open question: whether `min_machines_running = 1` is meant to prevent suspension here. This was
   not checked against Fly's documentation.
3. **Transient network or proxy delay** between the monitoring location and Fly.

Unknown: how long engine initialization takes on this machine; whether the machine restarted or
resumed at about that time.

## How to tell them apart

Look at the Fly machine events and logs around 2026-11-05 04:02 UTC. Commands (check `--help` for
exact flags; they need a logged-in `fly` CLI):

- `fly status -a support-buddy-api`
- `fly machine list -a support-buddy-api`
- `fly machine status <machine id> -a support-buddy-api` (event history with timestamps)
- `fly logs -a support-buddy-api --no-tail` (recent logs only; older entries may be gone)

Reading the result:

- A start or resume event near that time: hypothesis 1 or 2. Then measure initialization time
  locally to see whether it can explain about 18 s.
- No such event and no related log lines: hypothesis 3, or an unlogged slow request. Then the next
  step is to keep monitoring and see whether it recurs.

## Questions this raises (not decisions)

Only worth deciding once the cause is known:

- Should `/api/v1/health` stay dependent on the knowledge engine? A check that does heavy work
  measures "how fast can the service initialize" as much as "is the service up". A lighter
  liveness check plus a separate readiness check is one common pattern; it is an option, not a
  recommendation made here.
- Should the engine be built at startup instead of on first use?
- Is `suspend` the right auto-stop mode for an API that also runs a background watcher?
- Is a 10 s maximum response time the right threshold for the monitor?

## Related context

- The public demo page returns a **401** from `/api/v1/briefings` on every load when no access key
  is entered. This is intended: the frontend falls back to the bundled demo data and shows an
  Unlock button (`web/src/api.ts`, `web/src/App.tsx`). A browser-level check that only asserts the
  page title cannot tell "locked demo mode" from "API is down", which is why the API health check
  exists as a separate check.
- The monitoring was set up as a practice Checkly project (two checks: a Playwright page check
  and this API check, with email alerts). That project lives outside this repository.

## Prompt for Claude Code

Paste the block below into a new Claude Code session in this repository.

```
Read docs/health-latency-investigation.md first. It describes one 18.25 s response from
GET /api/v1/health on the deployed API. The cause is NOT confirmed. Your job is to help me find
out, not to assume.

Rules for this session:
1. Verify before you trust. Re-read the code the document cites (src/api/server.py health() and
   get_engine(), src/core/knowledge/store.py and engine.py, fly.toml, start.sh) and tell me
   whether each "Verified" statement is still true. If anything has drifted, say so.
2. Treat the three hypotheses as unproven. Do not present any of them as the cause.
3. Measure, do not guess. Propose a way to time knowledge-engine initialization locally
   (cold start, with the same data directory layout), run it if it is safe, and report the real
   numbers. Do not estimate.
4. Fly: do not run any command that changes anything on Fly (deploy, restart, scale, secrets).
   Read-only commands (status, machine list, machine status, logs) are fine only if I have
   logged in and I approve each one. Never print or log secrets, and never open or commit .env.
5. Do not change behavior yet. First give me the evidence and a short list of options with
   trade-offs (for example: split liveness from readiness, build the engine at startup, change
   the auto-stop mode, change the monitor threshold). Recommend one, and say what evidence would
   change your mind.
6. If we decide on a change, follow CLAUDE.md: write the failing test first, use type hints, run
   the tests and ruff, and open a PR with `gh pr create` in English with a Summary and a Test plan.
   Do not push a branch without a PR.
7. Do not claim something is fixed unless you re-measured it and can show the before and after.
   If we cannot confirm the cause, say that plainly and record it in the document instead of
   guessing.

Start by listing what you verified and what you could not verify. Ask me before running anything
that touches the network or the deployed app.
```
