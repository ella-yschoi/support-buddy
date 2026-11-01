#!/bin/bash
# Start the Linear watcher in the background, then the API server in the foreground.
# The watcher uses cursor-based polling so it safely resumes after machine suspend/restart.
#
# The watcher only starts when it is scoped. WATCH_LABEL is required (WATCH_TEAM is an optional
# extra filter) so it can never brief every open issue in a workspace, real ones included.

if [ -n "$LINEAR_API_KEY" ] && [ -n "$WATCH_LABEL" ]; then
  scope=(--label "$WATCH_LABEL")
  [ -n "$WATCH_TEAM" ] && scope+=(--team "$WATCH_TEAM")
  echo "[start] Starting Linear watcher (interval: ${WATCH_INTERVAL:-60}s, label: $WATCH_LABEL, team: ${WATCH_TEAM:-all})"
  .venv/bin/support-buddy watch \
    --source linear \
    "${scope[@]}" \
    --interval "${WATCH_INTERVAL:-60}" \
    >> /tmp/watcher.log 2>&1 &
  echo "[start] Watcher PID: $!"
elif [ -n "$LINEAR_API_KEY" ]; then
  echo "[start] WATCH_LABEL not set — watcher disabled (it will not read a whole workspace)"
else
  echo "[start] LINEAR_API_KEY not set — watcher disabled"
fi

echo "[start] Starting API server"
exec .venv/bin/uvicorn src.api.server:app --host 0.0.0.0 --port 8080
