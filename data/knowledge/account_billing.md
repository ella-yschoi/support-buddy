---
title: Account & Billing Error Reference
category: error_code
---

## ACCT-001: Payment Failed

Recurring subscription payment could not be processed.

**Common causes:**
- Credit card expired or declined
- Insufficient funds
- Payment provider outage
- Card flagged for fraud by issuing bank

**Resolution:**
1. Go to Dashboard > Account > Billing
2. Click "Update Payment Method" and enter new card details
3. Click "Retry Payment"
4. If the issue persists, ask the customer to contact their bank
5. Grace period: 7 days before account downgrade

## ACCT-002: Plan Limit Reached

User attempted an action that exceeds their current plan's limits.

**Common causes:**
- Storage quota exceeded (Free: 5GB, Pro: 1TB, Enterprise: unlimited)
- Device limit reached (Free: 3, Pro: 10, Enterprise: unlimited)
- Team member limit reached (Free: 1, Pro: 25, Enterprise: unlimited)

**Resolution:**
1. Check current usage: Dashboard > Account > Usage
2. Delete unused files or devices to free up capacity
3. Upgrade plan: Dashboard > Account > Plans > "Upgrade"
4. For Enterprise custom limits, contact the sales team

## ACCT-003: Account Suspended

The account has been suspended and all sync operations are paused.

**Common causes:**
- Payment overdue beyond 14-day grace period
- Terms of Service violation detected
- Admin-initiated suspension (Enterprise)
- Unusual activity flagged by security system

**Resolution:**
1. Check suspension reason: login page will display the reason
2. For payment issues: update payment method and pay outstanding balance
3. For ToS violations: review the notification email and contact support
4. For admin suspensions: contact the workspace administrator
5. Data is preserved for 30 days after suspension

## ACCT-004: Account Merge Conflict

Attempting to merge two accounts that have conflicting data or settings.

**Common causes:**
- User signed up with both email and SSO, creating duplicate accounts
- Company acquisition merging two CloudSync workspaces
- User changed email address and lost access to original account

**Resolution:**
1. Verify ownership of both accounts (email verification required for each)
2. Choose the primary account to keep
3. Contact support with both account emails for manual merge
4. Data from the secondary account will be moved to the primary
5. Merge typically completes within 24 hours

## ACCT-005: Trial Expired

Free trial period has ended and the account has been downgraded.

**Common causes:**
- 14-day trial period elapsed without converting to a paid plan
- Trial extension request was not approved

**Resolution:**
1. Go to Dashboard > Account > Plans
2. Select a plan and enter payment details
3. All data from the trial period is preserved for 30 days after expiration
4. If more trial time is needed, contact sales for a one-time 7-day extension
