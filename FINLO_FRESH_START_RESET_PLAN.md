# FINLONEXA CRM v2 — Complete Fresh-Start Reset Plan

**Document Status:** PENDING FINAL EXECUTION CONFIRMATION  
**Date:** November 14, 2026  
**Target Environment:** Staging / Pre-Production Supabase Instance  
**Database Host:** `aws-0-ap-south-1.pooler.supabase.com:6543` (Mumbai, `ap-south-1`)  
**Supabase Project Ref:** `ordzcyrzqhdsavfkkouz`  
**Database Name:** `postgres`  
**Django Framework:** Django 6.0 / ASGI Daphne / PostgreSQL 15+  

---

## 1. Executive Summary & Objective

The user has explicitly confirmed that all existing data in FINLONEXA CRM v2 is test/sample data and requested a **complete start from zero**. 

The goal of this operation is to transition the database from its current pre-seeded test state to an authentic **fresh-start production-ready state**:
1. **One Master Superadmin Account:** Reconcile `superadmin` (User ID 33) with full Django superuser and FINLO `SUPER_ADMIN` authority, completely unassigned from the old company (`company = None`), ready to bootstrap the application.
2. **Remove All Old Companies:** Permanently delete `FINLONEXA UAT` (Company ID 3) and all associated test regions, teams, assignments, currencies, and company-specific preferences.
3. **Remove All Transactional CRM Data:** 100% of test Leads, Opportunities, Accounts, Contacts, Activities, Campaigns, Forecasts, attachments, and user sessions safely cleared across all installed modules (including zero-row tables).
4. **Remove All Obsolete Human Accounts:** Purge the 9 test and legacy human accounts (`hafiz`, `test_superadmin`, `test_head_sales`, `test_rsm`, `test_ssm`, `test_asm`, `test_bdo`, `admin`, `test_superuser`).
5. **Preserve the CRM Engine & Global Defaults:** Retain PostgreSQL schemas, migration history, 1,234 system permissions, 162 content types, the 6 canonical sales roles, the 6-stage Lead lifecycle, the pipeline stages, and UI color themes as **global reusable templates**.

---

## 2. Technical Preflight Findings

| Preflight Check | Target Requirement | Audit Outcome |
| :--- | :--- | :--- |
| **Database Identity** | `ordzcyrzqhdsavfkkouz` | PASS — Independently reconfirmed against Supabase Mumbai transaction pooler |
| **New Business Records** | Zero additions since audit | PASS — Confirmed zero new business records across all modules |
| **Database Reachability** | Responsive connection | PASS — Live connection responding normally |
| **Backup Verification** | Complete recoverable backup | PASS — `backups/finlo_full_backup_pre_reset_20261114.json` (1.86 MB, 2,426 objects) verified |
| **Schema Integrity** | All migrations applied | PASS — 100% of migrations applied; 0 unapplied |
| **Local Application Server** | Daphne ASGI server | PASS — Running on `0.0.0.0:8000` |
| **Active Background Jobs** | No background record creators | PASS — Celery/Redis workers paused; no automated mock generators active |

---

## 3. Architecture: Company-Independent Bootstrap Administration

A primary requirement is that `superadmin` must NOT be permanently assigned to `FINLONEXA UAT` and must be able to log in and create the first company when no company exists.

### Technical Analysis of FINLO's Native Bootstrap Mechanics:
1. **Model Nullability:** `FinloUser.company` is natively configured as `null=True, blank=True, on_delete=PROTECT`. A user can safely exist with `company = None`.
2. **Company Scope Bypass:** In `finlo/contrib/core/authorization.py`:
   ```python
   def get_company_scope(user, request=None):
       if user.is_superuser:
           return CompanyScope(company_id=None, all_companies=True)
       if getattr(user.role, "system_key", None) == "SUPER_ADMIN":
           return CompanyScope(company_id=None, all_companies=True)
   ```
   When `is_superuser = True` or role is `SUPER_ADMIN`, the authorization engine returns `all_companies = True`, granting universal access without requiring a pre-existing company.
3. **Empty Company State in UI:** In `finlo/contrib/core/views/branches.py`:
   ```python
   @cached_property
   def no_record_add_button(self):
       if self.request.user.has_perm("core.add_company"):
           return {
               "url": f"{reverse_lazy('core:create_company')}?new=true",
               "attrs": 'id="branch-create"',
           }
   ```
   When `Company.objects.count() == 0`, `BranchListView` automatically displays the "Add Company" button.
4. **Native Auto-Linking Signal:** In `finlo/contrib/core/signals.py`:
   ```python
   @receiver(post_save, sender=Company)
   def assign_first_company_to_all_users(sender, instance, created, **kwargs):
       """Assign the first company created to all users"""
       if created and Company.objects.count() == 1:
           User.objects.filter(company__isnull=True).update(company=instance)
   ```
   FINLO already contains a built-in signal that automatically links any unassigned user (`superadmin`) to the newly created company the moment the first company is saved!
5. **Code Modification Requirement:** **NONE.** FINLO natively supports bootstrap administration without any invasive source code alterations.

---

## 4. Converting Canonical Configuration to Global Templates

In FINLO, `Role`, `LeadStatus`, `OpportunityStage`, and `OpportunitySettings` have a ForeignKey to `Company` with `on_delete = CASCADE`. However, all four models configure `company` as **`null = True`**:

| Model | Table | Action During Reset | Resulting State |
| :--- | :--- | :--- | :--- |
| `core.Role` | `core_role` | `Role.objects.all().update(company=None)` | All 6 canonical roles become **Global Roles**, surviving Company 3 deletion. |
| `leads.LeadStatus` | `leads_leadstatus` | `LeadStatus.objects.all().update(company=None)` | 6-stage Lead lifecycle becomes a **Global Template**. |
| `opportunities.OpportunityStage` | `opportunities_opportunitystage` | `OpportunityStage.objects.all().update(company=None)` | 10 Opportunity stages become a **Global Pipeline Template**. |
| `opportunities.OpportunitySettings` | `opportunities_opportunitysettings` | `OpportunitySettings.objects.all().update(company=None)` | Opportunity settings become a **Global Default**. |
| `theme.FinloColorTheme` | `theme_horillacolortheme` | Already has no company FK (13 rows) | Preserved 100% as **Global Themes**. |

---

## 5. Comprehensive Reset Scope (Model Registry Audit)

The audit examined all 147 registered Django models. The tables are classified below:

### 5.1 Tables Proposed for Clearing (~1,981 Rows)

```
┌────────────────────────────────────────────────────────────────────────┐
│                      TRANSACTIONAL DATA TO CLEAR                       │
├───────────────────────────────┬────────────────────────────────────────┤
│ Module                        │ Tables & Current Counts                │
├───────────────────────────────┼────────────────────────────────────────┤
│ Leads & Capture               │ leads_lead (105)                       │
│                               │ leads_leadcaptureform (0)              │
│                               │ leads_leadfile (0)                     │
├───────────────────────────────┼────────────────────────────────────────┤
│ Opportunities & Pipeline      │ opportunities_opportunity (51)         │
│                               │ opportunities_opportunitycontactrole (50)
│                               │ opportunities_opportunityteam (0)      │
│                               │ opportunities_opportunityteammember (0)│
├───────────────────────────────┼────────────────────────────────────────┤
│ Accounts & Contacts           │ accounts_account (26)                  │
│                               │ contacts_contact (77)                  │
│                               │ contacts_contactaccountrelationship (75│
├───────────────────────────────┼────────────────────────────────────────┤
│ Activities & Communications   │ activity_activity (122)                │
│                               │ activity_activitycomment (0)           │
│                               │ activity_callrecord (0)                │
├───────────────────────────────┼────────────────────────────────────────┤
│ Campaigns                     │ campaigns_campaign (12)                │
│                               │ campaigns_campaignmember (50)          │
├───────────────────────────────┼────────────────────────────────────────┤
│ Forecasts                     │ forecast_forecast (108)                │
├───────────────────────────────┼────────────────────────────────────────┤
│ Company & Sales Hierarchy     │ core_company (1 — FINLONEXA UAT)       │
│                               │ core_salesregion (1 — UAT South)       │
│                               │ core_salesteam (1 — UAT South Team)    │
│                               │ core_salesassignment (6)               │
├───────────────────────────────┼────────────────────────────────────────┤
│ Company Configuration         │ core_fiscalyear (1)                    │
│                               │ core_fiscalyearinstance (2)            │
│                               │ core_quarter (8)                       │
│                               │ core_period (24)                       │
│                               │ core_multiplecurrency (2)              │
│                               │ core_fieldpermission (30)              │
│                               │ core_recyclebinpolicy (1)              │
├───────────────────────────────┼────────────────────────────────────────┤
│ Sessions, Logs & UI State     │ django_session (683)                   │
│                               │ login_history_loginhistory (278)       │
│                               │ auditlog_logentry (84)                 │
│                               │ keys_shortcutkey (198)                 │
│                               │ core_horillaattachment (61)            │
│                               │ core_recentlyviewed (30)               │
│                               │ core_activetab (12)                    │
│                               │ core_listcolumnvisibility (259)        │
│                               │ core_pinnedview (1)                    │
│                               │ calendar_usercalendarpreference (8)    │
│                               │ calendar_useravailability (1)          │
│                               │ calendar_googlecalendarconfig (2)      │
└───────────────────────────────┴────────────────────────────────────────┘
```

### 5.2 Zero-Row Module Tables Audited & Confirmed Clean (87 Tables)
All other transactional and domain tables across installed modules (`calls`, `meeting`, `bookings`, `notifications`, `cadences`, `duplicates`, `approvals`, `reviews`, `workflow`) currently have 0 rows and will remain 0.

### 5.3 Essential Global Configuration PRESERVED (100% UNTOUCHED)
- `auth_permission` (1,234 rows)
- `django_content_type` (162 rows)
- `core_role` (6 canonical roles — converted to global templates)
- `leads_leadstatus` (6 lifecycle stages — converted to global templates)
- `opportunities_opportunitystage` (10 pipeline stages — converted to global templates)
- `opportunities_opportunitysettings` (1 row — converted to global default)
- `theme_horillacolortheme` (13 visual branding themes)
- `mail_horillamailconfiguration`, `meeting_meetingintegrationsetting`, `calls_callintegrationsetting`, `calendar_googleintegrationsetting` (1 row each — integration frameworks)

---

## 6. Accounts Proposed for Removal vs. Retained

### 6.1 Single Master Superadmin Account (Retained & Reconciled)
- **Username:** `superadmin`
- **User ID:** `33`
- **Target Configuration:**
  - `is_active = True`
  - `is_staff = True`
  - `is_superuser = True`
  - `role_id = 7` (`SUPER_ADMIN` canonical role)
  - `company = None` (Bootstrap state — ready to create the first company)
  - Administrator-supplied approved email address
  - Fresh strong password configured via Django PBKDF2 `set_password()`

### 6.2 Service Account Policy: `Horilla Bot` (User ID 2)
- In accordance with instructions, `Horilla Bot` will be retained strictly as an **internal locked service bot**:
  - `set_unusable_password()` (cannot authenticate via web or API)
  - `is_staff = False`, `is_superuser = False`, `is_active = True`
  - No human login capability.

### 6.3 Nine Human Test Accounts to Purge
The following 9 test and legacy accounts will be permanently removed:
- User ID 1: `hafiz` (legacy developer)
- User ID 3: `test_superadmin`
- User ID 4: `test_head_sales`
- User ID 5: `test_rsm`
- User ID 6: `test_ssm`
- User ID 7: `test_asm`
- User ID 8: `test_bdo`
- User ID 34: `admin` (obsolete test admin)
- User ID 35: `test_superuser`

---

## 7. Exact 12-Step Transactional Execution Sequence

To prevent foreign-key `ProtectedError` and cascade accidents, the reset executes in strict dependency order within explicit database transactions:

```
[Step 1] Technical Preflight Reconfirmation
    ↓
[Step 2] Convert Canonical Models to Global Templates (Role, LeadStatus, Stage -> company=None)
    ↓
[Step 3] Reconcile Superadmin (User 33 -> company=None, role=7, superuser=True, active=True)
    ↓
[Step 4] Verify Superadmin Authentication & Session Path
    ↓
[Step 5] Clear Transactional Child & Junction Records (Junctions, Attachments, Forecasts)
    ↓
[Step 6] Clear Transactional Parent Records (Activities, Campaigns, Opps, Contacts, Accounts, Leads)
    ↓
[Step 7] Clear Sessions, Audit Logs, Login History, UI State, and Sales Assignments
    ↓
[Step 8] Clear / Reassign Protected System References on SalesTeam, Dashboard, Reports
    ↓
[Step 9] Delete Company-Specific Configuration (SalesRegion, SalesTeam, FiscalYears, Currencies)
    ↓
[Step 10] Delete Old Company (Company ID 3 — FINLONEXA UAT)
    ↓
[Step 11] Purge Obsolete Human Test Accounts (User IDs 1, 3, 4, 5, 6, 7, 8, 34, 35)
    ↓
[Step 12] Final Verification (Audit zero rows, verify Superadmin UI bootstrap state)
```

---

## 8. Post-Execution Verification Checklist

Following execution, the system will be verified against the following acceptance criteria:

1. **Administrator Identity:**
   - Exactly ONE active human account exists: `superadmin`.
   - `superadmin.is_superuser == True`, `superadmin.is_staff == True`, `superadmin.is_active == True`.
   - `superadmin.role.system_key == 'SUPER_ADMIN'`.
   - `superadmin.company is None`.
2. **Company State:**
   - `Company.objects.count() == 0`.
   - `BranchListView` renders empty state with "Add Company" button.
   - Creating a company succeeds and automatically triggers `assign_first_company_to_all_users`.
3. **Data Cleanliness:**
   - `Lead.objects.count() == 0`
   - `Opportunity.objects.count() == 0`
   - `Account.objects.count() == 0`
   - `Contact.objects.count() == 0`
   - `Activity.objects.count() == 0`
   - `Campaign.objects.count() == 0`
   - `Forecast.objects.count() == 0`
   - `SalesRegion.objects.count() == 0`
   - `SalesTeam.objects.count() == 0`
   - `SalesAssignment.objects.count() == 0`
4. **Engine Preservation:**
   - 6 Canonical roles exist with `company is None` (883 permissions attached to SUPER_ADMIN).
   - 6 Lead lifecycle stages exist with `company is None`.
   - 10 Opportunity stages exist with `company is None`.
   - 1,234 permissions and 162 content types preserved.
   - MCP tools continue enforcing authenticated account scoping.
5. **Security:**
   - All 9 obsolete accounts are purged.
   - All old sessions are invalidated.
   - `Horilla Bot` has unusable password and no admin privileges.

---

## 9. Final Execution Confirmation Gate

> [!IMPORTANT]
> The preflight audit and full backup verification are complete.  
> Execution of the destructive reset (Steps 2–11) will proceed upon receiving:
> 1. Confirmation to proceed with the 12-step execution.
> 2. The approved administrator email address to assign to `superadmin`.
> 3. Confirmation of the preferred password setup method (CLI interactive prompt or temporary secure setup).

