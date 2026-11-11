# FINLO Six-Role Acceptance Matrix

| Requirement | Status | Evidence |
|---|---|---|
| Six protected identities exist | PASS | Existing authorization fixtures and live-state audit identify the six canonical system keys |
| Parent chain is unchanged | PASS | Role model `clean()`/`save()` protections and authorization tests pass |
| Built-in roles cannot be deleted | PASS | Authorization tests pass |
| System keys cannot be modified | PASS | Role model protection tests pass |
| Protected parents cannot be modified | PASS | Role hierarchy tests pass |
| Company boundaries remain enforced | PASS | Company-scoped API/queryset tests pass |
| Manager/subordinate visibility | PASS | Sales authorization tests pass |
| BDO assignment rules | PASS | Existing sales-role ceiling tests pass |
| Browser acceptance for all six roles | BLOCKED | No disposable browser/staging fixture was available |

Dynamic allow/deny/default behavior for all six built-in roles is covered by the isolated test `test_explicit_role_grants_and_denials_apply_to_all_six_builtin_roles`. Hard-coded sales ceilings remain intentional mandatory restrictions and are not treated as configurable feature grants.
