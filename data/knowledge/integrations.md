---
title: Third-Party Integration Guides
category: feature
---

## Slack Integration

Connect CloudSync to Slack to receive file activity notifications in your channels.

**Setup:**
1. Dashboard > Settings > Integrations > Slack > "Connect"
2. Authorize CloudSync in the Slack OAuth flow
3. Select a default channel for notifications
4. Choose which events to notify: file uploads, shares, comments, errors

**Available Slash Commands (after install):**
- `/cloudsync search <query>` — Search files from Slack
- `/cloudsync share <file-id> <#channel>` — Share a file link to a channel
- `/cloudsync status` — Check sync status for your account

**Troubleshooting:**
- If notifications stop: check that the Slack bot is still in the channel (may have been removed)
- Re-authorize if you see "token_revoked" errors in the integration logs
- Slack integration uses a separate webhook — does not count against your webhook endpoint limit

## Jira Integration

Link CloudSync files to Jira issues for seamless project tracking.

**Setup:**
1. Dashboard > Settings > Integrations > Jira > "Connect"
2. Enter your Jira instance URL (e.g., `https://yourcompany.atlassian.net`)
3. Authenticate with a Jira admin account
4. Map CloudSync team spaces to Jira projects (optional)

**Features:**
- Attach CloudSync file links to Jira issues (always up-to-date, unlike uploaded attachments)
- View Jira issue context from CloudSync file details panel
- Auto-create CloudSync folder when a new Jira project is created
- Activity feed shows linked Jira issue updates alongside file changes

**Limitations:**
- Jira Server (self-hosted) requires CloudSync Enterprise + network configuration
- Maximum 10 file links per Jira issue
- Jira integration requires Pro or Enterprise plan

## Zapier Integration

Automate workflows between CloudSync and 5,000+ other apps using Zapier.

**Available Triggers (CloudSync → other apps):**
- New file uploaded
- File updated
- File shared
- New comment on file
- New team member joined

**Available Actions (other apps → CloudSync):**
- Upload file from URL
- Create folder
- Share file/folder with user
- Move file to folder

**Popular Zap recipes:**
1. "When a file is uploaded to CloudSync, post to Slack" — keeps team informed
2. "When a Google Form is submitted, create a CloudSync folder for the respondent"
3. "When a file is shared in CloudSync, create a Trello card for review"
4. "Daily: export CloudSync audit log to Google Sheets"

**Setup:** Go to zapier.com, search for "CloudSync", and follow the connection wizard. You'll need a CloudSync API key with read-write scope.

## GitHub Integration

Connect CloudSync to GitHub for developer workflows.

**Setup:**
1. Dashboard > Settings > Integrations > GitHub > "Connect"
2. Authorize via GitHub OAuth
3. Select repositories to link

**Features:**
- Auto-sync release assets: when a GitHub release is published, attached files are mirrored to a CloudSync folder
- Link CloudSync design files in GitHub PRs and issues
- Webhook bridge: GitHub events can trigger CloudSync webhooks (useful for CI/CD asset deployment)

**Use cases:**
- Design teams store assets in CloudSync, developers reference them in GitHub issues
- Build artifacts from GitHub Actions uploaded to CloudSync for QA distribution
- Documentation PDFs auto-synced from CloudSync to GitHub Pages

**Requirements:** Pro or Enterprise plan. GitHub Free, Pro, or Enterprise.

## Microsoft 365 Integration

Access CloudSync files directly from Microsoft Office applications.

**Setup:**
1. Dashboard > Settings > Integrations > Microsoft 365 > "Connect"
2. Authenticate with a Microsoft 365 admin account
3. Install the CloudSync add-in from the Microsoft Add-ins store

**Features:**
- Open CloudSync files directly in Word, Excel, PowerPoint (web and desktop)
- Save Office documents directly to CloudSync from the "Save As" dialog
- CloudSync appears as a location in the Office file picker
- Real-time co-editing: changes saved in Office are synced to CloudSync immediately

**Limitations:**
- Requires Microsoft 365 Business or Enterprise license
- CloudSync Pro or Enterprise plan required
- Co-editing works for Office web apps only (desktop apps save on close)
- Maximum file size for direct edit: 500MB
