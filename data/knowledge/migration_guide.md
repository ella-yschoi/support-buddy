---
title: Migration Guides - Moving to CloudSync
category: faq
---

## Migrating from Dropbox

**Estimated time:** 1-4 hours for <100GB, 1-2 days for >1TB

**Steps:**
1. Install CloudSync desktop client alongside Dropbox
2. Dashboard > Settings > Import > "Migrate from Dropbox"
3. Authorize CloudSync to access your Dropbox account (read-only)
4. Select folders to migrate (all or specific folders)
5. CloudSync copies files to your CloudSync folder while preserving folder structure
6. Verify files in CloudSync, then uninstall Dropbox when ready

**What transfers:**
- All files and folder structure
- Shared folder memberships (invitations sent to collaborators)
- File comments (as metadata)

**What does NOT transfer:**
- Dropbox Paper documents (must be exported separately as .docx)
- Dropbox-specific features: Showcase, Transfer links
- Version history (only current version is migrated)
- Dropbox passwords/vault content

**Tips:**
- Run migration during off-hours to minimize bandwidth impact
- Keep both services active for 1-2 weeks to catch anything missed
- Notify collaborators before migration starts - shared folders will send re-invites

## Migrating from Google Drive

**Estimated time:** 1-4 hours for <100GB, 1-2 days for >1TB

**Steps:**
1. Dashboard > Settings > Import > "Migrate from Google Drive"
2. Authenticate with your Google account
3. Select Drive folders to migrate
4. Choose how to handle Google Docs/Sheets/Slides (see below)
5. Start migration

**Google Workspace file handling:**
- Google Docs → converted to .docx (Microsoft Word format)
- Google Sheets → converted to .xlsx (Microsoft Excel format)
- Google Slides → converted to .pptx (Microsoft PowerPoint format)
- Original Google format files remain in Google Drive (CloudSync copies the converted versions)

**Shared Drive migration:**
- Requires Google Workspace admin consent
- Each Shared Drive maps to a CloudSync Team Space
- Permissions are mapped: Owner→Owner, Manager→Admin, Contributor→Editor, Viewer→Viewer

**Tips:**
- Google Docs conversion may have minor formatting differences - review key documents
- Files shared via link (not folder membership) are not auto-migrated

## Migrating from OneDrive / SharePoint

**Estimated time:** 1-4 hours for <100GB, 1-2 days for >1TB

**Steps:**
1. Dashboard > Settings > Import > "Migrate from Microsoft OneDrive"
2. Authenticate with your Microsoft 365 account
3. Select OneDrive folders and/or SharePoint sites to migrate
4. Map SharePoint sites to CloudSync Team Spaces
5. Start migration

**SharePoint-specific considerations:**
- SharePoint document libraries map to CloudSync folders
- SharePoint list data is NOT migrated (it's structured data, not files)
- SharePoint page content is exported as HTML files
- Metadata columns are preserved as file properties where possible

**What does NOT transfer:**
- OneDrive Personal Vault files (must be exported manually)
- OneNote notebooks (export as PDF or .one files first)
- SharePoint workflows and Power Automate flows
- Version history beyond the current version

## Enterprise Bulk Migration

For organizations migrating 500+ users or >10TB of data, CloudSync offers a managed migration service.

**What's included:**
- Dedicated migration engineer assigned to your account
- Pre-migration assessment: audit current storage usage, identify potential issues
- Pilot migration: migrate 10-20 users first, validate, then proceed
- Parallel migration: run old and new systems side-by-side for 2-4 weeks
- User training: 1-hour live session for end users + admin training for IT team
- Post-migration validation: automated file count and checksum verification

**How to request:**
1. Contact your CSM or sales@cloudsync.io
2. Provide: current platform, user count, estimated data volume, timeline
3. CloudSync team delivers a migration plan within 5 business days
4. Typical enterprise migration: 2-6 weeks end to end

**SLA:** Zero data loss guarantee. If any files fail to migrate, CloudSync re-attempts automatically and escalates unresolved failures to the migration engineer.
