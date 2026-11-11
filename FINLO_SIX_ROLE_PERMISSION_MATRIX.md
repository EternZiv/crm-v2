# FINLO Six-Role Permission Matrix

## Canonical hierarchy observed

| Role | System key | Parent |
|---|---|---|
| Super Admin | `SUPER_ADMIN` | — |
| Head of Sales | `HEAD_OF_SALES` | Super Admin |
| Regional Sales Manager | `RSM` | Head of Sales |
| Senior Sales Manager | `SSM` | Regional Sales Manager |
| Area Sales Manager | `ASM` | Senior Sales Manager |
| Business Development Officer | `BDO` | Area Sales Manager |

The built-in role chain and identity protections are enforced by the `Role` model. Built-in identity and hierarchy edits are rejected.

## Effective access samples

| Account | Role state | Observed result |
|---|---|---|
| `test_superadmin` | active `SUPER_ADMIN` | broad role-manager, account, and core access allowed |
| `test_superuser` | active Django superuser + `SUPER_ADMIN` | broad access allowed |
| `test_asm` | active `ASM` | account view allowed; account delete and role-manager access denied |

Sales-role ceilings and owner-field restrictions remain in force. They prevent ordinary sales roles from receiving unrestricted cross-hierarchy access through the permission UI.

## Account-fixture discrepancy

The requested six-account list does not match the current database exactly: `test_ssm` and `test_bdo` exist instead of `test_sm` and `test_se`; `test_rsm` currently has no assigned role. No account assignments were changed.
