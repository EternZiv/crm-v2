# FINLONEXA CRM v2 — Browser Navigation Fix Results

Date: 2026-11-14

## Scope and outcome

The HTMX history restoration path now validates restored content, requests the current same-origin route once when a cached snapshot is incomplete, reports a recoverable retry state if recovery fails, and reinitializes the existing role-configured Dashboard charts after restoration. The full runtime acceptance gate is **BLOCKED** because authenticated browser verification was unavailable. No Leads or Accounts waterfall changes were made.

## Confirmed findings

- The prior runtime report observed Back restoring a blank/stuck skeleton and Forward restoring Dashboard markup without chart instances. Those historical browser observations were not reproduced in this turn.
- The prior report attributed missing fallback to `htmx.config.refreshOnHistoryMiss = false`. Inspection of the bundled HTMX implementation disproves that explanation: with this setting false, HTMX performs an AJAX history-miss request; setting it true causes a full document reload. The existing false setting is retained.
- The application history handler previously cleared the busy state and re-executed scripts but did not validate restored content. It also used a full document reload for a restored destination-shell snapshot. This left malformed/incomplete history content without a targeted recovery path.
- Dashboard template code already exposes an idempotent `window.initFinloDefaultHomeDashboard()` initializer, including role-provided chart configuration and hidden-container handling. Restoration now invokes it explicitly; no chart count is hardcoded.
- Snapshot readiness rejects actual skeletons and unfinished lazy fragments based on DOM state/size, not row count. An empty but fully rendered table remains eligible.

## Changes

- `static/assets/js/navigation_history.js`
  - Added deferred history-content validation after HTMX restore and nested settle.
  - Invalid cached snapshots receive one same-origin HTMX-style fetch; overlapping fallback fetches for the same URL are suppressed.
  - Failed fallback displays a retryable error rather than an endless skeleton or automatic reload.
  - 401/login redirects clear protected FinloViewCache and HTMX history storage; 403 responses clear protected caches and show an authorization message.
  - Dashboard chart initialization is invoked after both HTMX history restoration and FinloViewCache restoration.
  - `refreshOnHistoryMiss` remains false to retain HTMX's AJAX fallback behavior.
- `finlo/contrib/generics/test_navigation_shell.py`
  - Updated the shell-history regression expectation and added focused checks for bounded fallback, chart initialization, and cache cleanup on 401/403.

The navigation script had pre-existing uncommitted cache/revalidation work in the working tree. This report describes only the history/chart changes in this task; unrelated work was preserved.

## Verification

- Focused Django tests: `finlo.contrib.generics.test_navigation_shell` — **9 passed**.
- JavaScript syntax: `node --check static/assets/js/navigation_history.js` — **PASS**.
- Whitespace validation: `git diff --check` on the two changed code/test files — **PASS**.
- Browser Back/Forward, Dashboard → Leads → Dashboard, Dashboard → Accounts → Dashboard, chart count/rendering, filters/modals, duplicate requests, and click timing — **BLOCKED**; no isolated authenticated browser context was used.
- Database, permissions, roles, migrations, and server processes — untouched.

## Performance and acceptance matrix

Historical figures below are from the supplied runtime audit and are not re-measured or directly comparable to this code-only verification.

| Flow | Historical usable time | Historical requests | Current after-measurement |
|---|---:|---:|---|
| Dashboard cold load | 5,508 ms | 0 HTMX (document load) | BLOCKED |
| Dashboard → Leads | 3,064 ms | 3 | BLOCKED |
| Dashboard → Accounts | 2,875 ms | 3 | BLOCKED |
| Leads → Dashboard | 1,494 ms | 1 | BLOCKED |
| Cached Accounts → Dashboard | <200 ms usable | 0 immediate; 2,072 ms revalidation reported | BLOCKED |
| Back | Blank/stuck skeleton observed | 0 | BLOCKED |
| Forward | Dashboard DOM without charts observed | 0 | BLOCKED |

| Gate | Status |
|---|---|
| History restore validation and bounded fallback (code + focused tests) | PASS |
| Chart reinitialization hook (code + focused tests) | PASS |
| Browser history and chart runtime behavior | BLOCKED |
| P1 Leads/Accounts waterfall optimization | NOT ATTEMPTED pending P0 browser acceptance |
| Production readiness | NOT ESTABLISHED |

## Rollback

Revert only the history-recovery and chart-initialization hunks in `static/assets/js/navigation_history.js`, and restore the prior expectation in `finlo/contrib/generics/test_navigation_shell.py`. Preserve unrelated pre-existing changes in those files. No database or deployment rollback is applicable.

## Remaining acceptance work

Run an isolated authenticated browser pass for Back/Forward, dashboard chart restoration, Leads/Accounts navigation, and controls. Confirm no stale protected content is visible after a server-confirmed 401/403. The browser test must measure click-to-shell, click-to-usable, requests, and errors before any P1 waterfall optimization is considered.
