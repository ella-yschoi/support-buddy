---
title: Known Issues & Workarounds
category: troubleshooting
---

## KI-001: macOS Sonoma Finder Integration Broken (v4.2.x)

**Affected:** Desktop client v4.2.0–v4.2.1 on macOS Sonoma 14.x
**Status:** Fix in progress - ETA: v4.3.0 (next release)
**Severity:** Medium

**Symptoms:**
- CloudSync overlay icons (sync status badges) do not appear in Finder
- Right-click context menu "Share via CloudSync" option is missing

**Root cause:** Apple changed the Finder extension API in macOS Sonoma. Our extension needs to be recompiled with the new SDK.

**Workaround:**
1. Use the CloudSync desktop app directly (drag and drop files)
2. Or use the web dashboard for sharing
3. Sync functionality itself is NOT affected - only the Finder UI integration

## KI-002: Duplicate File Notifications on Windows

**Affected:** Desktop client v4.1.0+ on Windows 10/11
**Status:** Investigating
**Severity:** Low

**Symptoms:**
- Users receive 2-3 duplicate "File synced" notifications for a single file
- Notification count badge shows inflated numbers

**Root cause:** Windows File System watcher fires multiple events for a single file save (write + metadata update + close).

**Workaround:**
1. Settings > Notifications > set "Notification Cooldown" to 5 seconds
2. Or disable desktop notifications entirely: Settings > Notifications > toggle off

## KI-003: Delta Sync Fails for Files Over 4GB

**Affected:** All platforms, Pro and Enterprise plans
**Status:** Known limitation - architectural change required
**Severity:** Medium

**Symptoms:**
- Files over 4GB always upload completely instead of using delta sync
- No error is shown - delta sync silently falls back to full upload

**Root cause:** The delta sync algorithm uses a 32-bit block index, limiting the addressable file size to ~4GB.

**Workaround:**
- Split large files into smaller parts if possible
- Schedule large file syncs during off-peak hours to reduce bandwidth impact
- For video files: consider using lower-resolution proxies for day-to-day work and syncing originals overnight

## KI-004: Search Not Finding Recently Uploaded Files

**Affected:** Web dashboard, all plans
**Status:** By design - search index updates are asynchronous
**Severity:** Low

**Symptoms:**
- A file uploaded within the last 1-2 minutes does not appear in search results
- File is visible in the folder view but not returned by the search bar

**Root cause:** The full-text search index updates asynchronously with a 60-90 second delay after file upload.

**Workaround:**
1. Wait 2 minutes and search again
2. Navigate to the folder directly using the folder tree instead of search
3. Use the API endpoint `GET /api/v1/files?folder_id=xxx` for immediate results (bypasses search index)

## KI-005: Team Space Storage Showing Incorrect Usage

**Affected:** Web dashboard, Enterprise plan
**Status:** Fix deployed - may require cache refresh
**Severity:** Low

**Symptoms:**
- Team Space storage meter shows usage significantly higher than actual files
- Discrepancy between Team Space usage and individual file sizes sum

**Root cause:** Deleted files in Trash were still counted toward Team Space storage quota. Fixed in server-side update 2024-03-01.

**Workaround:**
1. Empty the Team Space trash: Team Space > Trash > "Empty Trash"
2. Wait 24 hours for the storage calculation to refresh
3. If still incorrect after 24 hours, contact support - we can trigger a manual recalculation
