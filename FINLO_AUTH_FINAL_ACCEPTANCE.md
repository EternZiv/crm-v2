# FINLONEXA CRM v2 — Authentication Final Acceptance

Date: 2026-11-14

## Summary

Authentication code and isolated HTTP acceptance checks are in good shape, but final production acceptance is **NO-GO** while browser, shared Redis, real email delivery, and authenticated Channels runtime checks remain blocked. No live account, credential, role, permission, CRM record, production setting, or database schema was changed during this acceptance pass.

## Gate status

| Gate | Status | Evidence / limitation |
|---|---|---|
| Git history and repository safety | **PASS with attribution unknown** | Reflog and commit metadata inspected. Both named commits are on `main`; remote tracking reflog records `origin/main` updates by push. No history was rewritten in this task. |
| Secret/credential review of named commits | **PASS (heuristic scan)** | Focused diff scan found no credential-signature matches and no secret-like or `.env` paths. A pattern scan cannot guarantee that arbitrary sensitive values are absent. No secret values were printed. |
| Authentication HTTP acceptance | **PASS** | 3 focused isolated tests passed; details below. |
| Existing authentication hardening tests | **PASS (prior result)** | Previously reported 18/18 focused authentication tests passed. Not rerun during this acceptance pass. |
| Authorization / role and company isolation | **PASS (prior result)** | Previously reported 31/31 isolated authorization tests passed, covering six built-in roles, custom permissions, company scoping, IDOR boundaries, and permission changes. Not rerun because this task did not change authorization code. |
| Browser logout/cache/history acceptance | **BLOCKED** | No isolated authenticated browser identity was available. The active browser session was not logged out or modified. |
| Password reset delivery | **PASS locally / BLOCKED externally** | Reset and single-use token behavior passed with Django's in-memory email backend. No real mailbox delivery was attempted. |
| Cross-worker Redis throttling | **BLOCKED** | Tests use isolated in-memory SQLite and local-memory cache. No dedicated disposable Redis instance was confirmed; shared Upstash was not used. |
| Trusted proxy IP behavior | **PASS at application boundary / BLOCKED in deployment** | Focused test confirms the limiter uses `REMOTE_ADDR` and ignores an untrusted raw `X-Forwarded-For`. Vercel/proxy normalization was not exercised. |
| Django Channels session authentication | **BLOCKED at runtime** | Static ASGI path wraps WebSocket routes in `AuthMiddlewareStack`; notification consumer rejects anonymous users. An isolated communicator attempt hung and was stopped. No live server or session was touched. |
| Production readiness | **NO-GO** | Runtime/browser and infrastructure acceptance gates above remain open. |

## Git history findings

The current branch and remote-tracking branch point to `6a14cb2b`.

- `deb1f3cb7bc3034a82539f21a8aef8e965bfbc1f` — authored and committed as `Antigravity Engineer <engineer@antigravity.local>` at 2026-11-14 00:08:55 +05:00. Subject: `fix(security): enforce POST logout, password reset host validation, and credential sanitization`.
- `6a14cb2b5afc5589fab578aee214baa3071c13a5` — same author/committer at 2026-11-14 00:13:35 +05:00. Subject: `fix(auth): add autocomplete to user creation form and clean unused imports`.

The local reflog records both as commit events. The `origin/main` reflog records `update by push` at 00:09:05 and 00:13:45 respectively. The repository's configured Git identity matches the commit metadata. The checked-in hooks directory contains only Git sample hooks, and no custom `core.hooksPath` was configured. This evidence confirms that pushes updated the remote-tracking ref, but Git metadata does **not** identify the person, IDE, agent, or process that initiated a commit or push. A process-level attribution could not be established; the process inspection attempted earlier was denied by Windows access controls. The Antigravity identity makes IDE/agent automation plausible, but that remains an inference.

The two commits modify authentication-related views, templates, the user form/model, navigation cache cleanup, and focused tests. No `.env` or obvious credential file appears in their changed paths. An adjacent commit `a9174580` has an image-removal subject but also changes authentication paths; this is a title/scope mismatch worth reviewing separately. No commit, push, revert, reset, amend, or history rewrite was performed for this task.

## Runtime evidence

### Isolated HTTP acceptance

Command:

```powershell
.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_auth_final_acceptance --settings=finlo.settings.security_test --verbosity=2
```

Result: **3 tests passed** in 36.878 seconds; Django system checks reported no issues. The runner created an in-memory SQLite test database, applied migrations only to that temporary database, and destroyed it after the run.

Covered flows:

1. Valid login, session-key rotation, invalid credentials, inactive account denial, and protected URL behavior after session expiration.
2. GET logout rejection, missing-CSRF POST rejection, valid CSRF POST logout, and protected URL redirect after logout.
3. New passwordless user has unusable credentials; a locally captured reset email enables password setup; the reset token cannot be reused.

The local email backend verifies token flow and message generation only; it does not prove SMTP/provider delivery. These fixture identities were created only inside the ephemeral SQLite test database.

### Previously completed focused suites

- Authentication hardening and login availability: **18/18 passed** (prior verified result; not rerun here).
- Isolated authorization suite: **31/31 passed** (prior verified result; not rerun here). Those tests provide the role hierarchy, company isolation, and permission-revocation evidence for this code state. No authorization implementation was changed in this task.
- A focused trusted-proxy limiter test passed (prior result): raw `X-Forwarded-For` does not override `REMOTE_ADDR`.

### Browser, Redis, email, and Channels

No active server was restarted and no authenticated browser session was disturbed. Browser Back/Forward after logout, FinloViewCache/HTMX history cleanup, and protected-page restoration therefore remain **BLOCKED** for runtime acceptance. Redis cross-worker behavior remains **BLOCKED** because only local-memory cache was available in the safe test configuration. Real reset-email delivery remains **BLOCKED**. Channels middleware and anonymous-consumer rejection were reviewed statically, but authenticated WebSocket handshake and logout/session-revocation behavior remain **BLOCKED**; the isolated communicator attempt did not complete.

## Files and worktree

No production authentication source changes were made during this final acceptance pass. The focused test module `finlo/contrib/core/test_auth_final_acceptance.py` was added to exercise disposable HTTP authentication flows. Existing user changes remain present; this task did not revert or overwrite them. Current known modified/untracked paths include:

- `finlo/contrib/core/management/commands/create_finlo_user.py`
- `finlo/contrib/core/test_auth_hardening.py`
- `finlo/contrib/core/views/core.py`
- `finlo/contrib/core/views/forgot_password.py`
- `FINLO_AUTH_SECURITY_HARDENING_RESULTS.md`
- `finlo/contrib/core/test_auth_final_acceptance.py`
- `FINLO_AUTH_FINAL_ACCEPTANCE.md` (this report)

Review the worktree before any later commit. No commit or push was created by this task.

## Remaining blockers and next safe steps

1. Use a dedicated isolated browser context and disposable identity to verify login, navigation, logout, Back/Forward, cache clearing, and post-expiry protected URLs.
2. Run cross-worker throttle checks against a dedicated disposable Redis service; do not use a shared production Redis instance for test state.
3. Verify provider email delivery using a controlled test mailbox and non-production configuration.
4. Complete authenticated Channels handshake, authorization, disconnect, and session invalidation checks in an isolated ASGI runtime.
5. Verify trusted proxy normalization in the actual deployment topology before relying on client-IP rate limits there.
6. Review commit `a9174580`'s authentication-related changes against its commit subject and confirm the origin push history with the person/team that owns the IDE automation. Git metadata alone cannot identify the actor.

Until these gates pass, keep authentication deployment status **NO-GO** rather than treating isolated Django tests as full production acceptance.
