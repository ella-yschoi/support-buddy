---
title: CloudSync Feature Documentation
category: feature
---

## Selective Sync

Allows users to choose which folders sync to each device. Useful for devices with limited storage.

**How to configure:**
1. Right-click the CloudSync tray icon
2. Select "Preferences" > "Selective Sync"
3. Uncheck folders you don't want on this device
4. Click "Apply"

**Notes:**
- Unsynced folders are removed from the local device but remain on the cloud
- Changes take effect after the next sync cycle
- Available on all plans

## Delta Sync

Only uploads/downloads the changed portions of files, significantly reducing bandwidth for large files.

**How to enable:**
1. Go to Settings > Sync > Advanced
2. Toggle "Delta Sync" on
3. Restart the sync agent

**Notes:**
- Works best with files >10MB
- Supported formats: all (binary diff algorithm)
- Reduces bandwidth by up to 90% for small changes to large files
- Available on Pro and Enterprise plans

## Team Spaces

Shared workspaces for team collaboration with role-based access control.

**Roles:**
- **Owner:** Full control, billing, can delete the space
- **Admin:** Manage members, configure settings, manage shares
- **Editor:** Upload, modify, delete files within the space
- **Viewer:** Read-only access to all files

**How to create a Team Space:**
1. Dashboard > Team Spaces > "Create New"
2. Name the space and set default permissions
3. Invite members by email or from workspace directory
4. Set storage quota for the space (Enterprise only)

## Webhooks

Real-time notifications when events occur in CloudSync.

**Supported events:**
- `file.created`, `file.updated`, `file.deleted`
- `folder.created`, `folder.deleted`
- `share.created`, `share.revoked`
- `user.joined`, `user.removed`

**Setup:**
1. Dashboard > Settings > Webhooks > "Add Webhook"
2. Enter the endpoint URL (must be HTTPS)
3. Select events to subscribe to
4. Optionally set a signing secret for verification
5. Click "Create"

**Payload format:** JSON with event type, timestamp, actor, and resource details.
**Retry policy:** 3 retries with exponential backoff (1s, 10s, 100s).

## Audit Log

Complete history of all actions within the workspace. Available on Enterprise plan.

**What's logged:**
- File operations (create, update, delete, move, share)
- User management (invite, remove, role change)
- Admin actions (settings change, SSO configuration)
- API access (key creation, key revocation)

**How to access:**
1. Admin Dashboard > Audit Log
2. Filter by user, action type, date range
3. Export as CSV for compliance reporting

**Retention:** 1 year (Enterprise), 90 days (Pro), not available (Free)
