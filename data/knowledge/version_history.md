---
title: Version History and File Recovery
category: feature
---

## Version History Overview

CloudSync automatically saves versions of every file each time it is modified. You can browse, preview, and restore any previous version.

**Retention by plan:**

| Plan | Version retention | Max versions per file |
|---|---|---|
| Free | 30 days | 10 |
| Pro | 180 days | 100 |
| Enterprise | 365 days | Unlimited |

## Viewing Version History

1. Right-click a file in the desktop client > "Version History"
2. Or: Dashboard > Files > select file > "..." > "Version History"
3. A panel shows all saved versions with timestamp and file size
4. Click any version to preview it

## Restoring a Previous Version

1. Open Version History for the file
2. Find the version you want to restore
3. Click "Restore" — this makes that version the current file
4. The current version is automatically saved before restoring, so you won't lose it

**Note:** Restoring a version on one device syncs the restored version to all other devices within one sync cycle.

## Downloading an Old Version Without Restoring

1. Open Version History
2. Click "Download" next to any version
3. The file is downloaded with the version date appended to the filename (e.g., `report_2026-09-15.pdf`)

## Trash and File Recovery

When a file is deleted from CloudSync (on any device or via web), it moves to Trash rather than being permanently deleted immediately.

**Trash retention:**
- Free: 30 days
- Pro: 30 days
- Enterprise: 90 days

**To restore a deleted file:**
1. Dashboard > Files > "Trash" (left sidebar)
2. Find the file (search by name or filter by deletion date)
3. Click "Restore" — the file returns to its original location
4. If the original folder was also deleted, the file restores to the root CloudSync folder

**To permanently delete:**
1. Dashboard > Files > Trash
2. Select files > "Delete Permanently"
3. Or click "Empty Trash" to remove all items

**Warning:** Permanent deletion cannot be undone. Permanently deleted files cannot be recovered by CloudSync support.

## Recovering Files Deleted Before Trash Was Introduced

For accounts that used CloudSync before the Trash feature (pre-2024), files deleted before that date may not be in Trash. Contact support with the exact filename and approximate deletion date — recovery may be possible from backups for up to 30 days.

## Version History for Team Spaces

In Team Spaces, version history shows who made each change:
- Timestamp of the change
- Team member who modified the file
- Size difference from the previous version

Admins can view version history for all files in the Space, including files they don't own.

## Common Issues

**"Version History is greyed out"**
- This file type may not support versioning (e.g., symlinks, `.cloudsync_temp` files)
- The file may be in a folder excluded from sync

**"I can only see a few versions, but I expected more"**
- Check your plan's version limit (Free: 10 versions, Pro: 100)
- Older versions beyond the limit are automatically pruned

**"Restore completed but old version didn't appear on my other device"**
- Wait for one sync cycle (usually under 60 seconds on a stable connection)
- Force a sync: right-click CloudSync tray icon > "Sync Now"
