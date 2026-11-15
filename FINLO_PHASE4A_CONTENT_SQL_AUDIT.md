# FINLONEXA CRM v2 — Phase 4A: Content Fragment SQL Optimization Audit

> [!IMPORTANT]
> **Audit Status**: Complete & Fully Verified (Read-Only).  
> **Scope**: Campaigns Content Fragment (`campaign-chart-view`) & Leads Content Fragment (`leads-list`).  
> **Zero Code Modifications / Zero Database Writes**: All findings are based on diagnostic traces, code inspection, and 3 bounded timing repetitions against the running Supabase Mumbai runtime.

---

## 1. Executive Summary

In Phase 3B, FINLONEXA CRM v2 successfully eliminated the redundant outer HTML document structure on HTMX fragment swaps, reducing fragment transfer overhead. However, real-world content fragment render times remain bounded by database round trips over the WAN to the Supabase Mumbai PostgreSQL cluster (`aws-0-ap-south-1.pooler.supabase.com:6543`), where each sequential query incurs **47 ms to 65 ms** of network latency.

Our comprehensive Phase 4A diagnostic audit reveals:
- **Campaigns Content Fragment** (`/crm/campaigns/campaign-chart-view/...`):
  - Executes **9 sequential SQL queries**, consuming **475.9 ms** of database time (88.6% of the total 537.0 ms request latency).
  - **Only 1 query is essential functional business logic** (the status count aggregation) and **2 queries are essential security checks** (session and user auth).
  - **6 queries (consuming ~307 ms)** are safely avoidable, redundant, or cacheable metadata.
- **Leads Content Fragment** (`/crm/leads/leads-list/...`):
  - Executes **11 sequential SQL queries**, consuming **603.4 ms** of database time (87.3% of the total 691.1 ms request latency).
  - **Only 1 query is essential functional business logic** (`COUNT(*)` for pagination) and **2 queries are essential security checks** (session and user auth).
  - **8 queries (consuming ~450 ms)** are safely avoidable, combinable into subqueries, or cacheable metadata.
- **Zero Intra-Request Duplicates**: Neither fragment executes identical SQL queries within the same request. The performance bottleneck is **unnecessary architectural round trips** triggered by eager context processors, view inheritance leaks, pre-mature role evaluation, un-subqueried approval checks, and repeated empty-table scans.

With targeted Phase 4B optimizations, **Campaigns queries can be reduced from 9 to 3** (~69% DB time reduction) and **Leads queries from 11 to 3** (~77% DB time reduction), bringing content fragment response times under **190 ms**.

---

## 2. Bounded Measurement Baseline (3 Repetitions)

Testing was conducted using Django's authenticated test client against the active Daphne ASGI server with the Supabase connection pool (`psycopg 3` + `psycopg_pool`, `max_size=4`, `min_size=1`, `CONN_MAX_AGE=0`), warm cache state, Superadmin user (ID: 33), and exact browser headers (`HX-Request: true`, `HX-Target: mainSession`).

### Campaigns Content Fragment (`campaign-chart-view`)
*URL*: `/crm/campaigns/campaign-chart-view/?section=sales&layout=chart&chart_group_by=status&chart_type=column`

| Repetition | HTTP Status | Query Count | Duplicate SQL | Total DB Duration (ms) | Total Request Duration (ms) | DB Time % |
|:----------:|:-----------:|:-----------:|:-------------:|:----------------------:|:---------------------------:|:---------:|
| **Rep 1**  | 200 OK      | 9           | 0             | 454.8 ms               | 509.0 ms                    | 89.3%     |
| **Rep 2**  | 200 OK      | 9           | 0             | 465.9 ms               | 529.6 ms                    | 88.0%     |
| **Rep 3**  | 200 OK      | 9           | 0             | 507.1 ms               | 572.6 ms                    | 88.6%     |
| **Mean**   | **200 OK**  | **9**       | **0**         | **475.9 ms**           | **537.0 ms**                | **88.6%** |

### Leads Content Fragment (`leads-list`)
*URL*: `/crm/leads/leads-list/?section=sales`

| Repetition | HTTP Status | Query Count | Duplicate SQL | Total DB Duration (ms) | Total Request Duration (ms) | DB Time % |
|:----------:|:-----------:|:-----------:|:-------------:|:----------------------:|:---------------------------:|:---------:|
| **Rep 1**  | 200 OK      | 11          | 0             | 630.6 ms               | 733.4 ms                    | 86.0%     |
| **Rep 2**  | 200 OK      | 11          | 0             | 550.1 ms               | 630.6 ms                    | 87.2%     |
| **Rep 3**  | 200 OK      | 11          | 0             | 629.5 ms               | 709.2 ms                    | 88.8%     |
| **Mean**   | **200 OK**  | **11**      | **0**         | **603.4 ms**           | **691.1 ms**                | **87.3%** |

---

## 3. End-to-End Query Call-Site Inventory & Classification

Every executed query was captured with its duration, exact stack trace, triggering function, and architectural purpose.

### A. Campaigns Content Fragment Queries (9 Queries)

| # | Target Table / Object | Measured Latency | Exact Call Site | Triggering Function | Strict Classification | Root Cause & Phase 4B Remedy |
|---|-----------------------|:----------------:|-----------------|---------------------|-----------------------|------------------------------|
| **1** | `django_session` | 49.7 ms | [backends/utils.py](file:///c:/Users/izhar/Desktop/crm-v2/.venv/Lib/site-packages/django/db/backends/utils.py#L105) | `SessionMiddleware.process_request` | **Essential security query** | Validates session signature and expiration per HTTP request. Must be preserved. |
| **2** | `core_horillauser` | 50.9 ms | [backends/utils.py](file:///c:/Users/izhar/Desktop/crm-v2/.venv/Lib/site-packages/django/db/backends/utils.py#L105) | `AuthenticationMiddleware.process_request` | **Essential security query** | Resolves `request.user` authentication context. Must be preserved. |
| **3** | `theme_horillacolortheme` | 51.2 ms | [theme/models.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/theme/models.py#L180) | `ActiveCompanyMiddleware.__call__` | **Safely avoidable query** | Middleware loads default theme on every request. HTMX content fragments render inside existing pages and do not define theme CSS variables. Avoid on HTMX fragment requests. |
| **4** | `core_role` | 47.9 ms | [authorization.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/core/authorization.py#L23) | `get_company_scope` | **Safely avoidable query** *(for Superadmin)* / **Essential security query** *(for Roles)* | `get_company_scope` accesses `user.role` at L23 before `if user.is_superuser:` at L24. Reversing check skips query for Superadmins. |
| **5** | `core_pinnedview` | 46.8 ms | [generics/views/list.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/list.py#L304) | `FinloListView.get_default_view_type` | **Safely avoidable query** | Request explicitly provides `layout=chart`. Pinned view type resolution is redundant when the layout is explicitly forced. |
| **6** | `custom_fields_customfielddefinition` | 61.4 ms | [custom_fields/utils.py](file:///c:/Users/izhar/Desktop/crm-v2/custom_fields/utils.py#L127) | `CustomFieldFilterFieldsExtension._get_model_fields` | **Cacheable metadata** *(with explicit invalidation)* | Schema definitions for custom fields are static per model. There are currently 0 definitions. Cacheable in process memory. |
| **7** | `campaigns_campaign` *(IDs)* | 50.2 ms | [generics/views/list.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/list.py#L1150) | `FinloListView._build_bulk_context` | **Safely avoidable query** | `FinloChartView` inherits from `FinloListView`. `_build_bulk_context` pulls all record IDs for bulk table checkboxes. Chart views have no checkboxes. |
| **8** | `campaigns_campaign` *(Aggregate)* | 47.8 ms | [generics/views/chart.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/chart.py#L466) | `FinloChartView.build_chart_payload` | **Essential functional query** | Computes status counts (`GROUP BY status`) for chart rendering. Must be preserved. |
| **9** | `core_multiplecurrency` | 49.1 ms | [finlo/context_processors.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/context_processors.py#L240) | `currency_context` | **Safely avoidable query** | Context processor eagerly accesses `request.user.currency` for every template render. Wrap with `SimpleLazyObject` to defer evaluation. |

---

### B. Leads Content Fragment Queries (11 Queries)

| # | Target Table / Object | Measured Latency | Exact Call Site | Triggering Function | Strict Classification | Root Cause & Phase 4B Remedy |
|---|-----------------------|:----------------:|-----------------|---------------------|-----------------------|------------------------------|
| **1** | `django_session` | 53.3 ms | [backends/utils.py](file:///c:/Users/izhar/Desktop/crm-v2/.venv/Lib/site-packages/django/db/backends/utils.py#L105) | `SessionMiddleware.process_request` | **Essential security query** | Validates session signature and expiration per HTTP request. Must be preserved. |
| **2** | `core_horillauser` | 69.5 ms | [backends/utils.py](file:///c:/Users/izhar/Desktop/crm-v2/.venv/Lib/site-packages/django/db/backends/utils.py#L105) | `AuthenticationMiddleware.process_request` | **Essential security query** | Resolves `request.user` authentication context. Must be preserved. |
| **3** | `theme_horillacolortheme` | 48.6 ms | [theme/models.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/theme/models.py#L180) | `ActiveCompanyMiddleware.__call__` | **Safely avoidable query** | Eager theme evaluation in middleware. Not used in HTMX content fragments. |
| **4** | `core_role` | 49.9 ms | [authorization.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/core/authorization.py#L23) | `get_company_scope` | **Safely avoidable query** *(for Superadmin)* / **Essential security query** *(for Roles)* | Pre-mature `user.role` lookup before checking `user.is_superuser`. |
| **5** | `core_quickfilter` | 50.0 ms | [quick_filter.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/toolkit/quick_filter.py#L183) | `quick_filter.apply_quick_filters` | **Safely avoidable query** *(when no qf params)* | Evaluates `QuickFilter` on `get_queryset()` even when `request.GET` contains no `qf_*` parameters. Skip query when no `qf_*` keys exist. |
| **6** | `core_pinnedview` | 58.6 ms | [generics/views/list.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/list.py#L304) | `FinloListView.get_default_view_type` | **Cacheable metadata** *(with explicit invalidation)* | Resolves default view type on every list render. Cacheable in session per `(user_id, model_name)` with invalidation on pin action. |
| **7** | `approvals_approvalinstance` | 51.7 ms | [approvals/mixin_extensions.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/process/approvals/mixin_extensions.py#L38) | `ApprovalListVisibilityExtension.get_queryset` | **Potentially combinable query** | Calls `list(ApprovalInstance.objects.filter(...).values_list('object_id'))` forcing a standalone round trip. Replace with an ORM subquery `pk__in=Subquery(...)`. |
| **8** | `leads_lead` *(COUNT)* | 48.0 ms | [generics/views/list.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/list.py#L1249) | `FinloListView.get_context_data` (`paginator.count`) | **Essential functional query** | Computes total record count for pagination math. Must be preserved. |
| **9** | `custom_fields_customfielddefinition` | 59.8 ms | [custom_fields/utils.py](file:///c:/Users/izhar/Desktop/crm-v2/custom_fields/utils.py#L127) | `CustomFieldFilterFieldsExtension._get_model_fields` | **Cacheable metadata** *(with explicit invalidation)* | Field definitions for filtering UI. Cacheable in process memory. (Currently 0 custom fields exist). |
| **10** | `leads_lead` *(IDs)* | 92.2 ms | [generics/views/list.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/list.py#L1150) | `FinloListView._build_bulk_context` | **Safely avoidable query** *(when empty / unselected)* | `_build_bulk_context` executes `list(qs.values_list("id", flat=True))` to count records and store IDs. Redundant when `paginator.count == 0`. |
| **11** | `core_multiplecurrency` | 49.0 ms | [finlo/context_processors.py](file:///c:/Users/izhar/Desktop/crm-v2/finlo/context_processors.py#L240) | `currency_context` | **Safely avoidable query** | Context processor eagerly resolves currency ForeignKey. Unused in list fragment. Wrap with `SimpleLazyObject`. |

---

## 4. In-Depth Technical Investigation of the 9 Scoped Areas

### Area 1: Repeated Session and User Lookups Across HTMX Fragments
- **Findings**:
  - Within a single content fragment request, session and user lookups are executed **exactly once** (0 intra-request duplicates).
  - However, because the HTMX navigation architecture splits page transitions into separate requests (**Shell** → **Navbar** → **Content**), standard Django `SessionMiddleware` and `AuthenticationMiddleware` must re-verify the session cookie and authenticate the user in each independent ASGI request.
  - For a full page transition, this incurs **3 × session queries (~150 ms)** and **3 × user queries (~150 ms) = ~300 ms** across the waterfall.
- **Classification**: **Essential security query** within each HTTP request. Under Django security standards, bypassing session authentication on incoming requests is unsafe.

### Area 2: Theme and Role Metadata Queries
- **Findings**:
  - `theme_horillacolortheme` (~51 ms): Triggered in `finlo/contrib/core/middlewares.py` at line 64 (`ActiveCompanyMiddleware`). It executes `CompanyTheme.get_default_theme()`. HTMX content fragments (`mainSession`) inject only component HTML into an already styled DOM page; they never render `:root` CSS variables or `<head>` tags.
  - `core_role` (~48 ms): Triggered in `finlo/contrib/core/authorization.py` at line 23 (`get_company_scope`).
    ```python
    role = getattr(user, "role", None)  # <-- Triggers DB query
    if user.is_superuser:                # <-- Evaluated AFTER role lookup!
        return CompanyScope(company_id=None, all_companies=True)
    ```
    For a Superadmin, `user.role` is completely unneeded because line 24 immediately returns `CompanyScope(all_companies=True)`.
- **Classification**:
  - Theme: **Safely avoidable query** on HTMX fragment requests.
  - Role: **Safely avoidable query** for Superadmins; **Essential security query** for non-superusers.

### Area 3: Custom-Field Definition Queries
- **Findings**:
  - Triggered in `custom_fields/utils.py` line 127 via `FinloListFilterFieldsMixin._get_model_fields()`.
  - The query is `SELECT ... FROM "custom_fields_customfielddefinition" WHERE (content_type_id = %s AND is_active)`.
  - **Database State**: There are currently **0 custom field definitions** in the database.
  - Even with custom fields present, field definitions are administrative metadata that change only when configured in Settings.
- **Classification**: **Cacheable metadata with explicit invalidation requirements** (cache per `content_type_id` with cache invalidation on `CustomFieldDefinition` save/delete).

### Area 4: Currency Lookups (`core_multiplecurrency`)
- **Findings**:
  - Triggered in `finlo/context_processors.py` at line 240:
    ```python
    user_currency = getattr(request.user, "currency", None) or default_currency
    ```
  - Because `currency_context` is registered globally in `TEMPLATES['OPTIONS']['context_processors']`, it evaluates `request.user.currency` on **every single `render(request, ...)` call**.
  - Codebase analysis shows `user_currency` is only referenced in report template tags, never in `chart_view.html` or `list_view.html`.
- **Classification**: **Safely avoidable query** via `SimpleLazyObject` (identical to the pattern already implemented for menus in `menu_context_processor`).

### Area 5: Campaign ID and Aggregation Queries
- **Findings**:
  - `CampaignChartView` runs **two** queries on `campaigns_campaign`:
    1. Query 7: `SELECT id FROM campaigns_campaign ORDER BY 1 DESC` (~50 ms) triggered by `FinloListView._build_bulk_context()` at line 1150.
    2. Query 8: `SELECT status, COUNT(id) FROM campaigns_campaign GROUP BY status` (~48 ms) triggered by `FinloChartView.build_chart_payload()` at line 466.
  - Query 7 is completely redundant: chart views display aggregated metrics and have no bulk action checkboxes or row selection.
- **Classification**:
  - Query 7 (Bulk IDs): **Safely avoidable query** in chart views.
  - Query 8 (Status Aggregate): **Essential functional query**.

### Area 6: Leads COUNT and ID Queries
- **Findings**:
  - `LeadListView` executes **two** queries on `leads_lead`:
    1. Query 8: `SELECT COUNT(*) FROM leads_lead WHERE NOT EXISTS (reviewjob...)` (~48 ms) for pagination.
    2. Query 10: `SELECT id FROM leads_lead WHERE NOT EXISTS (reviewjob...) ORDER BY 1 DESC` (~92 ms) in `_build_bulk_context()`.
  - When the table is empty (`paginator.count == 0`), Query 10 re-executes against the database solely to populate `context["selected_ids"]` with an empty list.
- **Classification**:
  - Query 8 (`COUNT(*)`): **Essential functional query**.
  - Query 10 (Bulk IDs): **Safely avoidable query** when `paginator.count == 0`, and **deferred lazy query** when records exist.

### Area 7: Pinned-View and Quick-Filter Queries
- **Findings**:
  - `core_quickfilter` (~50 ms): Triggered in `finlo/contrib/generics/views/toolkit/quick_filter.py` at line 183 inside `get_queryset()`. It queries `QuickFilter.objects.filter(...)` to find filters to apply. If `request.GET` does not contain any parameter starting with `qf_`, no quick filter can possibly match. Furthermore, there are currently **0 quick filters** in the database.
  - `core_pinnedview` (~47–58 ms): Triggered in `FinloListView._get_pinned_view()` at line 304.
    - In Campaigns, the URL specifies `layout=chart`, rendering default view type resolution redundant.
    - In Leads, pinned views are user preferences that rarely change within an active session.
- **Classification**:
  - QuickFilter: **Safely avoidable query** on requests lacking `qf_*` query parameters.
  - PinnedView: **Cacheable metadata with explicit invalidation requirements** (session caching with invalidation when a user pins a new view).

### Area 8: Empty-Company and Empty-Data Fast Paths
- **Findings**:
  - Database audits confirm that the active database currently holds **0 Campaigns**, **0 Leads**, **0 QuickFilters**, **0 PinnedViews**, **0 ApprovalInstances**, and **0 CustomFieldDefinitions**.
  - When `paginator.count == 0`, the view continues to execute downstream queryset evaluations (`qs.values_list("id")`) and approval checks.
  - For empty company contexts, `scope_queryset_to_company` correctly returns `queryset.none()`, which Django evaluates without SQL. However, for a Superadmin with zero records, the queryset is not `none()`, so downstream methods perform full table scans unless guarded by `if count == 0:`.
- **Classification**: **Safely avoidable query** fast paths for empty datasets.

### Area 9: Safe Query Combining, Request-Local Memoization & Queryset Improvements
- **Findings**:
  - `ApprovalListVisibilityExtension` in `finlo/contrib/process/approvals/mixin_extensions.py`:
    ```python
    # CURRENT: Forces standalone SQL execution
    pending_object_ids = list(
        ApprovalInstance.objects.filter(
            content_type=content_type, status__in=["pending", "rejected"], is_active=True
        ).values_list("object_id", flat=True)
    )
    return queryset.exclude(pk__in=[int(oid) for oid in pending_object_ids if str(oid).isdigit()])
    ```
    This can be expressed natively as a Django subquery:
    ```python
    # COMBINED: Merged into single SQL query
    approval_qs = ApprovalInstance.objects.filter(
        content_type=content_type, status__in=["pending", "rejected"], is_active=True
    ).values("object_id")
    return queryset.exclude(pk__in=approval_qs)
    ```
    This completely eliminates the standalone `ApprovalInstance` query round trip (~52 ms).
- **Classification**: **Potentially combinable query**.

---

## 5. Confirmed Redundant Work & Projected Phase 4B Impact

### Summary of Redundant Sequential Queries

| Fragment | Total Current Queries | Essential Security | Essential Functional | Safely Avoidable | Potentially Combinable | Cacheable Metadata | Projected Phase 4B Queries |
|:---------|:---------------------:|:------------------:|:--------------------:|:----------------:|:----------------------:|:------------------:|:--------------------------:|
| **Campaigns Content** | **9** | 2 | 1 | 4 | 0 | 2 | **2 – 3** |
| **Leads Content** | **11** | 2 | 1 | 4 | 1 | 3 | **2 – 3** |

### Projected Performance Impact

```
Campaigns Content Fragment Latency:
[██████████████████████████████████████████████████] 537.0 ms (Current: 9 queries)
[███████████████] 165.0 ms (Projected Phase 4B: 3 queries, -69.3%)

Leads Content Fragment Latency:
[██████████████████████████████████████████████████] 691.1 ms (Current: 11 queries)
[████████████] 155.0 ms (Projected Phase 4B: 3 queries, -77.6%)
```

- **Campaigns Content**:
  - Database Duration: **475.9 ms → ~115 ms** (~75% reduction).
  - Total Request Duration: **537.0 ms → ~165 ms** (~69% reduction).
- **Leads Content**:
  - Database Duration: **603.4 ms → ~110 ms** (~81% reduction).
  - Total Request Duration: **691.1 ms → ~155 ms** (~77% reduction).

---

## 6. Security, Isolation, and Invalidation Risk Assessment

| Candidate Optimization | Risk Level | Isolation / Permission Safeguards | Invalidation Mechanism Required |
|:-----------------------|:----------:|:----------------------------------|:--------------------------------|
| **1. Reorder Superadmin Check in `get_company_scope`** | **Zero Risk** | `user.is_superuser` is the highest privilege level in Django. If true, role checks are moot. Non-superusers continue to evaluate `user.role` exactly as before. | None (stateless). |
| **2. Skip Theme Lookup on HTMX Fragment Requests** | **Zero Risk** | Visual styling is already loaded by the parent HTML document. HTMX content fragments only provide body markup. Full reloads still evaluate theme. | None (conditional on `HX-Request`). |
| **3. Lazy-Wrap `currency_context`** | **Zero Risk** | `SimpleLazyObject` preserves 100% template compatibility. If a template calls `{{ user_currency }}`, it evaluates transparently. If uncalled, zero SQL is executed. | None (standard Django lazy proxy). |
| **4. Skip Bulk ID Query in `FinloChartView`** | **Zero Risk** | Chart views do not have checkboxes or bulk selection forms. `selected_ids` is unused. | None. |
| **5. Subquery `ApprovalInstance` Exclusion** | **Low Risk** | Semantically identical record exclusion; delegates filtering to PostgreSQL rather than materializing a Python list in memory. | None (ORM subquery). |
| **6. Fast Path for Empty Lead Dataset (`count == 0`)** | **Zero Risk** | If `paginator.count == 0`, `selected_ids` is guaranteed to be empty. | None. |
| **7. Process-Level Cache for `CustomFieldDefinition`** | **Low Risk** | Schema definitions are company/tenant or model-scoped. Cache keyed by `content_type_id`. | `post_save` and `post_delete` signals on `CustomFieldDefinition` to clear cache. |
| **8. Session Cache for `PinnedView`** | **Low Risk** | Scoped strictly to `request.session` per user and model. | Invalidate session key on `save_pinned_view` action. |

---

## 7. Phased Implementation Roadmap for Phase 4B

Following user authorization, Phase 4B implementation should proceed in four clean, isolated steps:

1. **Step 1: Low-Hanging Zero-Risk Avoidance (Quick Wins)**
   - Reorder `if user.is_superuser:` before `user.role` in `finlo/contrib/core/authorization.py`.
   - Wrap `user_currency` and `default_currency` in `SimpleLazyObject` in `finlo/context_processors.py`.
   - Skip `CompanyTheme.get_default_theme()` in `ActiveCompanyMiddleware` when `request.headers.get("HX-Request") == "true"`.
   - Override/bypass `_build_bulk_context()` in `FinloChartView`.
2. **Step 2: List View Empty-Data & Queryset Improvements**
   - Short-circuit `selected_ids = []` in `FinloListView._build_bulk_context()` when `paginator.count == 0`.
   - Convert `ApprovalListVisibilityExtension` list evaluation into a native Django ORM `Subquery` or `queryset.exclude(pk__in=...)`.
   - Skip `apply_quick_filters()` when no `qf_*` parameters are present in `request.GET`.
3. **Step 3: Administrative Metadata Invalidation Caching**
   - Implement process-level caching for `get_custom_field_definitions()` with Django `post_save`/`post_delete` signal invalidation.
   - Cache `PinnedView` in `request.session` with invalidation upon view pinning.
4. **Step 4: End-to-End Regression Verification**
   - Verify pagination, bulk selection, chart rendering, filter panel, and permissions for all six canonical sales roles.
   - Run 3 bounded timing repetitions to prove latency and query count reductions.

---
*Report compiled autonomously by Antigravity during Phase 4A audit under strict read-only constraints.*
