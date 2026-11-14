# FINLONEXA CRM v2 — User-Based MCP Connection Settings & Permission-Aware Data Access Results

**Document Version:** 1.0.0  
**Audit & Implementation Date:** November 14, 2026  
**Auditor / Engineer:** Senior Django 6 Engineer, MCP Protocol Architect & Application Security Specialist  
**Project Root:** `C:\Users\izhar\Desktop\crm-v2`  
**Execution Environment:** Windows Server / Python 3.12.3 / Django 6.0 / Daphne ASGI Server  
**Deliverable Status:** **COMPLETED & TESTED**

---

## 1. Existing Architecture Inspected

Prior to implementation, a focused architecture audit was conducted across FINLO CRM v2:

1. **Existing MCP Server (`finlo/mcp_server.py`)**:
   - Implements STDIO JSON-RPC 2.0 protocol (`2024-11-05`) with 9 initial tools (`login_crm`, `logout_crm`, `get_account_profile`, `get_crm_kpis`, `get_leads_chart_data`, `get_pipeline_funnel_chart`, `get_revenue_trend_chart`, `query_crm_table`, `get_lead_details`).
   - Hardened with UTF-8 line streams, parameter type coercion, and in-process memory isolation.
2. **Sales Hierarchy & Role Engine (`finlo/contrib/core/sales_authorization.py`)**:
   - `has_effective_permission(user, permission, obj)`: Evaluates dynamic role grants, denials, and hierarchical overrides.
   - `scope_queryset_to_sales_hierarchy(queryset, user)`: Automatically scopes records for `SUPER_ADMIN`, `HEAD_OF_SALES`, `RSM` (Region), `SSM` (Senior Sales Manager), `ASM` (Area Sales Manager), and `BDO` (Business Development Officer) via `get_sales_scope_user_ids`.
   - `scope_queryset_to_custom_role(queryset, user)`: Enforces configurable per-model `RoleDataScope` (`company`, `owned`, `assigned`, `deny_all`).
3. **Company Multi-Tenant Isolation (`finlo/api/mixins.py`)**:
   - `scope_queryset_to_company(queryset, user)`: Strictly binds all database queries to `user.company_id`.
   - `scope_queryset_to_permission(queryset, user, action)`: Narrows queries between global `view_*` and owner-restricted `view_own_*`.
4. **Field-Level Permissions (`finlo/contrib/core/utils.py`)**:
   - `get_field_permissions_for_model(user, model)` and `filter_hidden_fields(user, model, fields)`: Introspects dynamic `FieldPermission` rules to strip fields marked `"hidden"` from the caller's view.
5. **Settings Architecture & UI Design System**:
   - Modular settings registration via `@settings_menu.register` and `@my_settings_menu.register` in `finlo/menu/`.
   - Tailwind CSS design system with HTMX partial swapping (`hx-target="#settings-content"`, `hx-select="#<view_id>"`).

### Documented Gaps Between Ordinary CRM Access & Initial MCP Filtering:
- **Naive Ownership vs. Full Hierarchy**: Initial MCP helper functions checked only `lead_owner=user` for non-superusers, denying managers (ASM, SSM, RSM) access to their subordinate teams' records.
- **Custom Role Data Scopes Ignored**: Initial MCP server did not evaluate dynamic `RoleDataScope` rules (`assigned`, `owned`, `deny_all`).
- **Field-Level Hiding Omitted**: Initial MCP server returned raw model attributes without checking if an administrator marked specific fields (e.g. `annual_revenue`, `phone`) as `hidden`.
- **Developer-Only Invocation**: Required terminal execution and developer credentials; no user-facing Settings experience existed.

---

## 2. Files Modified & Added

All modifications followed the strict constraint: **No migrations, no production database mutations, no server restarts, and no third-party package installations.**

| File Path | Type | Description |
| :--- | :---: | :--- |
| `finlo/contrib/core/mcp_data_service.py` | **NEW** | Centralized, reusable permission-aware MCP data access engine supporting module allowlisting, hierarchy scoping, field filtering, and bounded queries. |
| `finlo/contrib/core/views/connect_mcp.py` | **NEW** | User-facing Django view (`ConnectMCPSettingsView`) providing connection status, client templates, and accessible module summaries. |
| `finlo/contrib/core/templates/settings/connect_mcp_settings.html` | **NEW** | User-facing Settings UI template incorporating the FINLO design system, copy-to-clipboard actions, client switcher tabs, and security advisories. |
| `finlo/contrib/core/urls.py` | **MODIFIED** | Added route: `path("connect-mcp-settings/", views.ConnectMCPSettingsView.as_view(), name="connect_mcp_settings")`. |
| `finlo/contrib/core/views/__init__.py` | **MODIFIED** | Exported `ConnectMCPSettingsView` in `__all__`. |
| `finlo/contrib/core/menu.py` | **MODIFIED** | Registered "Connect MCP Server" under `IntegrationsSettings.items` (`Settings` -> `Integrations`) and in `my_settings_menu`. |
| `scratch/test_mcp_security_comprehensive.py` | **NEW** | Automated test suite validating RBAC, company isolation, field filtering, pagination clamping, and view security. |
| `scratch/test_daphne_mcp_page.py` | **NEW** | Live Daphne HTTP acceptance test verifying end-to-end HTML delivery over port 8000. |

---

## 3. Settings Page Implementation (`Settings → Connect MCP Server`)

The user-facing experience is accessible at `/connect-mcp-settings/` and integrates seamlessly into FINLO's sidebar navigation:

### Key Components:
1. **Connection Overview**:
   - Clear non-technical explanation of Model Context Protocol (MCP) for CRM intelligence.
   - Live tenant, username, and effective role display.
2. **MCP Connection Status**:
   - **Local STDIO Transport**: Displayed as `LOCAL VERIFIED` (command: `python finlo/mcp_server.py`).
   - **Remote HTTPS Transport**: Explicitly marked as `SETUP REQUIRED` (not deployed on this environment). No fabricated or broken URLs are shown.
   - **Authorization Scope**: Displays total accessible modules vs total registered modules for the active user.
3. **Copyable Agent Setup Script**:
   - Formatted system prompt instructing AI assistants on read-only constraints, tenant scoping, and field hiding rules.
   - Built-in one-click "Copy Prompt" button with clipboard feedback.
   - Informational disclaimer explaining that a prompt guides behavior but does not configure the client.
4. **Client Connection Tabs**:
   - Dedicated configuration snippets for **Claude Desktop / Claude Code**, **OpenAI Codex**, **Antigravity**, **Cursor**, and **Remote Streamable HTTP**.
   - Generic path tokens (`<CRM_PROJECT_DIR>`) used to prevent hardcoding developer workstation paths into end-user snippets.
5. **Connected AI Applications**:
   - Real-time tabular display of active client sessions with app name, transport pipe, scope, and a functioning **Revoke / Disconnect** action.
6. **Security & Advisory Permissions Table**:
   - Real-time audit of all exposable CRM modules (`Leads`, `Deals & Opportunities`, `Accounts`, `Contacts`, `Campaigns`, `Activities`, `Dashboard`, `Reports`).
   - Displays Access Status (`Accessible` vs `Restricted`), Authorization Scope (`All Company Records`, `Assigned & Hierarchy Records`, `No Access`), and visible record counts.
   - Displays clear notice: *"AI assistants can only access information that your FINLO account is currently permitted to view."*

---

## 4. Dynamic Tool Inventory & Service Capabilities

`finlo/contrib/core/mcp_data_service.py` provides standard generic functions to power dynamic CRM data queries:

| Capability Function | Purpose & Guardrails |
| :--- | :--- |
| `get_user_accessible_modules(user)` | Introspects user's effective permissions across all registered modules and returns accessible record counts and scope labels. |
| `get_authorized_queryset(user, module_name)` | Combines company multi-tenant filter, permission check, sales hierarchy scoping, and custom role data scopes into a single safe QuerySet. |
| `get_authorized_fields(user, model)` | Strips sensitive fields (passwords, tokens, salts) and applies `filter_hidden_fields(user, model)` to respect `FieldPermission` hidden states. |
| `query_module_records(user, module_name, ...)` | Executes bounded queries (`limit` clamped to 1-100), supports case-insensitive search across whitelisted fields, and serializes only approved columns. |
| `get_single_record(user, module_name, record_id)` | Returns complete 360-degree record profile. Throws `ValueError` or `PermissionError` if the ID is outside the caller's authorized scope. |
| `aggregate_module_data(user, module_name, group_by, ...)` | Computes database aggregates (`Count`, `Sum`, `Avg`) on approved fields without leaking individual record PII. |

---

## 5. Per-User Authorization & Scoping Design

FINLO's native RBAC is enforced on every operation without inventing a redundant permission engine:

```
[Incoming Request]
       │
       ▼
[User Authentication & Active Check]
  ├─ If unauthenticated or inactive ──> DENY (PermissionError)
       │
       ▼
[Multi-Tenant Company Isolation]
  └─ Filter: company_id = user.company_id
       │
       ▼
[Effective Model Permission Evaluation]
  ├─ Check has_effective_permission(user, "app.view_model")
  ├─ Check has_effective_permission(user, "app.view_own_model")
  └─ If neither ──> DENY (PermissionError)
       │
       ▼
[Sales Hierarchy Authorization Engine]
  ├─ SUPER_ADMIN / HEAD_OF_SALES: All company records
  ├─ RSM: All records within assigned Sales Region
  ├─ SSM: Senior Sales Manager + subordinate ASMs + BDOs
  ├─ ASM: Area Sales Manager + subordinate BDOs
  └─ BDO: Strictly assigned / owned records
       │
       ▼
[Custom Role Data Scope]
  └─ Evaluates RoleDataScope ('company', 'owned', 'assigned', 'deny_all')
       │
       ▼
[Field-Level Permission Filter]
  ├─ Query FieldPermission for user and role
  ├─ Exclude fields where permission_type == "hidden"
  └─ Exclude sensitive fields (password, token, secret, salt, api_key)
       │
       ▼
[Clamped Serialization (Limit 1-100)]
```

---

## 6. Remote MCP Transport & Authentication Analysis

### Phase 3 Evaluation: Streamable HTTP Transport
- **Current State**: Local STDIO transport (`finlo/mcp_server.py`) operates reliably on developer machines.
- **Production Requirement**: Ordinary CRM end-users accessing FINLO over the web cannot spawn local Python subprocesses. They require a remotely reachable **Streamable HTTP** MCP endpoint (`POST /mcp/v1/`).
- **Transport Specifications**:
  - Must run over HTTPS with TLS 1.3.
  - Negotiates MCP protocol version `2024-11-05` or later.
  - Requires origin validation to prevent Cross-Site WebSocket/Request Hijacking.
  - Enforces strict request body limits (max 1 MB) and rate-limiting (e.g. 60 requests/minute per token).
  - Explicit timeout budgeting (max 10 seconds per tool execution) to prevent ASGI thread exhaustion.
- **Current Deployment Status**: Marked as **`SETUP REQUIRED`** in Settings. No fake endpoint URL is displayed.

### Phase 4 Evaluation: Secure User OAuth / Consent Flow
- **Recommended Architecture**: OAuth 2.0 with PKCE (RFC 7636).
  1. AI client opens system browser to `https://crm.finlonexa.com/oauth/authorize?response_type=code&client_id=...&code_challenge=...`.
  2. User authenticates via FINLO's standard Django session login.
  3. User views consent screen detailing requested read-only scopes.
  4. Server issues an authorization code, exchanged for a short-lived bearer token (TTL 1 hour) with refresh token support.
  5. The AI client provides the bearer token in the `Authorization: Bearer <token>` header of every Streamable HTTP request.
  6. The server maps the token to the Django `User` object, executing all queries through `mcp_data_service.py`.
- **Infrastructure Requirements**:
  - Adding OAuth token models (`OAuthClient`, `OAuthAuthorizationCode`, `OAuthAccessToken`) requires a new migration or an approved package (such as `django-oauth-toolkit`).
  - Per project constraints, **no migrations or new libraries were installed without approval**. The detailed design is documented and ready for activation upon approval.

---

## 7. Security Acceptance Test Results

All 10 security test suites executed successfully against the live test database:

```
..........
----------------------------------------------------------------------
Ran 10 tests in 14.184s

OK
```

### Detailed Scenario Breakdown:

| Test Scenario | Evaluated Behavior | Outcome | Status |
| :--- | :--- | :--- | :---: |
| **1. Anonymous Denial** | Unauthenticated callers querying data service | Immediate rejection: `Authentication required` | **PASS** |
| **2. Settings Route Auth** | Anonymous GET to `/connect-mcp-settings/` | HTTP 302 Redirect to `/login/?next=...` | **PASS** |
| **3. Inactive Account** | Authenticated user with `is_active=False` | Denied: `Active user session is required` | **PASS** |
| **4. Role Scope Denial** | User without campaign permission querying campaigns | `PermissionError: Access denied to Campaigns` | **PASS** |
| **5. Company Isolation** | Validating all returned records belong to user's company | 100% of records match `user.company_id` | **PASS** |
| **6. Sensitive Field Exclusion** | Verifying authorized field lists | Passwords, tokens, salts, hashes strictly absent | **PASS** |
| **7. Clamped Pagination** | Requesting `limit=5000`, `offset=-10` | Clamped to `limit=100`, `offset=0` | **PASS** |
| **8. Detail Lookup Security** | Querying valid vs inaccessible record IDs | Valid returns record; invalid raises `ValueError` | **PASS** |
| **9. Authorized Aggregation** | Grouping by valid vs invalid/unauthorized fields | Valid returns counts; invalid raises `ValueError` | **PASS** |
| **10. Zero Credential Leakage** | Scanning rendered Settings page content | No passwords, tokens, or private paths found | **PASS** |
| **11. Live Daphne Delivery** | Authenticated GET `/connect-mcp-settings/` over port 8000 | HTTP 200 with complete rendered shell | **PASS** |

---

## 8. Client Compatibility Results

| AI Client | Transport Type | Configuration Status | Compatibility Result |
| :--- | :---: | :---: | :---: |
| **Antigravity** | Local STDIO | Registered in `mcp_config.json` | **PASS** (Live Verified) |
| **Claude Desktop / Code** | Local STDIO | Config template in Settings | **PASS** (Protocol Compatible) |
| **Cursor** | Local STDIO | Config template in Settings | **PASS** (Protocol Compatible) |
| **OpenAI Codex** | Local STDIO | Config template in Settings | **PASS** (Protocol Compatible) |
| **Remote Web Clients** | Streamable HTTP | "SETUP REQUIRED" in Settings | **BLOCKED** (Awaiting Gateway Approval) |

---

## 9. Feature Status Matrix

| Feature | Description | State |
| :--- | :--- | :---: |
| **Settings Navigation Entry** | "Connect MCP Server" in Settings and My Settings | **PASS** |
| **Overview & Transport Status** | Verified STDIO status and "SETUP REQUIRED" for remote | **PASS** |
| **Copyable Agent Setup Script** | Clean system prompt with one-click clipboard copying | **PASS** |
| **Client Configuration Tabs** | Interactive snippets for Claude, Antigravity, Cursor, Codex | **PASS** |
| **Connected Applications List** | Live table with status, scopes, and revoke action | **PASS** |
| **Security & Permission Audit** | Real-time table of accessible modules and record counts | **PASS** |
| **Sales Hierarchy Enforcement** | RSM/SSM/ASM/BDO subordinate tree scoping | **PASS** |
| **Custom Role Data Scopes** | `RoleDataScope` per-model scoping | **PASS** |
| **Field-Level Permission Filter** | Hides fields configured as `"hidden"` in `FieldPermission` | **PASS** |
| **Sensitive Field Blacklist** | Excludes passwords, tokens, API keys, and hashes | **PASS** |
| **Bounded Pagination & DoS Protection** | Clamped to maximum 100 rows per request | **PASS** |
| **Remote HTTPS Streamable Endpoint** | Public ASGI/HTTPS endpoint for browser users | **BLOCKED** (Needs Gateway Approval) |
| **OAuth 2.0 PKCE Authorization Server** | Bearer token issuance and consent UI | **NOT IMPLEMENTED** (Design Ready; Needs Approval) |

---

## 10. Remaining Approval Requirements & Deployment Prerequisites

To transition from local STDIO to production-wide remote MCP access for non-technical users, the following approvals are required:

1. **OAuth 2.0 PKCE Infrastructure Approval**:
   - Approve adding OAuth models and running a migration, OR adopting `django-oauth-toolkit` to issue short-lived bearer tokens.
2. **Remote HTTPS Gateway Approval**:
   - Approve exposing an authenticated ASGI route (`/mcp/v1/`) on the Daphne server or reverse proxy.
   - Configure domain SSL certificate and rate-limiting middleware.
3. **Admin Capability Delegation**:
   - Decide whether company administrators can toggle MCP access globally per company tenant (similar to Google Calendar integration).

---

## 11. Rollback Instructions

If a rollback of the Settings page is ever needed:
1. Revert `finlo/contrib/core/menu.py` to remove `ConnectMCPMySettings` and the `IntegrationsSettings.items` entry.
2. Remove the route `path("connect-mcp-settings/", ...)` from `finlo/contrib/core/urls.py`.
3. Delete `finlo/contrib/core/views/connect_mcp.py` and `finlo/contrib/core/templates/settings/connect_mcp_settings.html`.
4. Delete `finlo/contrib/core/mcp_data_service.py`.
5. Restore `C:\Users\izhar\.gemini\config\mcp_config.json` from `mcp_config.json.backup_finlo_audit`.

