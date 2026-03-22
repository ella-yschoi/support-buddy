---
title: Error Code Reference
category: error_code
---

## SYNC-001: File Conflict

Two or more devices modified the same file before sync could complete. CloudSync detected divergent versions.

**Common causes:**
- Editing the same file on two devices while offline
- Network interruption during a sync operation

**Resolution:**
1. Open the Conflict Resolver: Dashboard > Files > Conflicts
2. Compare the two versions side by side
3. Choose which version to keep, or merge manually
4. Click "Resolve" to clear the conflict

## SYNC-002: Upload Failed

File upload to cloud storage failed after all retry attempts.

**Common causes:**
- Network connectivity issues
- Storage quota exceeded
- File exceeds 5GB size limit
- File is locked by another application

**Resolution:**
1. Check network connectivity
2. Check storage usage: Dashboard > Account > Storage
3. If quota exceeded, delete files or upgrade plan
4. Close any applications that may have the file locked
5. Retry sync from Settings > Sync > Retry Failed

## SYNC-003: Download Failed

File download from cloud storage failed.

**Common causes:**
- Network issues
- File was deleted on the server during download
- Insufficient local disk space

**Resolution:**
1. Check network connectivity
2. Verify the file still exists on the cloud
3. Check local disk space (need at least 2x the file size for temp space)
4. Retry from Settings > Sync > Retry Failed

## SYNC-004: Index Corruption

The local sync index has become corrupted and cannot be read.

**Common causes:**
- Unexpected system shutdown during sync
- Disk errors
- Antivirus software interference

**Resolution:**
1. Go to Settings > Sync > Reset Sync
2. Wait for re-indexing to complete (10-30 minutes)
3. If the issue persists, uninstall and reinstall the desktop client
4. Contact support if re-indexing fails repeatedly

## AUTH-001: Session Expired

The user session has expired and requires re-authentication.

**Common causes:**
- Session timeout (default: 24 hours for Free/Pro, configurable for Enterprise)
- Password was changed on another device
- Admin revoked the session

**Resolution:**
1. Log in again with your credentials
2. If unable to log in, reset your password
3. If the issue recurs frequently, check if an admin has set a short session timeout

## AUTH-002: Permission Denied

User does not have permission to access the requested resource.

**Common causes:**
- Folder share was revoked
- User role was changed (e.g., from Editor to Viewer)
- Attempting to access an admin-only feature

**Resolution:**
1. Check with the folder/file owner to verify sharing settings
2. Contact your workspace admin to verify your role
3. If you need higher permissions, request access through the "Request Access" button

## AUTH-003: SSO Configuration Error

Single Sign-On authentication failed due to configuration issues.

**Common causes:**
- SAML certificate expired
- IdP metadata URL unreachable
- Attribute mapping mismatch

**Resolution:**
1. Verify the SAML certificate is valid and not expired
2. Check that the IdP metadata URL is accessible from CloudSync servers
3. Verify attribute mapping: email, firstName, lastName must be mapped
4. Contact support with your SSO configuration details for troubleshooting

## PERF-001: Sync Throttled

Sync speed has been throttled due to rate limiting or bandwidth constraints.

**Common causes:**
- Too many concurrent sync operations (default limit: 5)
- Account-level rate limit reached
- Server-side throttling during peak hours

**Resolution:**
1. Reduce concurrent sync threads: Settings > Sync > Advanced > Max Threads
2. Schedule large syncs during off-peak hours
3. For Enterprise: contact support to adjust rate limits

## PERF-002: High Memory Usage

The CloudSync desktop client is using excessive memory.

**Common causes:**
- Monitoring too many files (>500,000)
- Large number of pending sync operations
- Memory leak in older client versions

**Resolution:**
1. Update to the latest client version
2. Reduce the number of monitored folders
3. Exclude large directories with many small files (e.g., node_modules)
4. Restart the CloudSync client

## API-001: Rate Limit Exceeded

API request was rejected due to rate limiting.

**Common causes:**
- Exceeding 100 requests/minute (Free), 1000/minute (Pro), 10000/minute (Enterprise)
- Burst of requests in a short window

**Resolution:**
1. Implement exponential backoff in your API client
2. Cache responses where possible
3. Upgrade to a higher plan for increased limits
4. Use batch endpoints where available

## API-002: Webhook Delivery Failed

Webhook notification could not be delivered to the configured endpoint.

**Common causes:**
- Endpoint URL unreachable
- Endpoint returned non-2xx status code
- SSL certificate verification failed
- Payload too large (max 1MB)

**Resolution:**
1. Verify the webhook endpoint is accessible from the internet
2. Check that the endpoint returns 200 OK within 10 seconds
3. Verify SSL certificate is valid
4. Check webhook logs: Dashboard > Settings > Webhooks > Delivery Logs
5. CloudSync retries failed webhooks 3 times with exponential backoff
