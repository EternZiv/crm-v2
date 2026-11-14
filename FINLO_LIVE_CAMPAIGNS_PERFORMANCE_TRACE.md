# FINLONEXA CRM v2 — Live Campaigns Performance Trace

**Date:** 2026-11-15
**Target:** `/crm/campaigns/campaign-view/?section=sales&layout=chart&chart_group_by=status&chart_type=column`
**Result:** BLOCKED before browser navigation; no live timings were collected.

## Runtime access

| Check | Result |
|---|---|
| Port 8000 listener | None found. |
| Read-only `/health/` probe | Not sent because no listener was present. |
| Known project-root logs (`runserver.log`, `daphne.log`, `logs/runserver.log`, `logs/daphne.log`, `task-7297.log`) | None found. |
| Existing browser session | Left untouched; application was not reachable, so no navigation was attempted. |
| Startup blocker | Exact process failure is unknown: no active server process/listener and no startup log were available to inspect. |

This establishes only that the local app was unavailable from this execution environment at the time checked. It does not establish a Django, Supabase, DNS, or application-code failure. No known blocked DNS/socket operation was retried.

## Requested measurements

| Measurement | Status | Evidence |
|---|---|---|
| Click timestamp / click-to-usable | BLOCKED | No page navigation was performed. |
| Soft-navigation LCP and its interaction attribution | BLOCKED | No Performance trace was available. |
| Shell, navbar, chart request timing/status/TTFB/transfer | BLOCKED | No requests were made. |
| Duplicate, retried, aborted requests | BLOCKED | No network trace. |
| Main-thread tasks and JavaScript timing | BLOCKED | No Performance trace. |
| Django/ASGI total and stage durations | BLOCKED | No request reached Django. |
| DB connect, SQL count/time | BLOCKED | No request/DB profiling was performed. |
| Primary bottleneck classification | BLOCKED | No live timing evidence; no cause is asserted. |

The user-reported 164.73-second soft-navigation LCP is not independently reproduced by this run and is not treated as click-to-usable timing.

## Shortest safe next step

Have the operator start the single intended local development server using the already-approved development command/configuration, without launching a second instance. Confirm that `http://127.0.0.1:8000/health/` returns HTTP 200 and that the startup output remains available. Once ready, the existing authorized Superadmin browser session can be used for three bounded Dashboard → Campaigns chart repetitions and one Chrome Performance trace. If startup fails, provide the final startup error/log excerpt with secrets redacted. No credentials or session values are needed in the report.

## Changes and safety

- No application or settings files changed.
- No server was started, restarted, or terminated.
- No database request or write, migration, or production load test was performed.
- No MCP files or processes were accessed.
- No optimization is recommended until the timing trace identifies the dominant stage.

## Live follow-up — 2026-11-15

### Execution-environment reachability

One bounded GET to 127.0.0.1:8000/health/ failed before reaching the application. Windows returned a socket permission error: “An attempt was made to access a socket in a way forbidden by its access permissions” for 127.0.0.1:8000. This confirms that the Codex execution environment is not permitted to access the local loopback socket. It does not establish that the server started manually in the operator's PowerShell is down.

No repeated connection attempt was made. No Chrome navigation or trace was captured. No timing values below are available for this run.

### Current measured-evidence table

| Measurement | Result |
|---|---|
| Codex-to-localhost health request | Blocked before HTTP; socket permission denied |
| Server HTTP status/TTFB | Not measured |
| Dashboard → Campaigns click-to-usable | Not measured |
| Shell/nav/chart request waterfall | Not measured |
| Main-thread JavaScript/long tasks | Not measured |
| Soft-navigation LCP attribution | Not measured |
| Database connection/SQL/view/template stages | Not measured |
| Confirmed live bottleneck | None; BLOCKED |

The prior user-reported 164.73-second soft-navigation LCP remains unverified in this run.

### Browser-only capture procedure for the operator

Use the already-open Chrome tab that is authenticated as the authorized Superadmin. Do not sign out, change credentials, or submit CRM forms.

1. Open DevTools with F12. In Network, enable Preserve log. Leave Disable cache off for the first warm-navigation sample; capture cold-cache behavior separately only if desired.
2. Open Performance, enable screenshots, start recording, click Dashboard, then click Sales → Campaigns. Stop recording after the Campaign chart is visibly usable.
3. Repeat the same click path twice more in separate recordings. Keep account, filters, viewport, and cache state consistent; note whether each run is cold or warm.
4. In Network, record each request's URL path, status, total duration, TTFB (Timing → Waiting/TTFB), and transfer size. Include the outer campaign-view request and the campaign-nav-view and campaign-chart-view fragments. Note canceled/failed/duplicate requests.
5. In the Performance trace, locate the click event, HTMX request/response intervals, DOM swaps, paints, and Main-thread tasks. Measure click-to-usable as click timestamp to the point where the chart/empty state and controls are usable. Do not substitute soft-nav LCP for this interaction duration.
6. For the SOFT NAV metric, record the soft-navigation marker/start and the LCP candidate tied to that interaction. Report LCP relative to that soft-nav start and include its element. If the trace does not show a matching soft-navigation entry/interaction, label that metric unavailable.
7. Copy or export only the timing summary and request paths. Redact cookies, authorization headers, usernames, CRM values, query parameters that contain sensitive data, and any session identifiers. Do not share a raw HAR unless it has been sanitized.

### Prioritized minimal correction plan (conditional on that trace)

1. **Do not change anything until one of the following patterns is measured.** The current failure is access isolation, not evidence about the CRM's cause.
2. If the outer shell has high TTFB, instrument that one request server-side in a non-persistent diagnostic run, splitting middleware/auth/company/permission work, connection creation, SQL, view, and template time. Do not change CONN_MAX_AGE or database settings based on the current blocked run.
3. If the shell is fast but navbar/chart fragments dominate, optimize only the slow fragment. The current template starts the two subview requests after shell insertion; confirm whether their timings overlap before considering composition changes.
4. If request/TTFB is fast but the Main thread has long tasks, inspect the exact task stack. The empty Campaign chart template skips ECharts initialization when it has no chart labels, so do not assume ECharts is the cause.
5. If click-to-usable is reasonable but the soft-nav LCP looks extreme, correct the metric attribution/reporting interpretation rather than changing application behavior.
6. Treat the CSP eval warning as a separate issue unless the trace links the violation to a failed critical handler or measurable long task. Do not weaken CSP.

### Final status

- Runtime/browser reproduction: BLOCKED by Codex loopback socket permission.
- Confirmed primary performance cause: NOT ESTABLISHED.
- Source/config/database changes: NONE.
- Next dependency: operator-run Chrome trace using the procedure above, or an approved browser environment with access to the manually started server.
