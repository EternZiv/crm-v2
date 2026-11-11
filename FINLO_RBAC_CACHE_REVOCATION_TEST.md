# FINLO RBAC Cache and Revocation Test

## Request-side authorization cache

**PASS** — batched role grants/denials are cached on the loaded user object and invalidated through a process-wide permission version when role permission many-to-many relations change. The post-change visibility regression test passed.

## Browser-side cache

**BLOCKED** — FinloViewCache remains tab-local/in-memory. Cross-session browser revocation, stale-menu behavior, and multiple-tab refresh were not safely executable because the browser connector could not create an isolated session. Browser cache is not treated as an authorization boundary; every backend request still evaluates permissions.

## Required follow-up

Validate session A grant/revoke against session B in a disposable staging environment. If stale privileged menus remain visible after revocation, add a minimal policy-version check to navigation invalidation; do not rely on hidden buttons for security.
