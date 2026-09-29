# Authentication and Login Troubleshooting

This guide covers sign-in problems for the Acme Cloud dashboard, including passwords,
single sign-on (SSO), multi-factor authentication (MFA) and session expiry.

## Password resets

Users can reset their password from the login page by clicking **Forgot password**.
A reset link is sent to the account email address and expires after **30 minutes**.
Only the most recent reset link is valid; requesting a new link invalidates older ones.

If the reset email does not arrive:

1. Ask the user to check spam or quarantine folders.
2. Confirm the email address on the account matches the address they typed.
3. Corporate mail filters sometimes block `no-reply@acme-cloud.dev`. Ask their IT team to allowlist it.

## Account lockout

After **5 failed login attempts** within 15 minutes the account is temporarily locked for
15 minutes. The lock clears automatically. Support agents can clear a lock early from the
admin console under **Users → Security → Clear lockout**.

## Multi-factor authentication (MFA)

Acme Cloud supports TOTP authenticator apps. Common MFA issues:

- **Invalid code**: TOTP codes depend on the device clock. Ask the user to enable automatic
  time synchronisation on their phone.
- **Lost device**: the user can sign in with one of the 10 recovery codes generated during setup.
  If recovery codes are lost, an account owner must reset MFA for that user. Identity must be
  verified before support resets MFA.

## Single sign-on (SSO / SAML)

SSO errors usually come from configuration mismatches between Acme Cloud and the identity provider.

- `SAML_RESPONSE_EXPIRED`: the identity provider clock is skewed by more than 3 minutes.
- `INVALID_AUDIENCE`: the Audience URI in the identity provider must be exactly
  `https://app.acme-cloud.dev/saml/metadata`.
- `USER_NOT_PROVISIONED`: just-in-time provisioning is disabled and the user has not been invited.

After changing the SSO configuration, users must sign out fully and sign in again.

## Session expiry

Dashboard sessions expire after 12 hours of inactivity. Users who are logged out repeatedly
within minutes usually have third-party cookies blocked or a browser extension clearing cookies.
Ask for the browser name and version and whether the issue happens in a private window.

## Information to collect

When a login issue cannot be resolved with the steps above, collect:

- the exact error message or error code shown
- timestamp of the failed attempt (with timezone)
- browser and version
- whether SSO or password login is used
