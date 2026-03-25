# Sample Customer Profiles

## Acme Corp

- **Industry:** Manufacturing
- **Plan:** Enterprise
- **Users:** 2,300
- **Key contact:** James Park (IT Director)
- **Setup:** SSO via Okta, custom data residency (US-East), SCIM provisioning
- **Integration:** Webhooks to internal ERP system, REST API for automated backups
- **Common issues:** SSO certificate renewals, bulk user provisioning errors, audit log exports
- **Notes:** Largest Enterprise customer. Dedicated CSM: Rachel Kim. Quarterly business review.

## Big Retail Co

- **Industry:** E-commerce / Retail
- **Plan:** Enterprise
- **Users:** 850
- **Key contact:** Amanda Torres (DevOps Lead)
- **Setup:** SSO via Azure AD, US data residency, API-heavy workflow
- **Integration:** Webhooks to Slack + custom inventory system, CI/CD pipeline integration
- **Common issues:** Webhook delivery failures (API-002), API rate limiting (API-001), large file uploads
- **Notes:** Heavy API user (~8,000 req/min). Custom rate limit approved.

## DesignStudio

- **Industry:** Creative / Design Agency
- **Plan:** Pro
- **Users:** 45
- **Key contact:** Maya Chen (Creative Director)
- **Setup:** Standard email login, 2FA enabled, macOS-heavy team
- **Integration:** None (manual workflow)
- **Common issues:** Large PSD/AI file sync (500MB–2GB), slow sync, storage quota warnings
- **Notes:** Frequent complaints about sync speed for large design files. Upsell candidate for Enterprise (delta sync would help significantly).

## TechStart Inc

- **Industry:** Software / Startup
- **Plan:** Pro
- **Users:** 22
- **Key contact:** Dev Patel (CTO)
- **Setup:** Standard login, team spaces for each project
- **Integration:** Webhooks to GitHub Actions for deploy triggers
- **Common issues:** node_modules accidentally syncing, desktop client memory issues, webhook configuration
- **Notes:** Tech-savvy team. Often reports edge cases and feature requests. Active in community forum.

## Solo Freelancer — Sarah Kim

- **Industry:** Photography / Freelance
- **Plan:** Free
- **Users:** 1
- **Key contact:** Sarah Kim
- **Setup:** Desktop client on Windows 11 + mobile app on iPhone
- **Integration:** None
- **Common issues:** Storage quota (5GB limit), large photo uploads timing out, confusion about selective sync
- **Notes:** Price-sensitive. Has asked about Pro pricing twice. Good candidate for conversion email campaign.

## GlobalEd Foundation

- **Industry:** Education / Non-profit
- **Plan:** Pro (discounted)
- **Users:** 120
- **Key contact:** Dr. Lisa Wong (IT Coordinator)
- **Setup:** Google Workspace SSO (not available on Pro — using manual login), team spaces per department
- **Integration:** None
- **Common issues:** Users forgetting passwords (no SSO), sharing permissions confusion, accidental file deletions
- **Notes:** Received 50% non-profit discount. Would benefit from Enterprise SSO but budget is limited. High ticket volume relative to user count.
