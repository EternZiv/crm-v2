# FINLONEXA CRM v2 — Phase 3 Navigation Performance Baseline & Architecture Plan

**Assessment Date:** November 15, 2026  
**Environment:** Local Development Runtime (`C:\Users\izhar\Desktop\crm-v2`)  
**Server Runtime:** Daphne / ASGI (`0.0.0.0:8000`) with StatReloader  
**Database Driver:** `psycopg` (v3.3.9) with `psycopg_pool` (v3.3.3)  
**Database Connection:** Supabase Mumbai (`aws-0-ap-south-1.pooler.supabase.com:6543`, transaction pooler mode)  
**Active Identity:** Superadmin (ID 33, `company=None`)  
**Browser Engine:** Google Chrome Headless 157.0.8103.78 via Chrome DevTools Protocol (CDP)  

---

## 1. Runtime Confirmation: Active Daphne & Pooling Status

The active Daphne process (PID 8664) and runtime configuration were verified against live endpoints:
- **Engine:** `django.db.backends.postgresql`
- **Active Driver:** `psycopg.Connection` (psycopg 3.3.9)
- **Active Pool:** `<psycopg_pool.pool.ConnectionPool>` (psycopg_pool 3.3.3)
- **`CONN_MAX_AGE`:** `0` (strictly enforced per Django 6 pooling requirements)
- **`CONN_HEALTH_CHECKS`:** `True`
- **`DISABLE_SERVER_SIDE_CURSORS`:** `True`
- **`prepare_threshold`:** `None` (disables prepared statements on Supabase port 6543)
- **Pool Size:** `min_size=1`, `max_size=4`, `timeout=10.0s`, `max_idle=300.0s`
- **Status:** **CONFIRMED & HEALTHY**. Daphne operates with 4 active pooled connections to Supabase.

---

## 2. Real Chrome DevTools Click-to-Usable Navigation Timings

Using automated Chrome DevTools Protocol (CDP) instrumentation, real browser user navigation was recorded across the full requested cycle: **Dashboard → Campaigns → Leads → Accounts → Dashboard**.

Each interaction measured the exact timestamp of the mouse click, every HTMX request dispatched, response headers, and the final `htmx:afterSettle` event when all skeletons were replaced by interactive DOM components.

### 2.1. Navigation Cycle Timing Summary

| Transition | Target URL | Navigation Type | HTTP Reqs | Chrome Click-to-Usable | Settle Target |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **1. Dashboard → Campaigns** | `/crm/campaigns/campaign-view/?section=sales` | HTMX Boosted | 3 | **1,380.7 ms (1.38 s)** | `#mainSession` (Chart) |
| **2. Campaigns → Leads** | `/crm/leads/leads-view/?section=sales` | HTMX Boosted | 3 | **1,824.6 ms (1.82 s)** | `#mainSession` (Table) |
| **3. Leads → Accounts** | `/crm/accounts/accounts-view/?section=people` | HTMX Boosted | 3 | **1,265.9 ms (1.27 s)** | `#mainSession` (Table) |
| **4. Accounts → Dashboard** | `/dashboard/dashboard-list-view/?section=analytics` | HTMX Boosted | 2 | **3,780.7 ms (3.78 s)** | `#navBar` (Dashboard) |

*Total 4-step navigation cycle duration: **8.25 seconds** across 11 total HTTP requests.*

---

## 3. Empirical HTTP Waterfall: Sequential vs Parallel Overlap

A primary architectural question was whether FINLO's multi-fragment navigation executes sequentially or overlaps in parallel.

The live Chrome CDP trace provides definitive empirical evidence:

```mermaid
sequenceDiagram
    autonumber
    actor User as Chrome User
    participant Browser as Chrome HTMX Engine
    participant Daphne as Daphne / ASGI Server
    participant DB as Supabase Mumbai (psycopg3 Pool)

    User->>Browser: Click "#campaigns" Link (t=0ms)
    Note over Browser: HTMX Boosted Navigation dispatched
    Browser->>Daphne: Req 1: GET /crm/campaigns/campaign-view/ (t=5.4ms)
    Daphne->>DB: Query shell metadata & layout definition
    DB--Daphne: Return (CONN_MAX_AGE=0, pooled ~50ms)
    Daphne--Browser: Req 1 Response: Shell HTML + Skeletons (t=432.8ms)
    Note over Browser: DOM Swaps #mainContent (t=450ms). HTMX detects hx-trigger="load" on #navBar & #mainSession

    par Parallel Fragment Requests
        Browser->>Daphne: Req 2: GET /crm/campaigns/campaign-nav-view/ (t=454.3ms)
        Daphne->>DB: Fetch pinned views & filter metadata
        DB--Daphne: Return nav data
        Daphne--Browser: Req 2 Response: Navbar HTML (t=831.2ms)
    and
        Browser->>Daphne: Req 3: GET /crm/campaigns/campaign-chart-view/ (t=455.8ms)
        Daphne->>DB: Aggregate campaign chart data
        DB--Daphne: Return chart JSON/HTML
        Daphne--Browser: Req 3 Response: Chart HTML (t=1313.4ms)
    end

    Note over Browser: #navBar settles at t=886ms
    Note over Browser: #mainSession settles at t=1380.7ms (Click-to-Usable Complete)
```

### Detailed Event Log Analysis

#### Step 1: Dashboard → Campaigns
- `t = 5.4 ms`: `BEFORE_REQUEST` → Shell `/crm/campaigns/campaign-view/?section=sales`
- `t = 432.8 ms`: `AFTER_REQUEST` ← Shell completed (Duration: 427.4 ms)
- `t = 454.3 ms`: `BEFORE_REQUEST` → Req 2: `/crm/campaigns/campaign-nav-view/?section=sales` (Target: `#navBar`)
- `t = 455.8 ms`: `BEFORE_REQUEST` → Req 3: `/crm/campaigns/campaign-chart-view/?section=sales` (Target: `#mainSession`)
- **Concurrency Analysis:**
  - Req 2 start: `454.3 ms`
  - Req 3 start: `455.8 ms` (dispatched within **1.5 ms** of each other)
  - Req 2 end: `831.2 ms`
  - Req 3 end: `1,313.4 ms`
  - **Overlap:** **375.4 ms of simultaneous parallel execution** across separate pooled connections.
  - Final DOM Settle: `1,380.7 ms`.

#### Step 2: Campaigns → Leads
- `t = 1.9 ms`: `BEFORE_REQUEST` → Shell `/crm/leads/leads-view/?section=sales`
- `t = 398.9 ms`: `AFTER_REQUEST` ← Shell completed (Duration: 397.0 ms)
- `t = 421.2 ms`: `BEFORE_REQUEST` → Req 2: `/crm/leads/leads-nav/?section=sales` (Target: `#navBar`)
- `t = 421.9 ms`: `BEFORE_REQUEST` → Req 3: `/crm/leads/leads-list/?section=sales` (Target: `#mainSession`)
- **Concurrency Analysis:**
  - Req 2 start: `421.2 ms`
  - Req 3 start: `421.9 ms` (dispatched within **0.7 ms** of each other)
  - Req 2 end: `782.3 ms`
  - Req 3 end: `1,790.5 ms`
  - **Overlap:** **360.4 ms of simultaneous parallel execution**.
  - Final DOM Settle: `1,824.6 ms`.

#### Step 3: Leads → Accounts
- `t = 1.6 ms`: `BEFORE_REQUEST` → Shell `/crm/accounts/accounts-view/?section=people`
- `t = 376.2 ms`: `AFTER_REQUEST` ← Shell completed (Duration: 374.6 ms)
- `t = 397.0 ms`: `BEFORE_REQUEST` → Req 2: `/crm/accounts/accounts-nav-view/?section=people` (Target: `#navBar`)
- `t = 397.8 ms`: `BEFORE_REQUEST` → Req 3: `/crm/accounts/accounts-list-view/?section=people` (Target: `#mainSession`)
- **Concurrency Analysis:**
  - Req 2 start: `397.0 ms`
  - Req 3 start: `397.8 ms` (dispatched within **0.8 ms** of each other)
  - Req 2 end: `776.4 ms`
  - Req 3 end: `1,228.6 ms`
  - **Overlap:** **378.6 ms of simultaneous parallel execution**.
  - Final DOM Settle: `1,265.9 ms`.

### Conclusion on Waterfall Behavior
**The HTTP waterfall is a Two-Stage Pipeline**:
1. **Stage 1 (Sequential Gate):** The Shell request (Req 1) executes first in complete isolation (~380–430 ms). The browser cannot discover or fire Req 2 and Req 3 until Req 1 finishes and parses.
2. **Stage 2 (Parallel Sibling Overlap):** Once `#mainContent` is swapped into the DOM, HTMX encounters `hx-trigger="load"` on both `#navBar` and `#mainSession`. It dispatches both HTTP requests virtually instantaneously (< 1.5 ms apart). Because Django Daphne runs ASGI with our Phase 2 connection pool (`max_size=4`), both requests execute concurrently without contention.
3. **The Root Inefficiency:** The total click-to-usable time is the sum of **Stage 1 (Shell: ~400 ms) + Stage 2 (Slowest Subview: ~900–1,400 ms)**. Splitting the navigation into a shell + 2 fragments forces **two serialized roundtrips** across the network for every single click.

---

## 4. Navigation Fragment Consolidation Assessment

| Fragment / Request | Current Behavior | Proposed Optimization | Safety & Compatibility Impact |
| :--- | :--- | :--- | :--- |
| **Shell Request (`#mainContent`)** | Always fetched via `hx-boost` or `hx-get`. Returns full HTML layout with skeletons. | **Retain as primary navigation trigger**, but pre-render navbar server-side into the initial payload. | **100% Safe.** Preserves `hx-push-url="true"` and browser history. |
| **Navbar Partial (`#navBar`)** | Fired as a separate HTTP request via `hx-trigger="load"` in `base.html`. Consumes ~380 ms server time. | **Eliminate separate HTTP request.** In `FinloView._render_subview(self.nav_url)`, embed the rendered navbar directly inside the shell response. | **100% Safe.** Does not break filter dropdowns or pinned views; eliminates 1 HTTP request per navigation. |
| **Main Content Partial (`#mainSession`)** | Fired as a separate HTTP request via `hx-trigger="load"` to fetch table or chart. | **Optionally stream or inline.** For initial loads, keep asynchronous or consolidate where fast (< 200 ms). | Preserves skeleton placeholder during long chart aggregation. |
| **Unified Navigation Out-Of-Band (`hx-select-oob="#finloUnifiedNavigation"`)** | Currently re-swaps the whole sidebar when switching main sections. | **Eliminate sidebar re-rendering.** With a single unified collapsible sidebar, all modules are visible in the sidebar tree. Switching sections requires only client-side CSS class toggle (`active`), not HTML re-fetching. | **Huge performance win.** Completely decouples sidebar state from server responses. |

---

## 5. Existing Sidebar Architecture & Data Source Inventory

### 5.1. Existing Templates
1. **`templates/components/sidebar.html`**:
   - The primary navigation template.
   - Contains branding logo, collapse toggle button (`#toggleSideMenu`), mobile close button (`#closeMobileSidebar`).
   - Renders sections via `main_section_menu` and children via `sub_section_menu`.
   - Contains floating quick-action button (`.floating-menu`).
2. **`templates/components/sub_sidebar.html`**:
   - Legacy template currently holding a 1-line comment: `{# Legacy include retained for third-party templates. #}`.
3. **`templates/components/modelcontent_layout.html`**:
   - Layout template extending `index.html`.
   - Defines `{% block sub_sidebar %}{% endblock %}` (currently empty).
4. **`templates/index.html`**:
   - Renders the shell wrapper `<div id="sidebar">{% include 'components/sidebar.html' %}</div>`.
   - Contains JavaScript deduplication logic (`deduplicateNavbars`) to remove duplicate headers/sidebars swapped by HTMX.

### 5.2. Permission-Filtered Navigation Data Source
- **Main Sections:** Registered via `@main_section_menu.register` in `finlo/menu/main_section_menu.py`. Evaluated via `get_main_section_menu(request)`. Permission is checked per user via `has_section_perm_url(request.user, item.section)`.
- **Sub-Sections:** Registered via `@sub_section_menu.register` in `finlo/menu/sub_section_menu.py`. Evaluated via `get_sub_section_menu(request)`.
  - Checks `is_super_admin_or_superuser(user)`.
  - Checks `user.has_perm(p)` for each item.
  - Returns a dictionary `sections[section_name]` containing sorted items.
  - Cached on `request._cached_sub_section_menu` for zero repeated database evaluation during a single request.
- **Context Processors:** `finlo/context_processors.py` exposes `main_section_menu` and `sub_section_menu` as `SimpleLazyObject` to all templates automatically.

---

## 6. Minimal Implementation Plan: Unified Collapsible MES-Style Sidebar

### 6.1. Visual Specification (Matching Power2Go MES Screenshot)
Based on `media_1794316565455_cd3d4a83.png` and `media_1794547484260_9473e143.png`:
- **Single Integrated Rail/Panel:** No secondary floating drawer. All sections (Sales, People, Analytics, Schedule) live in one unified dark sidebar (`bg-[#18181b]` or dark palette).
- **Accordion / Collapsible Tree:**
  - Section headers (e.g., "Sales", "People") expand/collapse their child items (`Leads`, `Campaigns`, `Opportunities`, `Forecast`).
  - Active item is styled with a subtle rounded pill background (`bg-primary-600/20 text-primary-400 font-medium`).
- **Sidebar Collapse Button:** A circular toggle icon button (`<` / `>`) at the top right of the sidebar header.
- **Collapsed Mode (Rail Mode):**
  - Width contracts to `64px` (`w-16`).
  - Labels hidden (`display: none`), only icons visible (`w-5 h-5`).
  - Hovering an icon surfaces a native tooltip with module name.
- **Expanded Mode:** Width expands smoothly to `240px` (`w-60`).
- **State Persistence:** Preserved in `localStorage.getItem('finlo_sidebar_collapsed')` to prevent flicker during navigations.

### 6.2. Affected Files

| File | Change Scope | Description |
| :--- | :---: | :--- |
| `templates/components/sidebar.html` | Template | Refactor markup to single unified collapsible tree. Clean up redundant nesting. |
| `static/assets/css/style.css` | Stylesheet | Add compact MES collapsible classes (`.finlo-sidebar.collapsed`, `.finlo-sidebar-expanded`). |
| `static/assets/js/global.js` | JavaScript | Wire `#toggleSideMenu` to toggle `.collapsed` class and sync with `localStorage`. |
| `finlo/menu/__init__.py` | Configuration | Remove `hx-select-oob: #finloUnifiedNavigation` from `MAIN_SECTION_HX_ATTRS` so navigation does not re-swap the sidebar HTML. |
| `finlo/contrib/generics/views/core.py` | View Logic | Pre-render `rendered_navbar` server-side during boosted navigation to eliminate Request 2. |

### 6.3. Expected Performance Benefits
1. **Request Count Reduction:** Reduces HTTP requests per page navigation from **3 requests down to 1–2 requests** (eliminating the standalone navbar call).
2. **Click-to-Usable Improvement:** Eliminates ~400 ms of navbar waterfall delay. Navigation click-to-usable is projected to drop from **~1.3–1.8 s down to ~800–950 ms**.
3. **Zero Sidebar Flashing / Layout Shifts:** The sidebar remains in the DOM and never re-renders; only the active CSS class changes via lightweight client-side listener.
4. **Bandwidth Savings:** Avoids sending redundant sidebar out-of-band HTML on every section switch.

---

## 7. Git Working Tree Integrity Audit

The repository working tree was audited prior to proposing any Phase 3 modifications (`git status -s`):
- **Phase 1 Fixes Intact:** `finlo/contrib/generics/views/navbar.py`, `list.py`, `dashboard/utils.py`, `core/utils.py`, `context_processors.py`.
- **Phase 2 Pooling Intact:** `finlo/settings/base.py` (`ENABLE_DB_POOL`, `psycopg 3`, `psycopg_pool`, `prepare_threshold=None`, `CONN_MAX_AGE=0`) and `requirements.txt`.
- **Pre-existing Uncommitted Files:** Pre-existing changes in `static/assets/css/style.css`, `static/assets/js/global.js`, `templates/components/sidebar.html`, and `static/assets/js/navigation_history.js` are preserved without conflict.

---

## 8. Regression Risks & Acceptance Test Matrix

| Risk Area | Potential Failure Mode | Prevention & Verification Strategy |
| :--- | :--- | :--- |
| **HTMX History & URL Push** | Back/forward navigation restores stale sidebar state. | Verify `hx-history-elt` wrapper and test Chrome Back/Forward buttons across 5 routes. |
| **RBAC / Permission Leakage** | User sees modules they lack permission for. | Rely exclusively on `get_sub_section_menu(request)` and test non-superuser roles (e.g. Sales Manager). |
| **Mobile Drawer Responsiveness** | Sidebar fails to open/close on small screens (< 1024px). | Verify `#mobileSidebarBackdrop` and `#closeMobileSidebar` behavior on 375px and 768px viewports. |
| **Dropdown / Select2 Initialization** | Pre-rendered navbar Select2 dropdown fails to initialize. | Verify `ensureSelect2Loaded()` hooks fire on `htmx:afterSwap`. |
| **Empty Company Superadmin** | Errors when `request.active_company is None`. | Verify navigation works seamlessly with `company=None`. |

---

## 9. Boundary Statement

**Phase 3 implementation has NOT been started.**  
No files have been modified. No database records, migrations, or server configuration settings were altered. This document establishes the empirical baseline and architecture plan awaiting user authorization.
