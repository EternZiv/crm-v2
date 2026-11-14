# FINLONEXA CRM v2 — Single Superadmin Setup Plan

**Document Status:** PENDING ADMINISTRATOR APPROVAL (PHASE 7 CHECKPOINT)  
**Date:** November 14, 2026  
**Target Identity:** `superadmin` (User ID 33)  
**Canonical Role:** `SUPER_ADMIN` (Role ID 7)  
**Primary Company:** `FINLONEXA UAT` (Company ID 3)  
**Framework:** Django 6.0 / FINLO Dynamic Role Manager / Custom FinloUser  

---

## 1. Objective & Architecture

This plan establishes a single, fully privileged human administrator account (`superadmin`) to serve as the master authority for **FINLONEXA CRM v2**.

After executing this plan:
1. `superadmin` will be the **only active human account** in the system.
2. The account will possess full Django superuser/staff privileges and FINLO `SUPER_ADMIN` role authority.
3. The account will have verified capability to create and manage companies, regions, teams, roles, users, and all CRM business modules.
4. The account will be verified and operational before any legacy test accounts are removed.

---

## 2. Superadmin Account Specification

### 2.1 Account Reconciliation Strategy
The database already contains a pre-staged user record for `superadmin` at **User ID 33**. Reconciling this existing record is strongly preferred over dropping and recreating, as it maintains primary key stability and avoids sequence fragmentation.

| Attribute | Current Value | Target Reconciled Value | Compliance Check |
| :--- | :--- | :--- | :--- |
| **User ID** | `33` | `33` | Reconciled existing record |
| **Username** | `superadmin` | `superadmin` | Matches canonical requirement |
| **Active Status** | `False` | `True` | Enabled for login |
| **Staff Status** | `True` | `True` | Django admin access enabled |
| **Superuser Status** | `True` | `True` | Root Django authority |
| **FINLO Role** | `None` | `Role ID 7` (`SUPER_ADMIN`) | Full FINLO RBAC authority (883 permissions) |
| **Company Association** | `FINLONEXA UAT` (ID: 3) | `FINLONEXA UAT` (ID: 3) | Required multi-tenant tenant link |
| **Email Address** | `superadmin@example.invalid` | *Administrator-Approved Address* | Real recovery email supplied by administrator |
| **Password** | Stale test hash | Fresh Django PBKDF2 SHA-256 | Configured via interactive CLI |

---

## 3. Administrative Capability Verification Matrix

Django's `is_superuser = True` alone does not guarantee access in FINLO, because FINLO employs custom multi-tenant decorators, company-scoping middleware, and the Dynamic Role Manager. The superadmin must be verified against all 6 administrative domains:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      FINLO SUPERADMIN AUTHORITY                        │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ 1. Company Admin  │ 2. Org & Sales    │ 3. User Administration         │
│ • Create Company  │ • Sales Regions   │ • Create / Edit Users          │
│ • Edit Company    │ • Sales Teams     │ • Activate / Deactivate        │
│ • Settings        │ • Sales Hierarchy │ • Role & Company Assignment    │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 4. Role & RBAC    │ 5. CRM Domain     │ 6. System & MCP                │
│ • Dynamic Roles   │ • Full CRUD Leads │ • FINLO Settings               │
│ • Field Perms     │ • Opps / Accounts │ • Dynamic Metadata             │
│ • Module Perms    │ • Activities/Logs │ • Connect MCP & Data Scopes    │
└───────────────────┴───────────────────┴────────────────────────────────┘
```

### Area 1: Company Administration
- **Capabilities:** Create new operating companies, view multi-company listings, update company profiles, configure company-specific default currencies and fiscal years.
- **Verification Path:** Access `/company/` and `/company/create/` endpoints; verify company scoping bypass for `SUPER_ADMIN`.

### Area 2: Organization & Sales Hierarchy Administration
- **Capabilities:** Create and manage Sales Regions (`core_salesregion`), define Sales Teams (`core_salesteam`), configure sales hierarchy reporting trees (SSM → ASM → BDO), and assign territory managers.
- **Verification Path:** Access `/settings/organization/` and sales assignment workflows.

### Area 3: User Administration
- **Capabilities:** Create human user accounts, update profile details, activate and deactivate users, trigger secure password resets, and assign/revoke company and role memberships.
- **Verification Path:** Access `/user/` user management views and invitation flows.

### Area 4: Role and Security Administration
- **Capabilities:** Create custom roles via the Dynamic Role Manager, modify module-level permissions, enforce field-level restrictions (`FieldPermission`), and manage record access rules.
- **Verification Path:** Access `/settings/roles/` and permission matrix editors.

### Area 5: CRM Domain Administration
- **Capabilities:** Full Create, Read, Update, and Delete access across all core modules:
  - Leads (`leads.Lead`)
  - Opportunities (`opportunities.Opportunity`)
  - Accounts (`accounts.Account`)
  - Contacts (`contacts.Contact`)
  - Activities, Calls, Meetings, Tasks (`activity.Activity`)
  - Campaigns (`campaigns.Campaign`)
  - Dashboards and Reports (`dashboard.Dashboard`, `reports.Report`)
- **Verification Path:** Verify model managers return full company scope without hierarchy filtering.

### Area 6: System Administration & MCP Integration
- **Capabilities:** Configure global system settings, customize color themes, manage dynamic fields and forms, inspect system audit logs, and administer MCP tool connections.
- **Verification Path:** Verify `/settings/` root, `/settings/mcp/`, and `finlo/contrib/core/mcp_data_service.py` scope evaluation.

---

## 4. Secure Password Configuration Procedure

To prevent security risks and comply with zero-credential leakage rules:

1. **No Hardcoded Passwords:** No default or temporary passwords will ever be written to disk, committed to Git, or output in command logs.
2. **Interactive Administrator Setup:** Upon Phase 7 approval, the password will be set via Django's interactive management command or a secure script that reads directly from the terminal:
   ```powershell
   .venv\Scripts\python.exe manage.py changepassword superadmin
   ```
3. **Cryptographic Standard:** Uses Django 6's standard `PBKDF2PasswordHasher` with SHA-256 and 1,200,000 hashing rounds.
4. **Fallback Safety:** If interactive input cannot be provided during automated batch execution, the account will be initialized with `set_unusable_password()` until the administrator performs the first password set via CLI.

---

## 5. Recovery Safety & Safe Cutover Sequence

> [!CAUTION]
> Under no circumstances will legacy test accounts (`test_superadmin`, `hafiz`, etc.) be deleted before the `superadmin` account is fully verified and confirmed functional.

### Cutover Verification Sequence:
1. **Reconciliation:** Update User ID 33 (`is_active = True`, `role_id = 7`, `email = <approved_email>`).
2. **Password Verification:** Set password and execute programmatic authentication test:
   ```python
   user = authenticate(username='superadmin', password=...)
   assert user is not None and user.is_active and user.is_superuser
   ```
3. **Session Verification:** Generate test session and verify access to authenticated CRM views.
4. **Administrative Handoff:** Confirm password recovery token generation succeeds for the approved email address.
5. **Reassign Protected Objects:**
   - Reassign `Company 3` (`created_by_id = 33`, `updated_by_id = 33`).
   - Reassign `SalesTeam 1` (`senior_sales_manager_id = 33`, `area_sales_manager_id = None`).
   - Reassign `Dashboard 2` (`dashboard_owner_id = 33`).
   - Reassign `ReportFolder 3` and `Report 2, 3` (`report_owner_id = 33`).
6. **Purge Approved Test Accounts:** Once steps 1–5 are 100% verified, remove test user accounts (IDs 1, 3, 4, 5, 6, 7, 8, 34, 35).

---

## 6. Service Account Policy: `Horilla Bot` (User ID 2)

### Technical Analysis:
- `Horilla Bot` is FINLO's built-in system identity used for automated background tasks, bot notifications, and default foreign key assignments.
- Keeping `Horilla Bot` in the database does not pose a human login risk because it has no human credentials.
- **Recommended Configuration:**
  - `is_active = True`
  - `is_staff = False`
  - `is_superuser = False`
  - Password set to unusable: `user.set_unusable_password()`
  - Retained strictly as an internal non-interactive service bot.

### Alternative Option:
- If the administrator insists on literally ONE row in `core_horillauser`, all foreign keys pointing to User 2 will be reassigned to User 33 (`superadmin`), and User 2 will be deleted.  
*(This choice is presented to the administrator at the Phase 7 checkpoint).*

---

## 7. Plan Status

- **Status:** `NEEDS APPROVAL`
- **Execution Gate:** Phase 8 execution is strictly blocked pending explicit confirmation of checkpoint items.

