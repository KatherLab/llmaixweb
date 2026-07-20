# Single sign-on (SSO)

**Single Sign-On (OIDC)** (`/admin/sso`) manages OpenID Connect identity
providers (Google, Keycloak, Azure AD, and any OIDC-compliant provider).

!!! note "Enable SSO globally first"
    SSO must be enabled in [system settings](settings.md) (**SSO Enabled**). When
    it's off, the page shows a reminder.

## Adding a provider

**Add provider** opens a form:

- **Display name** — the label users see (e.g. "Google").
- **Issuer URL** — the provider's base URL; the app discovers its configuration
  from `{issuer}/.well-known/openid-configuration`.
- **Client ID** and **Client secret** — from the provider (the secret is stored
  encrypted; on edit, leave it blank to keep the current one).
- **Scopes** — default `openid email profile`.
- **Enabled** — whether the provider is live.

Each provider row shows its status and configuration, with **Edit** and
**Delete**. Deleting a provider keeps linked users' accounts but stops them
signing in through it.

## How sign-in works

The login flow uses PKCE and a short-lived signed state, with the redirect URI
derived from the app's configured URL. On first sign-in, users are
**provisioned just-in-time**: linked to an existing identity, matched to an
existing account by email, or created new — governed by settings such as whether
a verified email is required, whether an invitation is required, and the default
role for new SSO users. SSO-only users have no password until they set one on the
[account settings](../user-guide/account.md) page.
