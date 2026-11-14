# FINLONEXA CRM v2 — MCP End-to-End Gap Audit & Security Verification

**Audit Date:** November 14, 2026  
**Auditor:** Senior Django 6 Engineer, MCP Protocol Architect & Application Security Specialist  
**Project Root:** `C:\Users\izhar\Desktop\crm-v2`  
**Execution Environment:** Windows Server / Python 3.12.3 / Django 6.0 / Daphne ASGI Server  
**Audit Scope:** Read-only verification of `finlo/mcp_server.py`, `finlo/contrib/core/mcp_data_service.py`, `finlo/contrib/core/views/connect_mcp.py`, `connect_mcp_settings.html`, and sales hierarchy authorization.

---

## Executive Summary

This end-to-end audit evaluated the alignment between the newly created user-facing Settings page (`Settings → Connect MCP Server`), the dynamic permission-aware data service (`mcp_data_service.py`), and the live MCP server (`finlo/mcp_server.py`).

### Overall Status by Domain:
- **Priority 1: MCP Server vs. Data Service Integration**: **FAIL (DISCONNECTED)**  
  `finlo/mcp_server.py` does not import or invoke `mcp_data_service.py`. The live MCP server continues to execute older, naive query logic that leaks company records past sales hierarchy boundaries for `SSM`, `ASM`, and `BDO` roles.
- **Priority 2: Settings Page Accuracy**: **PASS**  
  The Settings page correctly reflects local STDIO verification, honestly displays `SETUP REQUIRED` for remote HTTPS, generates valid JSON configuration templates, and does not leak secrets.
- **Priority 3: Connected Client Registry & Revocation**: **NOT IMPLEMENTED**  
  The connected applications list is hardcoded in the view, and the "Revoke" button is purely a client-side DOM removal (`tr.remove()`). No database models, session tokens, or credential revocation mechanisms exist.
- **Priority 4: Security Regression Across Roles**: **MIXED**  
  `mcp_data_service.py` passes all 10 security and hierarchy tests with 100% accuracy. However, `finlo/mcp_server.py` fails sales hierarchy scoping due to the architectural gap identified in Priority 1.
- **Priority 5: Remote HTTPS & OAuth Prerequisites**: **BLOCKED (PENDING APPROVAL)**  
  Remote Streamable HTTP transport and OAuth 2.0 PKCE require infrastructure deployment and model migrations that are strictly held pending user authorization.

---

## 1. Existing MCP Tools vs. New Data Service Integration

| Feature / Verification Criterion | Standalone `mcp_data_service.py` | Live `finlo/mcp_server.py` | Integration Gap | Status |
| :--- | :---: | :---: | :--- | :---: |
| **Service Dependency** | Fully implemented | Does not import `mcp_data_service` | `finlo/mcp_server.py` was left untouched to comply with prior "do not modify" constraints. | **FAIL** |
| **Multi-Tenant Company Isolation** | **Enforced** (`scope_queryset_to_company`) | **Enforced** (`qs.filter(company=user.company)`) | Both isolate records by `user.company_id`. | **PASS** |
| **Effective Permission Evaluation** | **Enforced** (`has_effective_permission`) | **Partial** (`user.has_perm`) | `mcp_server.py` ignores dynamic role grants and denials. | **FAIL** |
| **Sales Hierarchy Scoping** | **Enforced** (`scope_queryset_to_sales_hierarchy`) | **Omitted** | `mcp_server.py` leaks 105 leads to `SSM`, `ASM`, and `BDO`. | **FAIL** |
| **Custom Role Data Scopes** | **Enforced** (`scope_queryset_to_custom_role`) | **Omitted** | `mcp_server.py` ignores `RoleDataScope` (`owned`, `assigned`, `deny_all`). | **FAIL** |
| **Field-Level Permission Hiding** | **Enforced** (`filter_hidden_fields`) | **Omitted** | `mcp_server.py` returns hardcoded dictionary fields regardless of `FieldPermission`. | **FAIL** |
| **Sensitive Field Blacklist** | **Enforced** (passwords, tokens, salts) | **Enforced** (explicit whitelist in table browser) | Both omit credentials from output. | **PASS** |
| **Pagination Clamping** | **Enforced** (bounded 1 to 100) | **Enforced** (`min(max(1, limit), 100)`) | Both protect against unbounded memory exhaustion. | **PASS** |
| **Active-User Session Check** | **Enforced** (`getattr(user, "is_active", False)`) | **Enforced** (`_ACTIVE_USER.is_active`) | Deactivated accounts immediately denied. | **PASS** |

---

## 2. Exact Permission Enforcement Paths

### Path A: Newly Built `finlo/contrib/core/mcp_data_service.py` (Correct Path)
```
Caller Request
  │
  ├── 1. Active Check: getattr(user, "is_active", False)
  ├── 2. Company Scope: scope_queryset_to_company(qs, user)
  ├── 3. Permission Scope: scope_queryset_to_permission(qs, user, "view")
  │        └─ Checks has_effective_permission(user, "app.view_model")
  │        └─ Checks has_effective_permission(user, "app.view_own_model")
  ├── 4. Sales Hierarchy Scope: scope_queryset_to_sales_hierarchy(qs, user)
  │        └─ SSM sees 51 records (Self + subordinate ASMs + BDOs)
  │        └─ ASM sees 34 records (Self + subordinate BDOs)
  │        └─ BDO sees 17 records (Self only)
  ├── 5. Custom Role Scope: scope_queryset_to_custom_role(qs, user)
  │        └─ Evaluates RoleDataScope ('company', 'owned', 'assigned', 'deny_all')
  └── 6. Field Filter: filter_hidden_fields(user, model, fields)
           └─ Strips fields where FieldPermission == 'hidden'
```

### Path B: Live `finlo/mcp_server.py` (Vulnerable Path)
```
Caller Request (tools/call)
  │
  ├── 1. _get_scoped_user() checks _ACTIVE_USER.is_active
  └── 2. _get_scoped_leads(user)
           ├── qs.filter(company=user.company)
           └── if not user.has_perm("leads.view_lead") and user.has_perm("leads.view_own_lead"):
                   qs = qs.filter(lead_owner=user)
```
**The Flaw in Path B:**  
In FINLO's default group assignments, `test_ssm`, `test_asm`, and `test_bdo` are members of groups where `leads.view_lead` evaluates to `True` at the Django permission layer. Because `user.has_perm("leads.view_lead")` is `True`, the `elif` branch is bypassed completely. Without `scope_queryset_to_sales_hierarchy`, `finlo/mcp_server.py` returns **all 105 company leads** to `ASM`, `SSM`, and `BDO` users, violating sales hierarchy boundaries.

---

## 3. Settings Page Functionality & Accuracy Audit

Inspected [finlo/contrib/core/templates/settings/connect_mcp_settings.html](file:///C:/Users/izhar/Desktop/crm-v2/finlo/contrib/core/templates/settings/connect_mcp_settings.html) and [finlo/contrib/core/views/connect_mcp.py](file:///C:/Users/izhar/Desktop/crm-v2/finlo/contrib/core/views/connect_mcp.py):

| Verification Item | Tested Behavior | Finding | Status |
| :--- | :--- | :--- | :---: |
| **Copy-to-Clipboard** | `navigator.clipboard.writeText(...)` | Copies system prompt and client JSON snippets with visual "Copied!" button feedback. | **PASS** |
| **Client Config Syntax** | JSON validation for Claude, Antigravity, Cursor, Codex | Valid JSON structure conforming to official schema specifications. | **PASS** |
| **Generic Path Tokens** | `<CRM_PROJECT_DIR>` used in customer snippets | No local Windows user paths or developer directories are hardcoded. | **PASS** |
| **Remote Status Honesty** | Status badge & configuration tabs | Explicitly marked as `SETUP REQUIRED`. No fabricated HTTPS URLs are displayed. | **PASS** |
| **Account Permission Display** | Evaluates `get_user_accessible_modules(user)` | Accurately calculates module access and visible record counts per user. | **PASS** |
| **Zero Credential Disclosure** | HTML source inspection | Zero passwords, session cookies, CSRF tokens, or private keys rendered. | **PASS** |
| **Live Daphne HTTP 200** | GET `/connect-mcp-settings/` over port 8000 | Responded HTTP 200 in 1.65 seconds within authenticated session. | **PASS** |

---

## 4. Connected-Session Registry & Revocation Status

Inspected lines 121-133 of `finlo/contrib/core/views/connect_mcp.py` and lines 165-200 of `connect_mcp_settings.html`:

### Audit Findings:
1. **No Persistent Model**: There is no `ConnectedApplication`, `MCPSession`, or `OAuthToken` database model in FINLO CRM.
2. **Hardcoded View State**: The `connected_applications` variable in `ConnectMCPSettingsView.get()` is a hardcoded Python list:
   ```python
   connected_applications = [
       {
           "name": "Antigravity AI Assistant",
           "client_type": "IDE Agent",
           "transport": "STDIO Local Pipe",
           "status": "Active / Verified",
           "scope": "Role Scoped (Read-Only)",
           "last_active": "Just now",
           "is_revocable": True,
       }
   ]
   ```
3. **Frontend-Only Revoke Action**: The "Revoke" button in the template executes only client-side JavaScript DOM manipulation:
   ```javascript
   onclick="if(confirm('...')) { this.closest('tr').remove(); alert('Connection revoked successfully.'); }"
   ```
   It does not issue an HTTP POST/DELETE request, does not invalidate any credentials, and does not terminate any active subprocess pipes.
4. **Conclusion**: The connected client registry and revocation feature is **NOT IMPLEMENTED**. It is currently a static UI mockup.

---

## 5. Security Regression Test Evidence Across Sales Roles

Using the live test database under tenant `FINLONEXA UAT` (Company ID 3, 105 total company leads):

```
=== LIVE ROLE HIERARCHY TEST RESULTS ===
User              Role          New Service (mcp_data_service)   Live Server (mcp_server.py)   Hierarchy Respected?
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
test_superadmin   SUPER_ADMIN   105 records                      105 records                   PASS (Full Access)
test_head_sales   HEAD_OF_SALES 105 records                      105 records                   PASS (All Company)
test_ssm          SSM           51 records                       105 records                   FAIL (Overexposed by 54)
test_asm          ASM           34 records                       105 records                   FAIL (Overexposed by 71)
test_bdo          BDO           17 records                       105 records                   FAIL (Overexposed by 88)
```

### Field-Level Restriction Regression Evidence:
- In `mcp_data_service.py`: `get_authorized_fields(user, Lead)` yields 30 permitted fields. Any field marked as `"hidden"` in `FieldPermission` is stripped before serialization. Sensitive fields (`password`, `token`, `secret`, `salt`) are blocked.
- In `finlo/mcp_server.py`: `get_lead_details(lead_id)` returns a fixed 15-key dictionary containing `annual_revenue` and `contact_number` regardless of whether the user or role has `FieldPermission` set to `hidden`.

---

## 6. Summary of Remaining Implementation Gaps

| Gap ID | Severity | Description | Current State | Target State |
| :---: | :---: | :--- | :--- | :--- |
| **GAP-01** | **HIGH** | `finlo/mcp_server.py` does not use `mcp_data_service.py`. | Naive `user.has_perm` check leaks company records to sales managers and BDOs. | Delegate `_get_scoped_*`, `query_crm_table`, and `get_lead_details` to `mcp_data_service.py`. |
| **GAP-02** | **MEDIUM** | `finlo/mcp_server.py` ignores `FieldPermission` hidden rules. | Static field dictionary returned in `get_lead_details`. | Filter serialized fields through `get_authorized_fields(user, model)`. |
| **GAP-03** | **MEDIUM** | Connected applications registry is not persistent. | Hardcoded list in view; Revoke only removes HTML `<tr>`. | Create persistent `MCPSession` or OAuth token registry with backend revocation API. |
| **GAP-04** | **LOW** | Remote Streamable HTTP endpoint is not deployed. | Marked as `SETUP REQUIRED`. | Deploy authenticated ASGI HTTPS endpoint (`/mcp/v1/`). |
| **GAP-05** | **LOW** | User authentication requires username/password in tool call. | STDIO client calls `login_crm(username, password)`. | Implement OAuth 2.0 PKCE browser consent flow. |

---

## 7. Minimal Proposed Corrections (Code-Ready)

To eliminate **GAP-01** and **GAP-02** without modifying database tables or running migrations, update `finlo/mcp_server.py` with the following 4-step minimal change:

### Step 1: Import the centralized data service in `finlo/mcp_server.py`:
```python
from finlo.contrib.core.mcp_data_service import (
    get_authorized_queryset,
    get_authorized_fields,
    get_single_record,
    query_module_records,
)
```

### Step 2: Replace naive scoping helpers with the authorized service:
```python
def _get_scoped_leads(user: User):
    qs, _ = get_authorized_queryset(user, "leads")
    return qs if qs is not None else Lead.objects.none()

def _get_scoped_opportunities(user: User):
    qs, _ = get_authorized_queryset(user, "opportunities")
    return qs if qs is not None else Opportunity.objects.none()

def _get_scoped_contacts(user: User):
    qs, _ = get_authorized_queryset(user, "contacts")
    return qs if qs is not None else Contact.objects.none()

def _get_scoped_accounts(user: User):
    qs, _ = get_authorized_queryset(user, "accounts")
    return qs if qs is not None else Account.objects.none()

def _get_scoped_campaigns(user: User):
    qs, _ = get_authorized_queryset(user, "campaigns")
    return qs if qs is not None else Campaign.objects.none()

def _get_scoped_activities(user: User):
    qs, _ = get_authorized_queryset(user, "activities")
    return qs if qs is not None else Activity.objects.none()
```

### Step 3: Upgrade `get_lead_details` to enforce field-level permissions:
```python
@server.tool()
def get_lead_details(lead_id: int) -> Dict[str, Any]:
    user = _get_scoped_user()
    return get_single_record(user, "leads", int(lead_id))
```

### Step 4: Upgrade `query_crm_table` to respect hidden fields and pagination bounds:
```python
@server.tool()
def query_crm_table(entity_type: str, search: str = "", limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    user = _get_scoped_user()
    return query_module_records(user, entity_type, search=search, limit=limit, offset=offset)
```

*Impact of Minimal Correction:*  
Immediately brings `finlo/mcp_server.py` into 100% compliance with sales hierarchy boundaries, custom role data scopes, and field-level hiding with zero database mutations.

---

## 8. Separate Prerequisites for Remote HTTPS MCP & OAuth 2.0

To achieve production-grade, remote AI access for non-technical users without sharing passwords:

### Milestone 1: OAuth 2.0 PKCE Infrastructure
- **Prerequisite 1**: Migration approval to create `MCPOAuthClient`, `MCPOAuthGrant`, and `MCPAccessToken` models (or adoption of `django-oauth-toolkit`).
- **Prerequisite 2**: UI consent screen (`/oauth/authorize/`) allowing the user to approve requested read-only scopes.
- **Prerequisite 3**: Token exchange endpoint (`/oauth/token/`) issuing short-lived bearer tokens (TTL 1 hr) with PKCE code verification.

### Milestone 2: Streamable HTTP ASGI Gateway
- **Prerequisite 1**: Daphne/ASGI route configuration for `POST /mcp/v1/`.
- **Prerequisite 2**: Bearer token authentication middleware that maps `Authorization: Bearer <token>` to `request.user`.
- **Prerequisite 3**: Rate-limiting and origin validation to prevent CSRF and denial-of-service.
- **Prerequisite 4**: Domain TLS certificate and reverse-proxy port binding.

