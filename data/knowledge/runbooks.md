---
title: Support Runbooks
category: runbook
---

## Runbook: Customer Reports Data Loss

**Priority:** CRITICAL
**SLA:** Respond within 1 hour, resolve within 4 hours

**Immediate Actions:**
1. Acknowledge the customer's concern immediately
2. Ask: What files/folders are missing? When did you last see them?
3. Check CloudSync Trash (files may be in the 30/90-day retention)
4. Check the audit log: Admin > Audit Log > filter by user and date range
5. Check if another user deleted or moved the files (shared folders)

**Escalation Criteria:**
- If files are not in Trash and audit log shows no user action → Escalate to Engineering (P1)
- If audit log shows unexpected deletions by the system → Escalate to Engineering (P1)

**Customer Communication:**
- Do NOT say "data is lost" until confirmed by Engineering
- Reassure the customer that we have multiple backup layers
- Provide timeline for investigation

## Runbook: SSO Login Failure for Entire Organization

**Priority:** HIGH
**SLA:** Respond within 2 hours, resolve within 8 hours

**Immediate Actions:**
1. Confirm scope: Is it all users or specific users?
2. Check CloudSync system status: https://status.cloudsync.io
3. Ask for the SSO provider (Okta, Azure AD, Google Workspace, etc.)
4. Check if the SAML certificate recently expired
5. Test SSO flow with SAML tracer (browser extension)

**Common Fixes:**
- Expired certificate → Customer updates certificate in IdP and CloudSync admin
- IdP outage → Wait for IdP recovery, suggest direct login as temporary workaround
- Configuration change → Revert recent changes in Admin > SSO

## Runbook: API Integration Failures

**Priority:** MEDIUM-HIGH
**SLA:** Respond within 4 hours

**Immediate Actions:**
1. Ask: What API endpoint? What error code/message? When did it start?
2. Check API status: https://status.cloudsync.io/api
3. Verify the customer's API key is valid and not expired
4. Check rate limit status: GET /api/v1/rate-limit-status
5. Test the endpoint with the customer's parameters

**Diagnostic Questions:**
- Did anything change recently? (new deployment, key rotation, etc.)
- Is it intermittent or consistent?
- What's the full request/response? (redact auth headers)

## Runbook: Performance Degradation Report

**Priority:** MEDIUM
**SLA:** Respond within 4 hours

**Immediate Actions:**
1. Ask: What is slow? (sync, web dashboard, API, desktop client)
2. Get specifics: How slow? What's normal vs. current?
3. Check system status page for known issues
4. Ask for the client version and OS

**For Sync Performance:**
1. Check file count and sizes being synced
2. Check concurrent thread setting
3. Check for PERF-001 or PERF-002 errors
4. Ask for a network speed test result

**For Web Dashboard:**
1. Check browser (Chrome/Firefox/Edge recommended)
2. Check if loading is slow for all pages or specific ones
3. Ask the customer to try incognito mode
4. Check if they have browser extensions that may interfere
