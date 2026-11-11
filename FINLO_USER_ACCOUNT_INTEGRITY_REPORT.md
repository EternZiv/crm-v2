# FINLO User Account Integrity Report

## Read-only state observed

| Username | Active | Role / privilege note |
|---|---:|---|
| `test_superadmin` | yes | `SUPER_ADMIN` |
| `test_head_sales` | yes | `HEAD_OF_SALES` |
| `test_rsm` | yes | no role assigned |
| `test_ssm` | yes | `SSM` |
| `test_asm` | yes | `ASM` |
| `test_bdo` | yes | `BDO` |
| `test_superuser` | yes | Django superuser + `SUPER_ADMIN` |
| `superadmin` | no | Django superuser, no role |
| `admin` | no | Django superuser, no role |
| `hafiz` | no | inactive |
| `Horilla Bot` | yes | service account |

## Integrity findings

The live account set differs from the supplied test-account table. The mismatch is factual, not silently corrected. In particular, `test_rsm` lacks a role and legacy `superadmin`/`admin` are inactive.

No passwords, activation flags, role assignments, or superuser flags were changed. Any correction should be approved as a separate account-management operation.
