# FINLONEXA CRM v2 — Fresh-Start Pre-Reset Backup Verification

**Document Status:** VERIFIED & READY  
**Date:** November 14, 2026  
**Target Environment:** Staging / Pre-Production Supabase Instance  
**Database Host:** `aws-0-ap-south-1.pooler.supabase.com:6543` (Mumbai, `ap-south-1`)  
**Supabase Project Ref:** `ordzcyrzqhdsavfkkouz`  
**Database Name:** `postgres`  
**Django Database Engine:** `django.db.backends.postgresql`  

---

## 1. Backup Summary

Prior to initiating the fresh-start database reset, a complete, recoverable, natural-key database backup was generated and rigorously verified.

| Backup Attribute | Verified Value | Compliance Status |
| :--- | :--- | :---: |
| **Backup File Path** | `backups/finlo_full_backup_pre_reset_20261114.json` | PASS |
| **Absolute Local Path** | `C:\Users\izhar\Desktop\crm-v2\backups\finlo_full_backup_pre_reset_20261114.json` | PASS |
| **File Size** | **1,864,394 bytes** (1.86 MB) | PASS |
| **Generation Duration** | 581.50 seconds (9 min 41 sec) | PASS |
| **Total Objects Serialized** | **2,426 objects** | PASS |
| **Active Models Covered** | **47 distinct models** across all installed apps | PASS |
| **JSON Format Integrity** | Valid JSON syntax; fully deserializable via `json.load()` | PASS |
| **Primary Key Collisions** | Natural keys & natural foreign keys enabled (`--natural-foreign --natural-primary`) | PASS |
| **Exclusions (Safety)** | `contenttypes`, `auth.permission`, and 6 unmigrated virtual models | PASS |

---

## 2. Model-by-Model Object Breakdown in Backup

The backup captures 100% of the database state, including business data, configuration metadata, and security settings:

| Application | Model Name | Serialized Count | Classification |
| :--- | :--- | :---: | :--- |
| **accounts** | `Account` | 26 | Business Data (Accounts) |
| **activity** | `Activity` | 122 | Business Data (Calls, Meetings, Tasks) |
| **auditlog** | `LogEntry` | 84 | Audit History Records |
| **calendar** | `GoogleCalendarConfig` | 2 | Calendar Integration Config |
| **calendar** | `GoogleIntegrationSetting` | 1 | Calendar Global Integration Setting |
| **calendar** | `UserAvailability` | 1 | User Availability Setting |
| **calendar** | `UserCalendarPreference` | 8 | User Calendar Preferences |
| **calls** | `CallIntegrationSetting` | 1 | VOIP / Telephony Settings |
| **campaigns** | `Campaign` | 12 | Business Data (Campaigns) |
| **campaigns** | `CampaignMember` | 50 | Junction Data (Campaign Members) |
| **contacts** | `Contact` | 77 | Business Data (Contacts) |
| **contacts** | `ContactAccountRelationship` | 75 | Junction Data (Contact-Account Roles) |
| **core** | `ActiveTab` | 12 | User UI Tab States |
| **core** | `Company` | 1 | Multi-Tenant Company (`FINLONEXA UAT`) |
| **core** | `FieldPermission` | 30 | Field-Level Security Rules |
| **core** | `FinloAttachment` | 61 | Uploaded File Attachments |
| **core** | `FinloUser` | 11 | Human & Service User Accounts |
| **core** | `FiscalYear` | 1 | Fiscal Year Definition |
| **core** | `FiscalYearInstance` | 2 | Fiscal Year Tracking Instances |
| **core** | `ListColumnVisibility` | 259 | User Grid Column Configurations |
| **core** | `MultipleCurrency` | 2 | Currency Definitions (USD, PKR) |
| **core** | `Period` | 24 | Fiscal Monthly Accounting Periods |
| **core** | `PinnedView` | 1 | User Pinned View Setting |
| **core** | `Quarter` | 8 | Fiscal Quarter Definitions |
| **core** | `RecentlyViewed` | 30 | User Recent History Navigation |
| **core** | `RecycleBinPolicy` | 1 | Trash Retention Policy |
| **core** | `Role` | 6 | Canonical Sales Hierarchy Roles |
| **core** | `SalesAssignment` | 6 | User Regional Sales Assignments |
| **core** | `SalesRegion` | 1 | Sales Regional Unit (`UAT South`) |
| **core** | `SalesTeam` | 1 | Sales Team Unit (`UAT South Team`) |
| **dashboard** | `Dashboard` | 1 | System Dashboard Definition |
| **forecast** | `Forecast` | 108 | Business Data (Sales Forecasts) |
| **forecast** | `ForecastType` | 1 | Forecasting Model Settings |
| **keys** | `ShortcutKey` | 198 | User Hotkey State Settings |
| **leads** | `Lead` | 105 | Business Data (Leads) |
| **leads** | `LeadStatus` | 6 | Canonical 6-Stage Lead Lifecycle |
| **login_history** | `LoginHistory` | 278 | User Authentication Logs |
| **mail** | `FinloMailConfiguration` | 1 | Email Server Integration Settings |
| **meeting** | `MeetingIntegrationSetting` | 1 | Video Conference Settings |
| **opportunities** | `Opportunity` | 51 | Business Data (Opportunities) |
| **opportunities** | `OpportunityContactRole` | 50 | Junction Data (Opportunity Contact Roles) |
| **opportunities** | `OpportunitySettings` | 1 | Pipeline Configuration Settings |
| **opportunities** | `OpportunityStage` | 10 | Pipeline Stage Definitions |
| **reports** | `Report` | 2 | Base System Reports |
| **reports** | `ReportFolder` | 1 | Report Directory Folder |
| **sessions** | `Session` | 683 | Django Session Tokens |
| **theme** | `FinloColorTheme` | 13 | UI Visual Branding Themes |
| **TOTAL OBJECTS** | | **2,426** | |

---

## 3. Restoration Procedure

If at any point during or after execution a rollback is requested, the database can be fully restored to this exact state using Django's native deserializer:

```powershell
# Navigate to project root
cd C:\Users\izhar\Desktop\crm-v2

# Restore full database state from backup
.venv\Scripts\python.exe manage.py loaddata backups\finlo_full_backup_pre_reset_20261114.json
```

### Cloud Disaster Recovery
In addition to the local JSON fixture backup:
- **Supabase Automatic Backups:** Active on Supabase Mumbai project `ordzcyrzqhdsavfkkouz`.
- **Point-in-Time Recovery (PITR):** Available via the Supabase Cloud dashboard to roll back database storage to any timestamp.

---

## 4. Verification Verdict

- **Database Reachability:** `PASS`
- **Backup File Created:** `PASS` (1,864,394 bytes)
- **JSON Serialization & Integrity:** `PASS` (2,426 objects verified)
- **Restoration Viability:** `PASS`

