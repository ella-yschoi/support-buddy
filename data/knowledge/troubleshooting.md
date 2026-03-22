---
title: Troubleshooting Guide
category: troubleshooting
---

## Files Not Syncing

**Symptoms:** Files modified on one device do not appear on other devices. Sync icon shows paused or error state.

**Diagnostic Steps:**
1. Check sync agent status — tray icon should be green (running). Yellow = paused, Red = error
2. Verify network connectivity — try accessing https://status.cloudsync.io
3. Check sync logs: Settings > Logs > View Recent
4. Verify the file is in a synced folder (not excluded)
5. Check if the file exceeds the 5GB size limit
6. Check for file locks — close any application that may have the file open

**Common Resolutions:**
- Restart the sync agent (right-click tray icon > Restart)
- Reset sync index: Settings > Sync > Reset Sync
- Verify the file path doesn't contain special characters (avoid: < > : " | ? *)
- Check antivirus exclusions — add CloudSync data folder to exclusions

## Slow Sync Performance

**Symptoms:** Sync takes much longer than expected. Upload/download speeds are significantly below network bandwidth.

**Diagnostic Steps:**
1. Check available bandwidth with a speed test
2. Check number of files being synced — many small files are slower than fewer large files
3. Check concurrent sync threads: Settings > Sync > Advanced
4. Look for PERF-001 (throttling) errors in logs
5. Check system resources (CPU, RAM, disk I/O)

**Common Resolutions:**
- Increase sync threads for fast connections (max 10)
- Decrease sync threads if CPU/RAM is constrained
- Exclude unnecessary large directories (e.g., build/, node_modules/)
- Enable delta sync for large files: Settings > Sync > Delta Sync
- Schedule bulk syncs during off-peak hours

## Permission Denied Errors

**Symptoms:** User receives AUTH-002 when accessing shared folders or features.

**Diagnostic Steps:**
1. Verify the user's current role in the workspace
2. Check if the specific folder/file share is still active
3. Check if the user's account is in good standing (not suspended)
4. For SSO users, verify group membership in IdP

**Common Resolutions:**
- Folder owner re-shares with correct permissions
- Workspace admin adjusts user role
- For SSO: verify group-to-role mapping in Admin > SSO > Role Mapping

## Webhook Not Firing

**Symptoms:** Expected webhook notifications are not being received by the customer's endpoint.

**Diagnostic Steps:**
1. Check webhook configuration: Dashboard > Settings > Webhooks
2. Verify the endpoint URL is correct and accessible
3. Check webhook delivery logs for error messages
4. Test the endpoint with a manual trigger: Webhooks > Test
5. Verify event types are correctly configured

**Common Resolutions:**
- Fix endpoint URL (ensure HTTPS, no trailing slash issues)
- Update SSL certificate on the receiving server
- Increase endpoint timeout (must respond within 10 seconds)
- Check firewall rules — allow traffic from CloudSync IP ranges (see docs)
- Re-register the webhook if delivery log shows persistent failures

## Desktop Client Crashes on Startup

**Symptoms:** CloudSync desktop client fails to start or crashes immediately after launch.

**Diagnostic Steps:**
1. Check system requirements: macOS 12+, Windows 10+, Ubuntu 20.04+
2. Look for crash logs: ~/CloudSync/logs/crash.log
3. Check available disk space (need at least 500MB free)
4. Verify no conflicting software (other sync tools)

**Common Resolutions:**
- Update to the latest client version
- Clear local cache: delete ~/CloudSync/cache/ and restart
- Reinstall the desktop client
- Disable conflicting sync tools (Dropbox, OneDrive, etc.) temporarily to test
- Run as administrator (Windows) or check Full Disk Access (macOS)
