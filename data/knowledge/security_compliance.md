---
title: Security & Compliance
category: feature
---

## Data Encryption

CloudSync encrypts all data at rest and in transit.

**In transit:**
- TLS 1.3 for all API and web connections
- WebSocket connections (desktop sync) use WSS (TLS-encrypted)
- Certificate pinning on mobile apps to prevent MITM attacks

**At rest:**
- AES-256 encryption for all stored files
- Encryption keys managed via AWS KMS (Key Management Service)
- Enterprise customers can use Customer-Managed Keys (CMK) for added control

**Client-side encryption (Enterprise add-on):**
- Files are encrypted on the device before upload
- CloudSync servers never see unencrypted content
- Customer holds the master key — CloudSync cannot decrypt
- Trade-off: search and preview features are not available for client-side encrypted files

## Compliance Certifications

CloudSync maintains the following compliance certifications:

**SOC 2 Type II:**
- Audited annually by independent third party
- Covers: Security, Availability, Confidentiality
- Report available under NDA — contact sales@cloudsync.io

**GDPR:**
- EU data residency option (eu-west-1) for Enterprise customers
- Data Processing Agreement (DPA) available for all paid plans
- Right to erasure: Admin > Account > "Delete All Data" (permanent, irreversible)
- Data export: Admin > Account > "Export All Data" (ZIP file, delivered within 48 hours)

**HIPAA:**
- Business Associate Agreement (BAA) available for Enterprise Healthcare plans
- Requires client-side encryption add-on
- Audit log retention extended to 7 years for HIPAA compliance

**ISO 27001:**
- Certified since 2022
- Annual surveillance audits

**For compliance documentation requests:** Contact security@cloudsync.io or ask your CSM.

## User Access Controls

CloudSync provides granular access control for organizations.

**Workspace-level roles:**
| Role | Permissions |
|------|------------|
| Owner | Full control including billing and workspace deletion |
| Admin | Manage users, settings, integrations — no billing access |
| Member | Create files, join Team Spaces, use standard features |
| Guest | Access only specifically shared files/folders, no workspace navigation |

**File/folder-level permissions:**
- **Editor:** Read, write, delete, share
- **Viewer:** Read-only, download allowed
- **Restricted Viewer:** Read-only, download blocked (web preview only)

**Admin controls:**
- Enforce 2FA for all workspace members
- Set password complexity requirements
- Configure session timeout (1-72 hours)
- IP allowlisting (Enterprise): restrict access to specific IP ranges
- Device approval (Enterprise): new devices require admin approval before syncing

## Incident Response

CloudSync follows a structured incident response process.

**Severity levels:**
| Level | Definition | Response time | Example |
|-------|-----------|--------------|---------|
| P1 - Critical | Service-wide outage or data loss | 15 minutes | All users unable to sync |
| P2 - Major | Significant feature degraded for many users | 1 hour | Search not working |
| P3 - Minor | Feature degraded for some users | 4 hours | Slow uploads in one region |
| P4 - Low | Cosmetic or minor functionality issue | Next business day | UI rendering bug |

**Customer communication during incidents:**
- Status page updated within 15 minutes of P1/P2 detection
- Email notifications to affected Enterprise customers
- Post-incident report published within 5 business days for P1/P2

**How TSEs should handle incident inquiries:**
1. Check https://status.cloudsync.io first
2. If an incident is active, point the customer to the status page
3. Do NOT speculate about root cause — refer to official status updates
4. Log the customer's report in the incident ticket for impact tracking

## Data Retention & Deletion

CloudSync data retention policies vary by plan and data type.

**File retention:**
| Data type | Free | Pro | Enterprise |
|-----------|------|-----|-----------|
| Active files | Unlimited | Unlimited | Unlimited |
| Trash | 30 days | 30 days | 90 days |
| Version history | 5 versions | 30 versions | Unlimited |
| After account closure | 30 days | 30 days | 90 days (negotiable) |

**Audit log retention:**
- Pro: 90 days
- Enterprise: 1 year (HIPAA: 7 years)

**Permanent deletion:**
- When a file is removed from Trash (or retention expires), it is permanently deleted
- Permanent deletion is irreversible — files cannot be recovered by CloudSync staff
- Enterprise with CMK: deletion includes cryptographic shredding of the encryption key

**Account closure:**
1. Admin > Account > "Close Account"
2. 30-day (or 90-day Enterprise) grace period — can reactivate by logging in
3. After grace period: all data permanently deleted
4. Confirmation email sent at closure, 7 days before deletion, and after deletion
