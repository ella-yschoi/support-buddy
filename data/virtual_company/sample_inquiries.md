# Sample Customer Inquiries

## Inquiry 1: Sync Failure — Storage Quota

**Customer:** Sarah Kim (Free plan, solo user)
**Channel:** Email
**Priority:** Medium

> Subject: Files stopped syncing — error SYNC-002
>
> Hi support team,
>
> Since yesterday my files are not syncing anymore. I keep seeing a SYNC-002 error in the desktop app. I have a lot of photos from a recent shoot that I need to back up urgently. The app says something about storage but I'm not sure what to do. Can you help?
>
> Thanks,
> Sarah

**Expected handling:**
- Category: sync
- Severity: medium
- Key actions: Check storage usage (Free plan = 5GB), suggest deleting old files or upgrading to Pro
- Relevant KB: error_codes.md (SYNC-002), plan_matrix.md (storage limits), faq.md (file types)

---

## Inquiry 2: SSO Outage — Entire Organization

**Customer:** James Park, Acme Corp (Enterprise, 2,300 users)
**Channel:** Email (urgent)
**Priority:** Critical

> Subject: URGENT — All employees unable to log in via SSO
>
> Hi,
>
> Starting about 30 minutes ago, none of our employees can log into CloudSync through Okta SSO. They all see an "Authentication failed" error. This is affecting our entire organization of 2,300 users. We have critical project deadlines today.
>
> I can still log in with my admin email/password but regular users cannot. Please advise immediately.
>
> James Park
> IT Director, Acme Corp

**Expected handling:**
- Category: permission
- Severity: critical
- Key actions: Follow SSO runbook, check certificate expiry, suggest break-glass login for critical users
- Relevant KB: runbooks.md (SSO Login Failure), error_codes.md (AUTH-003), sso_guide.md

---

## Inquiry 3: Webhook Not Firing

**Customer:** Amanda Torres, Big Retail Co (Enterprise)
**Channel:** In-app chat
**Priority:** High

> Our webhooks to https://api.bigretail.com/hooks/cloudsync stopped working about an hour ago. We rely on these for our inventory sync pipeline and orders are piling up. The webhook delivery logs in the dashboard show "Connection timed out" for every attempt. Nothing changed on our end. Can you check if something is wrong on CloudSync's side?

**Expected handling:**
- Category: api
- Severity: high
- Key actions: Check CloudSync API status, verify webhook endpoint health from CloudSync side, review delivery logs
- Relevant KB: error_codes.md (API-002), features.md (Webhooks), runbooks.md (API Integration Failures)

---

## Inquiry 4: Slow Sync for Large Files

**Customer:** Maya Chen, DesignStudio (Pro, 45 users)
**Channel:** Email
**Priority:** Medium

> Subject: Sync is painfully slow for our design files
>
> Hi,
>
> Our team works with Photoshop and Illustrator files that are usually 500MB to 2GB each. Syncing these files takes forever — sometimes 30+ minutes for a single file. Our previous tool (Dropbox) was much faster for large files.
>
> Is there anything we can do to speed this up? We have 45 designers who are losing productivity because of this.
>
> Maya Chen
> Creative Director, DesignStudio

**Expected handling:**
- Category: performance
- Severity: medium
- Key actions: Recommend enabling Delta Sync (Pro feature), check concurrent thread settings, suggest excluding temp files
- Relevant KB: features.md (Delta Sync), troubleshooting.md (Slow Sync Performance), error_codes.md (PERF-001)

---

## Inquiry 5: Desktop Client Crashes

**Customer:** Dev Patel, TechStart Inc (Pro, 22 users)
**Channel:** In-app chat
**Priority:** High

> CloudSync desktop keeps crashing on my machine. It starts up, runs for about 2 minutes, then just disappears from the tray. I'm on macOS Sonoma 14.3 with v4.2.1 of the desktop client. I checked Activity Monitor and it's using 2GB+ of RAM before it dies. I think it might be related to my Projects folder which has a bunch of node_modules directories. Is there a way to exclude those?

**Expected handling:**
- Category: performance
- Severity: high
- Key actions: Confirm PERF-002 (high memory), guide to exclude node_modules via selective sync, suggest updating client
- Relevant KB: error_codes.md (PERF-002), features.md (Selective Sync), troubleshooting.md (Desktop Crashes)

---

## Inquiry 6: Account Billing Issue

**Customer:** Dr. Lisa Wong, GlobalEd Foundation (Pro, 120 users)
**Channel:** Email
**Priority:** Low

> Subject: Payment failed notification
>
> Hello,
>
> We received an email saying our payment failed. Our finance department updated the credit card last week but it seems it didn't go through. We're a non-profit on a discounted plan and really can't afford any disruption. Can you help us sort this out?
>
> Also, could you tell me what happens to our data if the payment issue isn't resolved? We have important research documents stored.
>
> Dr. Lisa Wong
> IT Coordinator, GlobalEd Foundation

**Expected handling:**
- Category: account
- Severity: low
- Key actions: Verify payment method on file, explain 7-day grace period, reassure about data retention (30 days after suspension)
- Relevant KB: account_billing.md (ACCT-001, ACCT-003), plan_matrix.md (Billing FAQ)

---

## Inquiry 7: API Rate Limiting

**Customer:** Amanda Torres, Big Retail Co (Enterprise)
**Channel:** Email
**Priority:** Medium

> Subject: Getting 429 errors on API calls
>
> Hi team,
>
> We're seeing intermittent 429 (Too Many Requests) responses from the CloudSync API. We're on Enterprise with a custom rate limit of 8,000 req/min, but during peak hours (6-9am PT) our traffic spikes to about 12,000 req/min. Is it possible to increase our limit? Or is there a batch endpoint we can use to reduce the number of individual calls?
>
> Amanda Torres
> DevOps Lead, Big Retail Co

**Expected handling:**
- Category: api
- Severity: medium
- Key actions: Review current rate limit, discuss batch endpoints, consider rate limit increase
- Relevant KB: error_codes.md (API-001), features.md (Webhooks — batch alternative), runbooks.md (API Integration)

---

## Inquiry 8: Permission Denied After Role Change

**Customer:** Unknown (via in-app chat, Acme Corp workspace)
**Channel:** In-app chat
**Priority:** Medium

> I was able to edit files in the Marketing shared folder until yesterday. Now I get "Permission Denied" every time I try to save. My manager said nothing changed. Error code AUTH-002. Can someone look into this?

**Expected handling:**
- Category: permission
- Severity: medium
- Key actions: Check if user role was changed, verify folder sharing settings with owner/admin
- Relevant KB: error_codes.md (AUTH-002), faq.md (folder sharing), troubleshooting.md (Permission Denied)

---

## Inquiry 9: Data Loss Scare

**Customer:** Maya Chen, DesignStudio (Pro, 45 users)
**Channel:** Email (urgent)
**Priority:** Critical

> Subject: URGENT — Files missing from shared Team Space!!!
>
> Several of our designers are reporting that files are missing from the "Client Projects Q1" team space. These are active project files that we need for client deliverables THIS WEEK. Approximately 50-60 PSD and AI files seem to have disappeared overnight.
>
> Please help us recover these files immediately. This is a business-critical emergency for us.
>
> Maya Chen

**Expected handling:**
- Category: sync
- Severity: critical
- Key actions: Follow Data Loss runbook, check CloudSync Trash, check audit log for deletions, reassure about recovery
- Relevant KB: runbooks.md (Data Loss), faq.md (file deletion/trash), features.md (Audit Log — limited on Pro)

---

## Inquiry 10: Feature Question — SSO on Pro Plan

**Customer:** Dr. Lisa Wong, GlobalEd Foundation (Pro, 120 users)
**Channel:** Email
**Priority:** Low

> Subject: SSO availability
>
> Hi,
>
> Our users keep forgetting their passwords and it creates a lot of support tickets on our side. We'd love to set up SSO with Google Workspace so they can log in with their school accounts. Is SSO available on the Pro plan, or is it Enterprise only? If Enterprise, is there a non-profit discount available?
>
> Dr. Lisa Wong

**Expected handling:**
- Category: feature
- Severity: low
- Key actions: Confirm SSO is Enterprise-only, suggest contacting sales for non-profit Enterprise pricing
- Relevant KB: plan_matrix.md (SSO — Enterprise only), sso_guide.md (overview), faq.md (2FA as alternative)
