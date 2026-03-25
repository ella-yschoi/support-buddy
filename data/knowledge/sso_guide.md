---
title: SSO Setup & Configuration Guide
category: troubleshooting
---

## SSO Overview

CloudSync supports SAML 2.0 Single Sign-On for Enterprise plans. SSO allows organization members to log in using their corporate identity provider (IdP).

**Supported IdPs:**
- Okta
- Azure Active Directory (Entra ID)
- Google Workspace
- OneLogin
- PingIdentity
- Any SAML 2.0 compliant provider

**Requirements:**
- Enterprise plan
- Admin access to both CloudSync and the IdP
- HTTPS endpoint for Assertion Consumer Service (ACS)

## Setting Up SSO with Okta

1. In Okta Admin: Applications > Create App Integration > SAML 2.0
2. Set the following values:
   - Single Sign-On URL: `https://app.cloudsync.io/sso/saml/callback`
   - Audience URI: `https://app.cloudsync.io/sso/saml/metadata`
   - Name ID format: `EmailAddress`
3. Map attributes:
   - `email` -> `user.email`
   - `firstName` -> `user.firstName`
   - `lastName` -> `user.lastName`
4. Download the IdP metadata XML
5. In CloudSync Admin > Security > SSO:
   - Upload the IdP metadata XML
   - Set "SSO Mode" to "Optional" for testing, "Required" after verification
   - Click "Save & Test"

## Setting Up SSO with Azure AD

1. In Azure Portal: Enterprise Applications > New Application > CloudSync
2. Single sign-on > SAML:
   - Identifier (Entity ID): `https://app.cloudsync.io/sso/saml/metadata`
   - Reply URL (ACS): `https://app.cloudsync.io/sso/saml/callback`
3. Attributes & Claims: map email, givenname, surname
4. Download Federation Metadata XML
5. Upload to CloudSync Admin > Security > SSO
6. Set SSO Mode and test

## Setting Up SSO with Google Workspace

1. In Google Admin: Apps > Web and mobile apps > Add App > Search for CloudSync
2. If not in catalog, choose "Add custom SAML app"
3. Configure:
   - ACS URL: `https://app.cloudsync.io/sso/saml/callback`
   - Entity ID: `https://app.cloudsync.io/sso/saml/metadata`
   - Name ID: Basic Information > Primary email
4. Download IdP metadata
5. Upload to CloudSync Admin > Security > SSO
6. Enable for target organizational units in Google Admin

## SSO Troubleshooting Checklist

**When SSO login fails, check these in order:**

1. **Certificate validity:** Is the SAML signing certificate expired? Certificates typically expire every 1-3 years. Check expiry in IdP settings.
2. **ACS URL:** Does the Reply URL in the IdP match exactly `https://app.cloudsync.io/sso/saml/callback`? Trailing slashes matter.
3. **Entity ID:** Must match exactly `https://app.cloudsync.io/sso/saml/metadata` in both IdP and CloudSync.
4. **Attribute mapping:** `email`, `firstName`, and `lastName` are all required. Missing any one causes AUTH-003.
5. **Clock skew:** Server time difference >5 minutes between IdP and CloudSync causes assertion expiry. Check NTP sync.
6. **User provisioning:** Is the user assigned to the CloudSync application in the IdP?
7. **Network:** Can CloudSync servers reach the IdP metadata URL? Firewall rules may block outbound access.

**Useful diagnostic tool:** Install the "SAML Tracer" browser extension to capture and inspect the SAML request/response flow.

## SSO Session Management

- Default session duration: 8 hours (configurable by admin, range: 1-72 hours)
- Session is tied to IdP session - if IdP session expires, CloudSync re-authenticates via IdP
- Admin can revoke all SSO sessions: Admin > Security > Active Sessions > "Revoke All"
- When SSO is set to "Required", password-based login is disabled for all non-admin users
- Break-glass: workspace Owner can always log in with email/password even when SSO is required
