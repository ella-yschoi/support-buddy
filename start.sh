#!/bin/bash
# Start the Linear watcher in the background, then the API server in the foreground.
# The watcher uses cursor-based polling so it safely resumes after machine suspend/restart.

if [ -n "$LINEAR_API_KEY" ]; then
  echo "[start] Starting Linear watcher (interval: ${WATCH_INTERVAL:-60}s)"
  .venv/bin/support-buddy watch \
    --source linear \
    --interval "${WATCH_INTERVAL:-60}" \
    >> /tmp/watcher.log 2>&1 &
  echo "[start] Watcher PID: $!"
else
  echo "[start] LINEAR_API_KEY not set — watcher disabled"
fi

echo "[start] Starting API server"
exec .venv/bin/uvicorn src.api.server:app --host 0.0.0.0 --port 8080
