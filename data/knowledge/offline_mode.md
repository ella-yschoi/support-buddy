---
title: CloudSync Offline Mode
category: feature
---

## How Offline Mode Works

CloudSync continues to work without an internet connection. Files in your sync folder are always available locally — you can read, edit, and create files offline. When connectivity is restored, CloudSync automatically syncs all changes.

## What You Can Do Offline

- **Read any file** in your local sync folder
- **Edit files** — changes are queued and uploaded when back online
- **Create new files and folders** — synced on reconnection
- **Delete files** — deletions are synced on reconnection (file goes to Trash on other devices)
- **Move and rename files** — synced on reconnection

## What Requires an Internet Connection

- Accessing files that are cloud-only (not downloaded locally)
- Sharing files or folders with other users
- Inviting team members
- Accessing version history for files not cached locally
- Using the web dashboard (app.cloudsync.io)
- API calls

## Offline Indicators

**Desktop tray icon:**
- Cloud with checkmark = synced and online
- Cloud with X = offline (no connection)
- Cloud with arrows = syncing
- Cloud with warning = sync error

**File status badges (Windows Explorer / macOS Finder):**
- Green checkmark = synced locally
- Blue circle = syncing
- Grey dash = available cloud-only (not downloaded)
- Red X = sync error

## Cloud-Only Files (Smart Sync)

On Pro and Enterprise plans, files can be "cloud-only" — they appear in your folder but are not downloaded until you open them (similar to OneDrive's "Files On-Demand" or Dropbox's "Smart Sync").

**To download a file for offline access:**
1. Right-click the file > "Make Available Offline"
2. The file downloads to your local device
3. The green checkmark confirms it's available offline

**To make a file cloud-only again (free up local space):**
1. Right-click the file > "Free Up Space"
2. The local copy is removed but the file remains in the cloud

**To make an entire folder available offline:**
1. Right-click the folder > "Make Available Offline"
2. All files in the folder (recursively) are downloaded

## Conflict Resolution After Going Back Online

If you edited a file offline that someone else also edited while you were offline, CloudSync creates a conflict:

1. Both versions are preserved — you'll see `filename.txt` and `filename (conflicted copy 2026-10-13).txt`
2. A notification appears when you come back online
3. Go to Dashboard > Files > Conflicts to review and resolve
4. Choose which version to keep, or manually merge the changes

## Offline Queue

When offline, CloudSync builds a queue of pending operations. You can view this:
1. Tray icon > "Sync Status"
2. "Pending" tab shows all queued operations: uploads, deletes, moves

Large queues (e.g., after a long offline period) may take several minutes to process after reconnecting.

## Common Offline Issues

**"File shows as available offline but won't open"**
- The local copy may be corrupted
- Right-click > "Force Re-download" to fetch a fresh copy from the cloud

**"Changes I made offline didn't sync"**
- Check the Sync Status panel for errors
- Look for a conflict version of the file
- If the file shows a red X, check error_codes.md for SYNC-001 or SYNC-002

**"I can't see any files when offline"**
- Files may be cloud-only (not downloaded locally)
- On initial setup, CloudSync downloads only recently accessed files
- Right-click folders to "Make Available Offline" for guaranteed local access

**"Sync is very slow after a long offline period"**
- Normal — CloudSync is processing a large queue
- Don't restart the client; let it finish
- Check Sync Status for estimated time remaining
