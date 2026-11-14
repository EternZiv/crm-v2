# FINLONEXA CRM v2 — Complete CRM Data Reset Preview

**Document Status:** PENDING ADMINISTRATOR APPROVAL (PHASE 7 CHECKPOINT)  
**Date:** November 14, 2026  
**Environment:** Staging / Pre-Production Supabase Instance  
**Database Host:** `aws-0-ap-south-1.pooler.supabase.com:6543` (Mumbai, `ap-south-1`)  
**Supabase Project Ref:** `ordzcyrzqhdsavfkkouz`  
**Application Engine:** Django 6.0 / ASGI Daphne / PostgreSQL 15+  

---

## 1. Executive Summary

This preview details the exact, model-aware data reset operation proposed to prepare **FINLONEXA CRM v2** for a fresh operational rollout.

The planned outcome is:
1. **Exactly ONE active human login account:** `superadmin` with full FINLO administrative authority, Django superuser/staff status, and association with the primary company.
2. **Complete removal of sample/test business records:** 100% of test Leads, Opportunities, Accounts, Contacts, Activities, Campaigns, Forecasts, and related junctions (~1,981 rows across 21 tables) safely cleared.
3. **Preservation of essential configuration:** Database schemas, migration history, 1,234 system permissions, 6 canonical sales roles, field permission rules, pipeline stages, currencies, fiscal periods, and application settings remain 100% intact.
4. **Referential integrity protected:** All foreign key constraints, ownership references, and protected relations are systematically resolved in a strict dependency-ordered deletion sequence, eliminating any risk of `ProtectedError` or orphaned records.

> [!IMPORTANT]
> **Strict Checkpoint Rule:** No deletions, database mutations, or account resets will occur until the administrator grants explicit approval at the Phase 7 checkpoint.

---

## 2. Target Database & Infrastructure Verification

| Attribute | Verified Value | Inspection Result |
| :--- | :--- | :--- |
| **Django Database Engine** | `django.db.backends.postgresql` | PASS — PostgreSQL backend verified |
| **Database Host** | `aws-0-ap-south-1.pooler.supabase.com` | PASS — Supabase Mumbai pooler reachable |
| **Port / Pooling Mode** | `6543` (Transaction Pooler) | PASS — Active connection verified |
| **Database Name** | `postgres` | PASS — Verified target database |
| **Supabase Project Ref** | `ordzcyrzqhdsavfkkouz` | PASS — Matches FINLONEXA CRM v2 |
| **Environment Classification** | Staging / Pre-Production | PASS — Confirmed non-production test data |
| **Migration Status** | 100% applied (0 unapplied migrations) | PASS — Schema is fully up to date |
| **Active Local Server** | Daphne ASGI Server (`0.0.0.0:8000`) | PASS — Server active and healthy |
| **Concurrent Agents** | Codex (working on separate role tests) | PASS — No overlap; navigation files untouched |

---

## 3. Account Inventory & Proposed Cleanup (Phase 5)

### 3.1 Retained Single Human Administrator
- **Username:** `superadmin`
- **User ID:** `33`
- **Current State:** `is_superuser = True`, `is_staff = True`, `is_active = False`, `company_id = 3` (`FINLONEXA UAT`), `role_id = None`.
- **Target Reconciled State:**
  - `is_active = True`
  - `role_id = 7` (FINLO Canonical `SUPER_ADMIN` role with 883 permissions)
  - `company_id = 3` (Primary Company)
  - Strong, unique administrator password set via Django PBKDF2 `set_password()`
  - Verified login session and recovery path before old accounts are removed.

### 3.2 Obsolete Accounts Proposed for Removal / Deactivation
The following 9 human test and legacy accounts are identified for cleanup:

| ID | Username | Role / Privilege | Current Status | Proposed Action |
| :---: | :--- | :--- | :---: | :--- |
| **1** | `hafiz` | Legacy developer account | Inactive | Reassign FK references → Purge |
| **3** | `test_superadmin` | Test Superadmin (Role 7) | Active | Reassign ownership → Purge |
| **4** | `test_head_sales` | Test Head of Sales (Role 8) | Active | Reassign ownership → Purge |
| **5** | `test_rsm` | Test Regional Sales Mgr (Role 9) | Active | Reassign ownership → Purge |
| **6** | `test_ssm` | Test Senior Sales Mgr (Role 10) | Active | Clear `SalesTeam.SSM` → Purge |
| **7** | `test_asm` | Test Area Sales Mgr (Role 11) | Active | Clear `SalesTeam.ASM` → Purge |
| **8** | `test_bdo` | Test Business Dev Officer (Role 12) | Active | Reassign ownership → Purge |
| **34** | `admin` | Obsolete secondary admin | Inactive | Purge |
| **35** | `test_superuser` | Test Superuser (Role 7) | Active | Purge |

### 3.3 Service Account Handling Policy
- **User ID 2 (`Horilla Bot`):**
  - **Classification:** Internal System Service Account.
  - **References:** Created Company 3, referenced by system automated workflows and bot default settings.
  - **Proposed Action:** Retain as an internal locked service bot with `set_unusable_password()`, `is_staff = False`, `is_superuser = False`, and `is_active = True`.
  - **Alternative Option:** Reassign `Company.created_by` and all foreign keys to `superadmin` (User 33) and purge.  
  *(Subject to explicit administrator selection in Phase 7).*

---

## 4. Business Data Proposed for Complete Reset (Phase 4)

The database audit identified **48 active tables with rows > 0**.  
The 21 tables below contain operational, transactional, and test data proposed for clearing:

| Table Name | Model Class | Row Count | Classification | Deletion Safe | FK Cascade Safeguards |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `opportunities_opportunitycontactrole` | `OpportunityContactRole` | 50 | Junction | YES | Delete before Opportunity / Contact |
| `contacts_contactaccountrelationship` | `ContactAccountRelationship` | 75 | Junction | YES | Delete before Account / Contact |
| `campaigns_campaignmember` | `CampaignMember` | 50 | Junction | YES | Delete before Campaign / Lead / Contact |
| `core_horillaattachment` | `FinloAttachment` | 61 | Attachments | YES | Delete before parent records |
| `core_recentlyviewed` | `RecentlyViewed` | 30 | UI History | YES | Safe to clear |
| `forecast_forecast` | `Forecast` | 108 | Business Data | YES | Safe to clear |
| `activity_activity` | `Activity` | 122 | Business Data | YES | Delete before Account / Lead / Contact |
| `campaigns_campaign` | `Campaign` | 12 | Business Data | YES | Delete before Opportunity (primary source) |
| `opportunities_opportunity` | `Opportunity` | 51 | Business Data | YES | Delete before Account (protect rule) |
| `contacts_contact` | `Contact` | 77 | Business Data | YES | Delete before Account |
| `accounts_account` | `Account` | 26 | Business Data | YES | Self-referencing FK cleared, then delete |
| `leads_lead` | `Lead` | 105 | Business Data | YES | Delete after CampaignMember / Activity |
| `core_salesassignment` | `SalesAssignment` | 6 | Org Assignment | YES | Delete before deleting sales users |
| `calendar_useravailability` | `UserAvailability` | 1 | User Preference | YES | Delete before deleting users |
| `calendar_usercalendarpreference` | `UserCalendarPreference` | 8 | User Preference | YES | Delete before deleting users |
| `calendar_googlecalendarconfig` | `GoogleCalendarConfig` | 2 | Integration Data | YES | Delete before deleting users |
| `keys_shortcutkey` | `ShortcutKey` | 198 | User UI State | YES | Recreated automatically for new users |
| `core_activetab` | `ActiveTab` | 12 | User UI State | YES | Safe to clear |
| `auditlog_logentry` | `LogEntry` | 88 | Audit History | YES | Test audit entries cleared |
| `login_history_loginhistory` | `LoginHistory` | 282 | Login Logs | YES | Old test logins cleared |
| `django_session` | `Session` | 683 | Auth Sessions | YES | Invalidate all stale sessions |
| **TOTAL BUSINESS / TEST ROWS** | | **1,981** | | | |

---

## 5. System Configuration & Metadata to PRESERVE

The following system tables and metadata records will remain **100% UNTOUCHED**:

| Table Name | Model Class | Row Count | Purpose & Preservation Rationale |
| :--- | :--- | :---: | :--- |
| `auth_permission` | `Permission` | 1,234 | Standard Django permission registry. Essential for RBAC. |
| `django_content_type` | `ContentType` | 162 | Django model type registry. Essential for generic FKs. |
| `core_company` | `Company` | 1 | Primary operational tenant (`FINLONEXA UAT`, ID: 3). |
| `core_role` | `Role` | 6 | Canonical sales hierarchy roles (SUPER_ADMIN, HOS, RSM, SSM, ASM, BDO). |
| `core_fieldpermission` | `FieldPermission` | 30 | Field-level security matrices across roles. |
| `core_salesregion` | `SalesRegion` | 1 | Base regional organizational unit (`UAT South`). |
| `core_salesteam` | `SalesTeam` | 1 | Base sales team structure (reassigned to superadmin). |
| `core_recyclebinpolicy` | `RecycleBinPolicy` | 1 | System retention and trash recovery policy. |
| `core_fiscalyear` | `FiscalYear` | 1 | Fiscal calendar definition. |
| `core_fiscalyearinstance` | `FiscalYearInstance` | 2 | Active fiscal year tracking instances. |
| `core_quarter` | `Quarter` | 8 | Fiscal quarter definitions. |
| `core_period` | `Period` | 24 | Fiscal period / monthly accounting definitions. |
| `core_multiplecurrency` | `MultipleCurrency` | 2 | Currency support (USD, PKR). |
| `leads_leadstatus` | `LeadStatus` | 6 | Canonical 6-stage Lead lifecycle (New, Contacted, Qualified, Proposal, Lost, Convert). |
| `opportunities_opportunitystage` | `OpportunityStage` | 10 | Pipeline stage definitions (Prospecting through Closed Won). |
| `opportunities_opportunitysettings` | `OpportunitySettings` | 1 | Opportunity workflow configuration. |
| `forecast_forecasttype` | `ForecastType` | 1 | Forecasting calculation model settings. |
| `dashboard_dashboard` | `Dashboard` | 1 | Base system dashboard definition (reassigned to superadmin). |
| `reports_reportfolder` | `ReportFolder` | 1 | System report hierarchy folder. |
| `reports_report` | `Report` | 2 | Base system reports (Leads by Source, Lead Status). |
| `mail_horillamailconfiguration` | `FinloMailConfiguration` | 1 | Mail server integration configuration. |
| `meeting_meetingintegrationsetting` | `MeetingIntegrationSetting` | 1 | Meeting / Zoom / Calendar integration settings. |
| `calls_callintegrationsetting` | `CallIntegrationSetting` | 1 | VOIP / telephony integration settings. |
| `calendar_googleintegrationsetting` | `GoogleIntegrationSetting` | 1 | Google Calendar synchronization settings. |
| `theme_horillacolortheme` | `FinloColorTheme` | 13 | UI visual branding and color palettes. |

---

## 6. Cascade Risks & Referential Integrity Strategy

FINLO enforces strict `on_delete=PROTECT` relationships on multiple models. Indiscriminate truncation or deleting users first would fail with `ProtectedError`. The cleanup executes in this **exact 10-step dependency-safe sequence**:

```
Step 1: Junction Tables & Attachments (OpportunityContactRole, ContactAccountRelationship, CampaignMember, Attachments)
   ↓
Step 2: Activities & Meetings (Activity records linked to Leads/Contacts/Accounts)
   ↓
Step 3: Opportunities (Opportunity records; account FK has PROTECT)
   ↓
Step 4: Campaigns (Campaign records; parent_campaign FK cleared first)
   ↓
Step 5: Contacts (Contact records; account FK has PROTECT)
   ↓
Step 6: Accounts (Account records; parent_account FK cleared first)
   ↓
Step 7: Leads (Lead records; LeadStatus has PROTECT)
   ↓
Step 8: Sessions, User History & UI State (Django sessions, LoginHistory, AuditLog, ShortcutKeys, SalesAssignment)
   ↓
Step 9: System Object Ownership Reassignment (Reassign Company, SalesTeam, Dashboard, Reports to User 33)
   ↓
Step 10: Obsolete Human Account Removal (Purge test user accounts 1, 3, 4, 5, 6, 7, 8, 34, 35)
```

---

## 7. Backup and Restoration Plan

### 7.1 Verified Local Pre-Reset Dump
- **Tool:** Django `manage.py dumpdata` with natural keys.
- **Verification Test:** Executed on core business apps (`leads`, `opportunities`, `accounts`, `contacts`, `activity`, `campaigns`, `forecast`).
  - Total objects dumped: **694**.
  - File size: **503,338 bytes**.
  - Verification outcome: **PASS (100% valid JSON, all models restored)**.
- **Production Pre-Reset Backup Target:**  
  `backups/finlo_full_backup_pre_reset_20261114.json` (covers all apps prior to execution).

### 7.2 Cloud Disaster Recovery
- **Supabase Automatic Backups:** Daily automated physical snapshots on Supabase Mumbai (`ordzcyrzqhdsavfkkouz`).
- **Point-in-Time Recovery (PITR):** Available via Supabase Dashboard to roll back database state to any minute.

### 7.3 Restoration Procedure
If rollback is requested:
```powershell
.venv\Scripts\python.exe manage.py loaddata backups/finlo_full_backup_pre_reset_20261114.json
```

---

## 8. Status & Next Actions

- **Reset Preview Status:** `COMPLETED (NEEDS APPROVAL)`
- **Superadmin Setup Plan:** `COMPLETED (NEEDS APPROVAL)`
- **Destructive Execution:** `BLOCKED` until explicit administrator approval of Phase 7 checkpoint items.

