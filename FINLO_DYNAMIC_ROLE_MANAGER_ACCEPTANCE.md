# FINLO Dynamic Role Manager Acceptance

## Backend results

**PASS** — isolated tests cover role listing/rendering, allow/deny/default decisions, custom scopes, write authorization, protected built-in restrictions, custom-role deletion rules, and post-change permission visibility.

The previously introduced permission snapshot optimization now uses a version invalidated by `Role.permissions` and `Role.denied_permissions` many-to-many signals. The regression test `test_role_permission_changes_are_visible_to_other_loaded_users` passed.

## Security results

**PASS** — tests cover company isolation, role-assignment authority, protected hierarchy behavior, recovery permissions, and prevention of privilege expansion through ordinary sales roles.

## Browser workflow

**BLOCKED** — the available browser tab was authenticated as ASM and the browser connector could not create an isolated Super Admin/staging tab. No live role mutations were attempted.

## Defect classification

The sales-role permission ceilings are mandatory hierarchy/data-scope rules, not a confirmed Dynamic Role Manager defect. Editable feature permissions apply where `role_permission_grant_allowed()` permits them; mandatory ownership and recovery restrictions remain enforced.
