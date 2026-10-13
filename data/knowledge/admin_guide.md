---
title: CloudSync Workspace Administration Guide
category: admin
---

## Admin Role Overview

Workspace Admins can manage members, configure security policies, and monitor workspace activity. The workspace Owner has all Admin permissions plus the ability to delete the workspace or transfer ownership.

**Admin capabilities:**
- Invite, remove, and manage member roles
- Configure SSO and 2FA policies (Enterprise)
- View and export Audit Logs (Enterprise)
- Manage Team Spaces and shared resources
- Set storage quotas per Team Space (Enterprise)
- Configure API access and webhook policies

## Managing Members

### Inviting Members

1. Admin Dashboard > Members > "Invite Members"
2. Enter email addresses (comma-separated for bulk)
3. Assign a default role: Admin, Editor, or Viewer
4. Optionally assign to a Team Space on join
5. Click "Send Invitations"

Invitations expire after 7 days. Resend from Members > Pending Invitations.

### Changing Member Roles

1. Admin Dashboard > Members
2. Find the member and click their name
3. Click "Change Role" and select the new role
4. Confirm — the change takes effect immediately

**Note:** Changing a member from Editor to Viewer revokes write access instantly across all devices.

### Removing Members

1. Admin Dashboard > Members > select member > "Remove"
2. Choose what to do with their files:
   - **Transfer to another member:** Files are moved to the selected member's ownership
   - **Keep in workspace:** Files remain but are unowned (accessible to Admins)
   - **Delete:** Files move to Trash (recoverable for 30/90 days depending on plan)
3. Confirm removal

Removed members immediately lose access. Active sessions are terminated within 60 seconds.

### Deactivating vs. Removing

- **Deactivate:** Member can't log in but their files and history are preserved. Useful for temporary leave. Not billed.
- **Remove:** Permanent. Files must be transferred or deleted. Cannot be undone (but the person can be re-invited).

## Security Policies

### Enforcing Two-Factor Authentication

1. Admin Dashboard > Security > Two-Factor Authentication
2. Toggle "Require 2FA for all members"
3. Set a grace period (1–14 days) for members to comply
4. Members who don't set up 2FA by the deadline are locked out until they do

### Session Timeout

Configure how long sessions stay active before requiring re-login:
1. Admin Dashboard > Security > Session Policy
2. Set timeout duration (minimum: 1 hour, maximum: 30 days)
3. Optionally require re-authentication for sensitive actions (download, delete)

### IP Allowlist (Enterprise)

Restrict access to specific IP ranges:
1. Admin Dashboard > Security > IP Allowlist
2. Add CIDR ranges (e.g., `203.0.113.0/24`)
3. Optionally exempt certain users (e.g., executives who travel)

**Warning:** If you lock yourself out, contact support immediately with your admin credentials.

### Device Management

View and revoke access for any device connected to the workspace:
1. Admin Dashboard > Devices
2. See all active devices: device name, OS, last active, location
3. Click "Revoke" to disconnect a specific device
4. "Revoke All" forces all members to re-authenticate on all devices

## Team Space Management

### Creating a Team Space

1. Admin Dashboard > Team Spaces > "Create New"
2. Set name, description, and default member permissions
3. Set storage quota if on Enterprise plan
4. Click "Create"

### Transferring Team Space Ownership

1. Admin Dashboard > Team Spaces > select space > "Settings"
2. "Transfer Ownership" > select new owner (must be an Admin or Owner)
3. Confirm — original owner retains Admin role unless manually changed

### Archiving a Team Space

Archived spaces are read-only. No new files can be added.
1. Admin Dashboard > Team Spaces > select space > "Archive"
2. Members can still view and download files
3. Archived spaces count toward storage quota
4. Unarchive at any time from the same menu

## Monitoring and Reporting

### Usage Dashboard

Admin Dashboard > Analytics shows:
- Storage used vs. quota (workspace total and per-member)
- Active users (daily, weekly, monthly)
- File operations (uploads, downloads, deletes)
- API usage by key
- Sync error rate

### Audit Log (Enterprise)

All admin-relevant events are logged with:
- Timestamp (UTC)
- Actor (user or API key)
- Action type
- Affected resource
- IP address and device

**Export:** Audit Log > "Export CSV" (up to 90 days per export).
**SIEM integration:** Audit events can be streamed to Splunk, Datadog, or any syslog endpoint.

## Common Admin Scenarios

**"A member lost their 2FA device and is locked out"**
1. Admin Dashboard > Members > find member > "Bypass 2FA"
2. This grants a one-time login link valid for 15 minutes
3. Advise the member to set up 2FA with a new device immediately after logging in

**"We're over our storage quota and sync has paused"**
1. Check who is using the most storage: Analytics > Storage by Member
2. Ask members to move files to external storage or delete unneeded files
3. Or upgrade the plan: Account > Plans

**"An employee left the company and we need their files"**
1. Remove the member and choose "Transfer to another member"
2. Revoke all their active devices from the Devices tab
3. Rotate any API keys they owned: API Settings > Keys
