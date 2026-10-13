---
title: CloudSync Performance Tuning Guide
category: troubleshooting
---

## Why Is My Sync Slow?

Sync speed depends on several factors: network bandwidth, file count, file size, and client configuration. Use this guide to diagnose and improve performance.

## Diagnosing Sync Speed

### Check Current Sync Status

1. Click the CloudSync tray icon > "Sync Status"
2. See: files pending, current upload/download speed, and estimated time remaining
3. If speed is unexpectedly low, check the throttle settings (see below)

### View Sync Logs

Desktop client: Settings > Advanced > "Open Log File"

Key log messages to look for:
- `THROTTLE: rate limit reached` — you've hit the per-account rate limit
- `CONFLICT: file modified on multiple devices` — conflicts are slowing sync
- `RETRY: upload failed, attempt N/3` — network instability
- `SLOW_OP: file took >30s` — individual file is taking long (network or file lock)

## Bandwidth Throttling

### Set Upload/Download Speed Limits

Useful if CloudSync is competing with other applications for bandwidth.

1. Settings > Sync > Bandwidth
2. Set maximum upload speed (e.g., 5 MB/s)
3. Set maximum download speed (e.g., 10 MB/s)
4. Optionally configure a schedule: e.g., unlimited overnight, throttled during work hours

### Scheduled Sync

For large sync jobs (initial sync or bulk uploads), schedule sync during off-peak hours:
1. Settings > Sync > Schedule
2. Toggle "Scheduled Sync" on
3. Set active hours (e.g., 11 PM – 6 AM)
4. CloudSync pauses outside these hours

## Reducing the Number of Files Being Monitored

Syncing folders with many small files (e.g., `node_modules`, `.git`, build artifacts) is inefficient and can overwhelm the sync index.

### Exclude Folders

1. Settings > Sync > Ignored Paths
2. Add folders or patterns to exclude:
   - `node_modules`
   - `.git`
   - `__pycache__`
   - `*.tmp`
   - `build/`, `dist/`
3. Click "Save" — excluded items are removed from sync immediately

### Selective Sync (Choose What to Sync Per Device)

1. Tray icon > Preferences > Selective Sync
2. Uncheck folders you don't need on this device
3. Useful for keeping large media libraries on desktop but not laptop

## Optimizing Large File Sync

### Enable Delta Sync (Pro/Enterprise)

Delta Sync only uploads/downloads the changed portions of a file instead of the whole file. Critical for large files that change frequently.

1. Settings > Sync > Advanced > Toggle "Delta Sync" on
2. Restart the sync agent
3. Best for files >10 MB with small incremental changes (e.g., databases, video projects)

### Chunked Uploads

Files over 100 MB are automatically uploaded in 50 MB chunks. If a chunk fails, only that chunk is retried — not the whole file. No configuration needed.

## Concurrent Sync Threads

### Increase Threads for Faster Sync (High-Bandwidth Environments)

Default: 5 concurrent operations. Increase if you have fast internet and many small files to sync.

1. Settings > Sync > Advanced > Max Concurrent Operations
2. Recommended range: 5–20 (higher values help with many small files, not large files)
3. Too high a value can cause throttling — start at 10 and increase gradually

### Decrease Threads to Reduce CPU/Memory Usage

If the desktop client is using too much CPU or RAM:
1. Reduce Max Concurrent Operations to 2–3
2. Enable "Low Power Mode": Settings > Sync > Advanced > "Low Power Mode"
   - Reduces CPU usage by 60–70%
   - Sync speed decreases by approximately 30%

## Memory Usage Optimization

### High Memory Usage Causes

- Watching >500,000 files in the sync folder
- Large pending queue (many files waiting to sync)
- Outdated client version with known memory leaks

### Fixes

1. **Update the client** — most memory issues are fixed in the latest version
2. **Reduce watched files** — move non-essential data out of the sync folder or add to Ignored Paths
3. **Restart the client** — clears the in-memory index (safe, index rebuilds from disk cache)
4. **Limit index cache:** Settings > Advanced > "Max Index Cache" — reduce from 512 MB to 256 MB on low-RAM devices

## Initial Sync Best Practices

When syncing a large dataset for the first time:

1. **Use the desktop client, not the web uploader** — more efficient for bulk transfers
2. **Disable other bandwidth-heavy applications** during initial sync
3. **Use a wired connection** instead of Wi-Fi for large initial syncs
4. **Set sync to run overnight** using the Scheduled Sync feature
5. **Don't restart your computer** during initial sync — it will resume but progress is lost for in-flight uploads

## Performance Error Codes

| Code | Meaning | Quick Fix |
|---|---|---|
| PERF-001 | Sync throttled (rate limit) | Reduce concurrent operations; upgrade plan |
| PERF-002 | High memory usage | Update client; reduce watched files |
| PERF-003 | Index rebuild required | Settings > Sync > Reset Sync |
| PERF-004 | Too many conflicts queued | Resolve conflicts in Dashboard > Files > Conflicts |
