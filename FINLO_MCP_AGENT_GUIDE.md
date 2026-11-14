# FINLONEXA CRM v2 — AI Agent MCP Integration Guide

**Document:** `FINLO_MCP_AGENT_GUIDE.md`  
**Target Server:** FINLO Read-Only Model Context Protocol Server  
**Server Name:** `finlo-crm-readonly`  
**Protocol Version:** `2024-11-05` (JSON-RPC 2.0 over STDIO)  
**File Location:** `finlo/mcp_server.py`

---

## 1. Project Identity & Architecture Overview

FINLONEXA CRM v2 is a single-company enterprise CRM built with:
* **Backend:** Django 6, ASGI (Daphne 4.2.1), PostgreSQL (Supabase pooler), Redis cache, Celery, and Channels.
* **Frontend:** Django Templates, HTMX progressive page navigation, Tailwind CSS, and ECharts.
* **Security & Multi-Tenancy:** Strict company isolation (`user.company`), Django authentication, and a 6-tier canonical sales hierarchy (`SUPER_ADMIN` → `HEAD_OF_SALES` → `RSM` → `SSM` → `ASM` → `BDO`) with dynamic model permissions.
* **Smart Cache Engine:** `LeadDataService` multi-tenant cache keys with 300s TTL and 30s client-side revalidation.

---

## 2. MCP Server Name & Verified Launch Command

* **Server Name:** `finlo-crm-readonly`
* **Transport:** STDIO (Standard Input / Output using newline-delimited JSON-RPC 2.0)
* **Verified Launch Command:**
  ```powershell
  C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe C:\Users\izhar\Desktop\crm-v2\finlo\mcp_server.py
  ```
* **Prerequisites:**
  * Virtual environment at `.venv` with project requirements installed.
  * Active PostgreSQL database connection configured in `finlo/settings/base.py` (Supabase).
  * No external pip packages required for MCP transport (embedded zero-dependency JSON-RPC engine with transparent `FastMCP` delegation if `mcp` is installed).

---

## 3. Discovered Tool Inventory (9 Tools)

All tools are **strictly read-only**. The server cannot create, modify, or delete database records, execute shell commands, or modify files.

| Tool Name | Parameters | Purpose & Output |
| :--- | :--- | :--- |
| `login_crm` | `username_or_email` (str), `password` (str) | Authenticates session against Django auth. Locks all subsequent queries to user's company tenant and role permissions. |
| `logout_crm` | *none* | Clears active in-memory user session. |
| `get_account_profile` | *none* | Returns identity, company tenant, superuser status, roles, and granular model access scopes (`leads`, `opportunities`, `contacts`, `accounts`, `campaigns`, `activities`). |
| `get_crm_kpis` | *none* | Executive scorecard: total leads, conversion rate, active deals, pipeline value, closed-won revenue, win rate, average deal size, total accounts, total contacts. |
| `get_leads_chart_data` | `group_by` (str: `"status"`, `"source"`, `"industry"`) | Returns aggregated lead counts, percentage shares, chart series (pie/bar), and markdown table. |
| `get_pipeline_funnel_chart` | *none* | Returns deal stages, deal volume, total stage value ($), and average stage probability formatted for funnel visualizations. |
| `get_revenue_trend_chart` | `months` (int, default: 6) | Monthly time-series data: new leads created, deals created, and closed-won revenue trends. |
| `query_crm_table` | `entity_type` (str), `search` (str), `limit` (int, max 100), `offset` (int) | Paginated tabular browsing for `leads`, `opportunities`, `contacts`, `accounts`, `campaigns`, or `activities`. |
| `get_lead_details` | `lead_id` (int) | 360-degree detailed read-only profile of an individual Lead record. |

---

## 4. Authentication & Authorization Requirements

1. **Authentication Gate:**
   * Every query tool (`get_account_profile`, `get_crm_kpis`, `get_leads_chart_data`, `get_pipeline_funnel_chart`, `get_revenue_trend_chart`, `query_crm_table`, `get_lead_details`) calls `_get_scoped_user()`.
   * If unauthenticated, the tool execution halts immediately with:
     `PermissionError: Authentication required: You must log in with your Finlo CRM ID/email and password.`
2. **Login Mechanisms:**
   * **Explicit Tool Call:** Call `login_crm(username_or_email="...", password="...")` at the start of your session.
   * **Environment Variables (Optional):** Define `FINLO_USERNAME` and `FINLO_PASSWORD` in your MCP client's `env` configuration block for automatic authentication on server startup.
3. **Multi-Tenant & Role Isolation:**
   * Queries are strictly filtered by `company=user.company`.
   * Records are restricted to assigned items if the user only possesses `view_own_<model>` permissions.

---

## 5. Safe Development Workflow for AI Agents

1. **Connect & Authenticate:**
   * Launch the server via STDIO.
   * Verify initialization via `tools/list`.
   * Call `login_crm` with authorized credentials or verify automatic login via `get_account_profile`.
2. **Read-Only Verification:**
   * Execute `get_crm_kpis()` to verify tenant connectivity.
3. **Visualization & Charting:**
   * Use `get_leads_chart_data`, `get_pipeline_funnel_chart`, and `get_revenue_trend_chart` when users ask for visual summaries, sales pipeline health, or revenue analytics.
4. **Data Browsing:**
   * Use `query_crm_table` with bounded limits (`limit <= 50`) and targeted search strings to prevent fetching massive record sets.

---

## 6. How to Disconnect or Disable the Server

* **From Client Settings:** Remove the `"finlo-crm"` entry from your client's MCP configuration JSON or TOML file.
* **Process Termination:** The server runs as a child process of the AI client. Exiting the client or closing the session automatically sends an EOF to `sys.stdin`, prompting immediate, clean termination with exit code `0`.

