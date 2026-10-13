---
title: CloudSync Onboarding Guide
category: onboarding
---

## Getting Started with CloudSync

### Step 1: Create Your Account

1. Go to app.cloudsync.io and click "Sign Up"
2. Enter your email and create a password (minimum 10 characters)
3. Verify your email address via the confirmation link
4. Complete your profile: name, company, and timezone

### Step 2: Install the Desktop Client

CloudSync works best with the desktop client installed.

**Windows:**
1. Download `CloudSync-Setup.exe` from dashboard.cloudsync.io/download
2. Run the installer and follow the prompts
3. Sign in with your CloudSync credentials
4. Choose your sync folder (default: `C:\Users\<name>\CloudSync`)

**macOS:**
1. Download `CloudSync.dmg` from dashboard.cloudsync.io/download
2. Drag CloudSync to Applications
3. Open CloudSync and sign in
4. Grant the required permissions (Full Disk Access is recommended)
5. Choose your sync folder (default: `~/CloudSync`)

**Linux:**
1. Download the `.AppImage` or `.deb` package
2. For `.deb`: `sudo dpkg -i cloudsync-*.deb`
3. Launch from Applications or run `cloudsync` in terminal

### Step 3: Upload Your First Files

**Via desktop client:** Simply move or copy files into your CloudSync folder. They sync automatically.

**Via web:** Dashboard > Files > Upload (drag and drop or click to browse). Supports up to 5 GB per file.

**Via API:** See the API Guide for programmatic uploads.

### Step 4: Invite Team Members (Pro/Enterprise)

1. Dashboard > Team > Members > "Invite"
2. Enter email addresses (one per line for bulk invites)
3. Select a role: Admin, Editor, or Viewer
4. Click "Send Invitations"

Members receive an email invitation valid for 7 days. Resend via Team > Members > "Resend Invite".

### Step 5: Set Up Two-Factor Authentication (Recommended)

1. Account > Security > Two-Factor Authentication
2. Choose your method: Authenticator app (recommended) or SMS
3. Scan the QR code with your authenticator app
4. Enter the 6-digit code to confirm
5. Save your backup codes in a safe place

### Common First-Day Issues

**"Sync not starting after install"**
- Ensure CloudSync is running (check system tray / menu bar icon)
- Check that your firewall allows CloudSync on ports 443 and 8443
- Try signing out and back in

**"Files not appearing on other devices"**
- Initial sync can take time depending on file count and size
- Verify the other device is also signed in and online
- Check that Selective Sync hasn't excluded the folder

**"Invitation email not received"**
- Ask the invitee to check their spam folder
- Verify the email address is correct
- Admin can resend from Team > Members > "Resend Invite"

### Storage Quotas by Plan

| Plan | Storage | What counts toward quota |
|---|---|---|
| Free | 5 GB | All files in your CloudSync folder |
| Pro | 1 TB | All files in your CloudSync folder |
| Enterprise | Unlimited | N/A |

Deleted files in Trash still count toward quota until permanently deleted.
