# FINLO Authentication Security Hardening Results

Date: 2026-11-14

## Summary

The focused hardening changes below preserve Django session authentication and the existing CRM authorization system. Automated checks passed, including the isolated authorization suite. Production readiness is **NO-GO** until Redis/email delivery and browser/logout acceptance are verified in an approved staging environment.

## Results by area

| Area | Status | Evidence / remaining gate |
|---|---|---|
| User password creation | PASS | New `FinloUser` records without an explicit password now receive an unusable password. Existing password values and explicit hashes remain unchanged. No migration was needed. |
| Activation/password setup | BLOCKED | Passwordless accounts can complete setup through Django's email reset flow. Automatic activation email delivery is not enabled or tested; verify the mail configuration and user-facing activation instructions before using passwordless creation operationally. |
| Login and throttling | PASS (focused code tests); BLOCKED (Redis runtime) | Uses fixed-window shared-cache counters: 20 failed attempts per normalized username/IP pair and 60 per `REMOTE_ADDR` in 15 minutes. This avoids a global username lockout that could block a user from other networks. Tests cover throttled rejection before password verification, same response for unknown/inactive users, non-PII cache keys and fail-closed cache errors. Verify the deployed proxy supplies an appropriate `REMOTE_ADDR` and that Vercel Redis is reachable. |
| Password reset | PASS (focused tests); BLOCKED (email runtime) | Reset requests are throttled to 5 per identifier/IP pair and 20 per `REMOTE_ADDR` per hour. Production reset URLs require `SITE_URL` to be HTTPS and allowlisted. Token timeout is explicitly 24 hours to match email copy. Password values are no longer reflected in reset form HTML. No real email was sent. |
| Logout and CSRF | PASS (focused middleware tests); BLOCKED (browser) | Logout is POST-only; GET returns 405. The header uses a CSRF-protected form. Client-side FinloViewCache and HTMX history entries are cleared on logout submission. Browser Back/protected-route behavior after logout was not exercised. |
| Session configuration | PASS (configuration review) | Django defaults remain in use for session engine/lifetime: database-backed sessions, 14-day age, `SESSION_SAVE_EVERY_REQUEST=False`, HttpOnly session cookie and `SameSite=Lax`. Production/Vercel settings set Secure cookies and HTTPS proxy handling. No live sessions were invalidated. |
| RBAC and company scope | PASS (regression suite) | `finlo.contrib.core.test_authorization`: 31 tests passed on isolated SQLite. No permission or role code was changed. |
| Browser flow | BLOCKED | No isolated browser identity was available. Existing authenticated sessions were not logged out or altered. |
| MFA | NOT TESTED / NOT IMPLEMENTED | No MFA was added or enabled. See recommendation below. |

## Changes made

- `finlo/contrib/core/models/user.py`: removed phone-derived password behavior; new passwordless users receive an unusable password. Existing hashes are not rewritten.
- `finlo/contrib/core/auth_rate_limit.py`: added hashed-key, shared-cache counter helpers.
- `finlo/contrib/core/management/commands/create_finlo_user.py`: require an explicit password and apply Django password validators before creating a superuser.
- `finlo/contrib/core/views/core.py`: added login user/IP throttling, fail-closed cache handling, uniform inactive/invalid login response, and POST-only logout.
- `finlo/contrib/core/views/forgot_password.py`: added reset throttling, allowlisted reset-link origin validation, safer logging, and removed exception detail from invalid-link context.
- `finlo/settings/base.py`: set `PASSWORD_RESET_TIMEOUT` to 24 hours.
- `finlo/contrib/core/forms/users.py`, `templates/login.html`, and `finlo/contrib/core/templates/forgot_password/password_reset_confirm.html`: use appropriate password-manager autocomplete values; reset passwords are not repopulated after validation errors.
- `templates/components/header.html`: changed logout control to a CSRF-protected POST form.
- `static/assets/js/navigation_history.js`: clear protected cache entries when the logout form is submitted.
- `finlo/contrib/core/test_auth_hardening.py`: added database-free focused regression coverage.

## Account creation and recovery design

The multi-step user form does not request a password. Those new accounts now have unusable credentials rather than credentials derived from a phone number. The single-step form and API validate explicitly supplied passwords and use Django's password hashing. The API uses `create_user()`; the dedicated superuser command now rejects missing or policy-weak passwords before database access. Initial setup continues to require an explicit password for the first administrator.

The custom management command's interactive password prompt no longer echoes typed input. Its legacy `--password` option remains for compatibility and can expose the secret in shell history or process listings; do not use that option for production credentials. Prefer the interactive prompt until a secure automation interface is separately approved.

The existing signed Django reset token is used as the password-setup mechanism: possession of the configured email inbox is required to complete setup. Production reset URLs use `SITE_URL`, validated against `ALLOWED_HOSTS`, and require HTTPS. If email delivery or `SITE_URL` is not configured, the endpoint does not send a reset email. Admin-created passwordless accounts must not be treated as ready for use until the owner completes setup.

Existing password hashes cannot reveal whether a password was originally derived from a phone number. Do not test phone-number guesses against live accounts. If historical exposure is suspected, identify the affected cohort from account-creation/audit records where possible and conduct an approved forced-reset campaign without changing passwords automatically.

## Authentication behavior

The application uses `AUTH_USER_MODEL = "core.FinloUser"`. Login posts username/password to `/login/`, uses Django `authenticate()` and `login()`, rejects inactive users, and sanitizes the `next` redirect. No custom `AUTHENTICATION_BACKENDS` setting was found; Django's default backend is therefore active. Username is the authentication identifier; email works only when it is also the stored username.

Base settings use LocMemCache, which is process-local and unsuitable for shared production throttling. Vercel settings configure Redis-backed cache. The Redis provider was not contacted in this verification, so distributed atomic-counter behavior and failure handling are not runtime-accepted. The per-identity counter is scoped to the identity/IP pair to avoid an attacker globally locking out a username; the separate IP quota remains. The limiter trusts only server-provided `REMOTE_ADDR`; deployment operators must confirm trusted proxy normalization rather than reintroducing raw client `X-Forwarded-For` handling.

The login page uses standard Django CSRF protection. Successful login uses Django session APIs. `finlo/asgi.py` wraps WebSocket routes in `AuthMiddlewareStack`, so Channels uses the Django session cookie; WebSocket revocation behavior was not tested in this task.

## Password reset and session notes

- Django's `default_token_generator` remains in use. Its token is invalidated by password/account-state changes; expiry is now explicitly 24 hours.
- Reset request responses remain the same for known and unknown identifiers. Rate limits apply before lookup. Response-time equality was not measured; known accounts require email delivery and may have a distinguishable duration. Asynchronous mail dispatch could reduce this difference if a reliable worker is available.
- Forgot-password visibility depends on mail configuration, and no live delivery test was performed.
- Password changes use Django `set_password()`. The existing change-password view refreshes the current session hash; password reset also calls `update_session_auth_hash()` before redirecting to login. Other sessions should fail Django's session-auth-hash check.
- Session policy was not shortened to avoid changing existing behavior. Consider an explicit inactivity/absolute-lifetime policy as a separately approved product decision.

## Verification

- `finlo.contrib.core.test_auth_hardening` and `finlo.contrib.core.test_login_availability`: **18 passed** after final throttle-scope adjustment.
- `finlo.contrib.core.test_authorization`: **31 passed** using the isolated `security_test` SQLite configuration.
- Python compilation for changed Python modules: **PASS**.
- `node --check static/assets/js/navigation_history.js`: **PASS**.
- Django system checks under the test settings: **PASS**.
- `git diff --check` on relevant paths: **PASS**.
- No migrations, production database writes, live email, account changes, role changes, or session resets were performed.

## MFA recommendation

Plan a separate opt-in MFA rollout for SUPER_ADMIN and HEAD_OF_SALES first. Prefer WebAuthn/passkeys or TOTP, with one-time recovery codes, administrator recovery safeguards, enrollment audit events, rate-limited verification, and encrypted secret storage. Do not make MFA mandatory until recovery and support procedures are tested. This needs an enrollment/recovery data design and an approved rollout; no schema or login-flow dependency was introduced here.

## Repository state and safety note

During this task, Git unexpectedly advanced to commits authored by “Antigravity Engineer”; `main` and `origin/main` both showed the new HEAD. I did not run a commit or push command. I did not rewrite history or attempt a rollback. This was not part of the requested work and should be investigated before any deployment or further push.

## Rollback

No database migration is involved. To roll back the hardening, revert only the listed authentication code/template hunks and the focused tests, preserving unrelated edits. In particular, do not restore whole `core.py`, `login.html`, or `navigation_history.js` files because they contain unrelated existing work. Since Git advanced unexpectedly, do not use `reset --hard`; coordinate any history rollback with the repository owner.
