# FINLONEXA CRM v2 — Phase 3 Performance Audit & Optimization Report
**First-Load Performance & HTMX Waterfall Consolidation**

**Date:** November 10, 2026  
**Environment:** Windows 11, Django 6 + Daphne ASGI, PostgreSQL (Supabase Mumbai Transaction Pooler port 6543), Redis / LocMemCache, HTMX + Alpine.js, Google Chrome Headless CDP Suite.

---

## Executive Summary

Phase 03 targeted the cold first-visit experience across all primary CRM pages. Previously, navigating to any generic view (Leads, Accounts, Contacts, Opportunities, Activities) triggered a **three-hop HTMX waterfall** across the network, executing multiple redundant round-trips to Supabase Mumbai and repeating authentication, session, and role queries on each hop.

Through server-side component pre-rendering, Kanban single-query batching, and dashboard ForeignKey eager-loading, we achieved:
- **First-Load HTTP Requests:** Reduced from **3 sequential round trips to 1 single consolidated request** across all generic views.
- **Opportunities Kanban:** First-load time reduced from **2,480.1 ms to 1,399.1 ms (-43.6%)**, cutting SQL queries from **35 to 23** (eliminating 11 N+1 queries).
- **Accounts Chart First Load:** Reduced from **1,258.3 ms to 815.8 ms (-35.2%)**, cutting SQL queries from **21 to 13**.
- **Leads Chart First Load:** Reduced from **1,561.3 ms to 1,121.8 ms (-28.1%)**, cutting SQL queries from **22 to 14**.
- **Activities First Load:** Reduced from **951.3 ms to 553.9 ms (-41.8%)**, cutting SQL queries from **16 to 8**.
- **Dashboard First Paint:** Reduced from **3,556.5 ms to 1,364.0 ms** in real Google Chrome (surpassing the <1,500 ms target).
- **Dashboard N+1 Queries:** Eliminated 10 repetitive template rendering queries via relation auto-selection.
- **Repeat Navigation:** Maintained sub-10 ms restoration (**6.7 ms** in Chrome CDP).
- **Unsaved Form & Modal Safety:** Added full dirty checking (`value !== defaultValue`, open modals, rich-text editors) preventing background SWR from clobbering active user edits.
- **Security & Authorization:** 100% verified across sales roles; 0 record leakage; unauthenticated access safely blocked with 302.

---

## 1. Measured Performance Baseline (Phase 3.1)

All baseline tests were conducted on cold loads (in-memory navigation cache cleared) with the live Daphne ASGI server and Supabase Mumbai transaction pooler.

| Page / Route | Initial Hops | Total Time (ms) | SQL Execution Time (ms) | Total Queries | Transferred (Bytes) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Dashboard** (`/dashboard/?section=home`) | 1 | 3,860.1 ms | 2,718.0 ms | 45 | 378,302 B | 200 OK |
| **2. Leads — List** (`/crm/leads/...&layout=list`) | **3** | 1,886.5 ms | 1,499.0 ms | 27 | 445,591 B | 200 OK |
| **3. Leads — Chart** (`/crm/leads/...&layout=chart`) | **3** | 1,561.3 ms | 1,172.0 ms | 22 | 109,548 B | 200 OK |
| **4. Accounts — List** (`/crm/accounts/...&layout=list`) | **3** | 1,852.1 ms | 1,468.0 ms | 27 | 395,712 B | 200 OK |
| **5. Accounts — Chart** (`/crm/accounts/...&layout=chart`) | **3** | 1,258.3 ms | 1,110.0 ms | 21 | 108,916 B | 200 OK |
| **6. Contacts** (`/crm/contacts/...`) | **3** | 1,459.6 ms | 1,282.0 ms | 25 | 104,434 B | 200 OK |
| **7. Opportunities — List** (`/crm/opportunities/...&layout=list`) | **3** | 1,875.0 ms | 1,467.0 ms | 28 | 392,998 B | 200 OK |
| **8. Opportunities — Kanban** (`...&layout=kanban`) | **3** | 2,480.1 ms | 2,093.0 ms | 35 | 518,705 B | 200 OK |
| **9. Activities** (`/activity/...`) | **3** | 951.3 ms | 859.0 ms | 16 | 72,223 B | 200 OK |
| **10. Calendar** (`/calendar/...`) | 1 | 447.2 ms | 392.0 ms | 7 | 148,790 B | 200 OK |
| **11. Settings** (`/settings-view/...`) | 1 | 337.5 ms | 265.0 ms | 5 | 48,623 B | 200 OK |

---

## 2. Root Cause Analysis

### Bottleneck A: The Triple-Hop HTMX Waterfall
In `finlo/contrib/generics/templates/base.html`, generic views originally returned empty placeholder `<div>` tags with `hx-trigger="load"`:
```html
<!-- Hop 1: Empty shells with load triggers -->
<div id="navBar" hx-get="{{ nav_url }}" hx-trigger="load"></div>
<div id="mainSession" hx-get="{{ layout_url }}" hx-trigger="load">...</div>
```
When the client browser processed the HTML response of Hop 1, HTMX fired **two additional HTTP requests** over the network:
1. `Hop 2` fetched the navigation bar partial (`nav_url`).
2. `Hop 3` fetched the table/chart layout partial (`layout_url`).

Because every request is an independent HTTP round trip, the user had to wait for all three sequential/parallel network hops across the internet before seeing usable content.

### Bottleneck B: Redundant Database Queries Across Hops
Because Hops 1, 2, and 3 were distinct HTTP requests, Django had to repeatedly execute common infrastructure queries on every hop:
- `SELECT session_data FROM django_session` (3x)
- `SELECT core_horillauser` (3x)
- `SELECT core_company` (3x)
- `SELECT core_role` (3x)
- `SELECT core_pinnedview` (2x)

Between 8 and 14 duplicate queries were issued per page load simply due to request fragmentation.

### Bottleneck C: N+1 Per-Stage Queries in Opportunities Kanban
In `finlo/contrib/generics/views/kanban.py`, `FinloKanbanView.get_context_data()` looped through each column (stage) and evaluated `page_obj.object_list`. For 10 stages, this executed **10 separate SELECT queries** sequentially across the Mumbai pooler connection (adding ~650 ms of network latency).

### Bottleneck D: N+1 Template Foreign Key Lookups in Dashboard
In `finlo/contrib/dashboard/utils.py`, `DefaultDashboardGenerator.build_table_context` only eager-loaded `company`. When rendering the recent Opportunities table, the template accessed `opp.account.name` and `opp.stage.name`, issuing 10 individual SQL queries during template rendering.

---

## 3. Optimizations Implemented

### 1. Server-Side Consolidated Subview Pre-Rendering (`FinloView`)
In `finlo/contrib/generics/views/core.py`, added `_render_subview(self, url_str)` to `FinloView`. When rendering the initial page, `FinloView` resolves `self.nav_url` and `layout_url = self.get_layout_url()` in-process and passes their rendered HTML into template context as `rendered_navbar` and `rendered_main_session`.

In `finlo/contrib/generics/templates/base.html`:
```html
{% block navbar %}
<div id="navBar" class="w-full"{% if not rendered_navbar %}
    hx-get="{{ nav_url }}{% if request.GET.urlencode %}{% if '?' in nav_url %}&{% else %}?{% endif %}{{ request.GET.urlencode }}{% endif %}"
    hx-trigger="load"{% endif %}>{% if rendered_navbar %}{{ rendered_navbar|safe }}{% endif %}</div>
{% endblock navbar %}

{% block main %}
{% with query=request.GET.urlencode %}
<div class="p-5 h-full pt-24 flex flex-col min-h-0" style="position: relative" id="mainSession"{% if not rendered_main_session %}
    hx-get="{{ layout_url }}..." hx-trigger="load" hx-indicator="#loading-indicator" hx-disinherit="*"{% endif %}>
    {% if rendered_main_session %}
        {{ rendered_main_session|safe }}
    {% else %}
        <div id="loading-indicator" class="htmx-indicator" ...>...</div>
    {% endif %}
</div>
{% endwith %}
{% endblock main %}
```
- **Fallback Guarantee:** If subview resolution encounters any error or missing kwargs, it returns `""` and cleanly falls back to the original `hx-trigger="load"`.
- **HTMX Dynamic Switchers Intact:** Layout switchers, search bars, pagination, and filters continue to target `#mainSession` and `#navBar` as independent endpoints.

### 2. Single-Query Batched Retrieval for Kanban (`FinloKanbanView`)
In `finlo/contrib/generics/views/kanban.py`, when columns are on page 1 and item counts are within `self.paginate_by`, items across all active columns are retrieved in **one single SQL query** using `stage_id__in=active_keys` and partitioned in Python:
```python
can_batch = all(
    self.request.GET.get(f"page_{k}", "1") == "1"
    and group["_total_count"] <= self.paginate_by
    for k, group in sorted_items.items()
)
if can_batch and active_keys:
    all_qs = queryset.filter(**{f"{group_by}__in": active_keys}).order_by(*order_by_tuple)
```
Preserves exact stage ordering, column counts, and permission scoping while cutting 10 round trips down to 1.

### 3. Dashboard Eager Foreign Key Loading (`build_table_context`)
In `finlo/contrib/dashboard/utils.py`, `build_table_context` now resolves `table_fields` upfront, detects all `many_to_one` relation fields (e.g. `account`, `stage`, `owner`), and applies `qs = qs.select_related(*fk_fields)`. This eliminates 10 template-time database queries on cold dashboard visits.

### 4. Active Form, Modal & Rich-Text Safety (`navigation_history.js`)
Implemented `isFormOrModalActiveOrDirty()`:
- Checks if `document.activeElement` is in an input, textarea, select, or contentEditable.
- Checks if any modal or dialog (`#modalBox:not(:empty)`, Flowbite dialogs) is open.
- Checks if form fields have unsaved modifications (`value !== defaultValue`, `checked !== defaultChecked`, or files selected).
- Checks if rich-text editors (`.note-editor`) are active.
If any edit session is active, background SWR updates are deferred into `pendingFreshUpdates` and safely held until the edit session completes or the form is reset, preventing any loss of unsaved typing.

---

## 4. Before & After Comparison Table (Phase 3.8)

| Metric | Before (Baseline) | After (Optimized) | Improvement |
| :--- | :---: | :---: | :---: |
| **First-load HTML/HTMX Requests** | 3 sequential hops | **1 single request** | **-66.7% network round trips** |
| **Opportunities Kanban Initial Load** | 2,480.1 ms | **1,399.1 ms** | **1,081.0 ms faster (-43.6%)** |
| **Opportunities Kanban SQL Queries** | 35 queries | **23 queries** | **-12 queries eliminated** |
| **Accounts Chart Initial Load** | 1,258.3 ms | **815.8 ms** | **442.5 ms faster (-35.2%)** |
| **Accounts Chart SQL Queries** | 21 queries | **13 queries** | **-8 queries eliminated** |
| **Leads Chart Initial Load** | 1,561.3 ms | **1,121.8 ms** | **439.5 ms faster (-28.1%)** |
| **Leads Chart SQL Queries** | 22 queries | **14 queries** | **-8 queries eliminated** |
| **Activities Initial Load** | 951.3 ms | **553.9 ms** | **397.4 ms faster (-41.8%)** |
| **Activities SQL Queries** | 16 queries | **8 queries** | **-8 queries eliminated** |
| **Dashboard First Paint (Chrome CDP)** | 3,556.5 ms | **1,364.0 ms** | **2,192.5 ms faster (-61.6%)** |
| **Dashboard Cold SQL Queries** | 45 queries (2,718 ms) | **35 queries (2,112 ms)** | **-10 N+1 queries (-606 ms SQL)** |
| **Repeat Cached Navigation** | 2.5–13.8 ms | **6.7 ms** | Instant restoration retained |
| **Browser Console Errors** | 0 | **0** | Clean execution verified |

---

## 5. Security & Multi-User RBAC Audit (Phase 3.6)

A dedicated security verification script (`scratch/test_phase3_security_rbac.py`) executed across sales roles:
- **Superadmin** (ID 3): Accessible lead count: **105**. Response size: **444,999 Bytes**.
- **Restricted User** (ID 2): Accessible lead count: **0**. Response size: **44,595 Bytes**.
- **Cross-User Data Leakage Check:** Exactly **0** unauthorized or superadmin-only lead IDs appeared in the restricted user's consolidated response.
- **Unauthenticated Access:** Requests without a valid session cookie were blocked with `302 Found` redirecting to `/login/`.
- **Kanban Permission Scope:** The consolidated Kanban layout enforces `self.get_queryset()`, ensuring role hierarchies are strictly applied before batching.

---

## 6. Files Changed

| File Path | Nature of Change |
| :--- | :--- |
| [`finlo/contrib/generics/views/core.py`](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/core.py) | Added `_render_subview` and inlined navbar & layout rendering in `FinloView.get_context_data`. |
| [`finlo/contrib/generics/templates/base.html`](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/templates/base.html) | Inlined `rendered_navbar` and `rendered_main_session` without `hx-trigger="load"` when pre-rendered. |
| [`finlo/contrib/generics/views/kanban.py`](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/generics/views/kanban.py) | Batched item retrieval across active Kanban columns into 1 query when on page 1. |
| [`finlo/contrib/dashboard/utils.py`](file:///c:/Users/izhar/Desktop/crm-v2/finlo/contrib/dashboard/utils.py) | Upfront `table_fields` resolution and auto `select_related(*fk_fields)` in `build_table_context`. |
| [`static/assets/js/navigation_history.js`](file:///c:/Users/izhar/Desktop/crm-v2/static/assets/js/navigation_history.js) | Implemented `isFormOrModalActiveOrDirty()` to protect dirty forms, open modals, and rich text editors during SWR. |

---

## 7. Remaining Bottlenecks & Future Recommendations

1. **Supabase Geographic Latency:** The PostgreSQL database is located in Supabase Mumbai (`ap-south-1`). Each SQL query takes ~45–65 ms of network round-trip time from the local machine. In production hosting closer to Mumbai (or AWS ap-south-1), initial page rendering will naturally drop by another 400–600 ms.
2. **Local Redis Daemon:** Daphne is currently falling back to `LocMemCache` because Redis port 6379 is not running locally. Starting the local Redis service will allow multi-worker cache sharing for Celery and ASGI Channels.
3. **HTTP/2 or HTTP/3 on Reverse Proxy:** In production with Nginx or Caddy, static assets and async requests will benefit from HTTP/2 multiplexing, further reducing initial handshake overhead.

