# FINLONEXA CRM v2 — Performance & Stability Results

Date: 2026-11-14

## Outcome

**Partial PASS for previously implemented query reductions; current acceptance is BLOCKED/FAIL.** The worktree already contains Dashboard/Leads performance changes and a measurement report. I did not edit those active, uncommitted files. A focused regression run completed 45 tests with **44 passing and one error**. The failing test cannot exercise its permission-revocation assertion because it patches a missing method. Local runtime and isolated browser measurements were unavailable, so current performance and browser stability were not remeasured.

## Baseline and prior measurements

The requested current baseline was Dashboard cold/warm **3,201/1,008 ms** and Leads cold/warm **2,214/604 ms**. These match the “after” measurements in the existing November 14 latency report. They are historical; they were not remeasured in this run.

| Route | Prior report: before change | Prior report: after change | User-supplied current baseline | Current run |
|---|---|---|---|---|
| Leads list fragment | 18 queries; SQL 1,296 ms; server 2,540 ms | 14 queries; SQL 891 ms; server 2,214 ms; payload 341,373 bytes | Cold 2,214 ms; warm 604 ms | **BLOCKED**; server socket access denied in sandbox |
| Default Dashboard | 40 queries; SQL 2,253 ms; view 2,978 ms; template 1,046 ms; total 4,024 ms | 30 queries; SQL 1,797 ms; view 2,434 ms; template 766 ms; total 3,201 ms; payload 302,579 bytes | Cold 3,201 ms; warm 1,008 ms | **BLOCKED**; server socket access denied in sandbox |

The existing latency report also records warm Leads at 3 queries / 265 ms SQL / 604 ms server, and warm Dashboard at 9 queries / 498 ms SQL / 1,008 ms server. These values are reported as prior measurements, not newly verified results. No new performance gain is claimed.

## Highest-impact bottlenecks and current status

The following three bottlenecks were measured in the existing latency report and their changes are already present in the dirty worktree:

1. **Repeated field-permission lookups:** six field-level permission queries were replaced with a model-level batch lookup and per-user-instance/request reuse. The helper still resolves through the existing field permission function; no security rules were intentionally changed.
2. **Repeated sales-scope queries:** repeated `SalesAssignment` scope resolution was reduced using request and user-instance reuse. The current cache key includes user, company, and role.
3. **Dashboard count/table duplication:** Lead KPI counts are passed into the dashboard table count cache, and zero-count tables avoid an empty page-row query. This preserves data retrieval for non-empty tables.

The prior report attributes measured reductions to these changes: Leads cold query count 18→14 and SQL time 1,296→891 ms; Dashboard cold query count 40→30 and SQL time 2,253→1,797 ms. Current code-level changes were inspected but not edited in this task because the relevant files are already modified and may be actively owned by Antigravity.

## Current regression result and security acceptance

Ran the focused command once:

```text
.venv\Scripts\python.exe manage.py test finlo_crm.leads.tests.test_analytics_service finlo.contrib.dashboard.test_request_reuse finlo.contrib.core.test_auth_hardening --settings=finlo.settings.security_test
```

Result: **45 tests; 1 error; 44 completed without failure.** Django system checks passed. The error is:

```text
AttributeError: LeadDataService does not have the attribute '_can_read_leads'
```

`test_permission_revocation_prevents_returning_cached_kpi` patches that missing method, so the test errors before exercising the expected revoked-permission behavior. In the current service path, the authorized queryset builder is invoked on a cache miss; a cache hit returns the result before that queryset is built. Permission-change signals are intended to bump authorization revisions, but this run cannot establish an immediate current-permission check on cache hits. **Treat cache-hit permission revocation as FAIL/UNVERIFIED until the active owner restores or corrects this guard and the test asserts the behavior.** I did not alter `services.py` or the test file because both are already uncommitted/possibly active. This is a correctness gate; performance acceptance must not override it.

## Runtime and frontend status

- A bounded anonymous `/health/` request to `127.0.0.1:8000` was denied by the sandbox socket policy. This is **BLOCKED**, not proof that the server is down.
- No authenticated request timing, SQL count, SQL duration, response bytes, or view/template timings were collected in this run.
- No existing browser session was navigated or modified. No isolated authenticated browser was available.
- Dashboard → Leads / Accounts navigation, Back/Forward, skeleton completion, chart initialization/disposal, duplicate requests/listeners, overlays, dropdowns, and modal behavior are **BLOCKED** for browser acceptance.
- WebSocket or other infrastructure behavior was not investigated because it is outside this focused performance acceptance and no browser runtime was used.

## Files changed in this task

- Added `FINLO_PERFORMANCE_STABILITY_RESULTS.md` only.
- No application code, settings, tests, database, Redis, browser session, or server process was changed by this task.
- The following already-modified performance files were reviewed but left untouched: `finlo/contrib/core/utils.py`, `finlo/contrib/core/sales_authorization.py`, `finlo/contrib/dashboard/utils.py`, `finlo_crm/leads/dashboard.py`, `finlo_crm/leads/services.py`, and `finlo_crm/leads/views/core.py`.

## Remaining issues and next optimization

1. Resolve the Lead cache-hit permission guard/test mismatch in the active owner’s worktree; confirm permission revocation before serving cached aggregates, while retaining company/row scope and avoiding redundant expensive queries.
2. Re-run the same 45 focused tests after that correction; do not accept the current error as a passing security test.
3. With an approved authenticated runtime, capture cold and warm Leads/Dashboard requests using identical identity, filters, cache state, and instrumentation. Report SQL, view, template, payload, and browser click-to-usable values separately.
4. Only after those gates, investigate any remaining repeated query fingerprints. Do not add shared caching, alter the five-minute Lead TTL, or rewrite navigation as part of this task.

## Rollback

There is no application-code rollback for this task. The new report can be removed independently if desired. Do not revert the existing uncommitted performance changes as a group; they predate this task and may include active work. If rollback is later approved, revert only the specific optimization hunks after confirming ownership and rerunning the focused suite.

## Acceptance summary

| Area | Status |
|---|---|
| Previously measured backend query reductions | **PASS as historical report evidence; not remeasured** |
| Current focused regression suite | **FAIL** — one permission-revocation test errors before assertion |
| Current local server measurement | **BLOCKED** — sandbox denied socket access |
| Browser navigation/skeleton/chart acceptance | **BLOCKED** — no isolated authenticated browser |
| Application changes in this task | **NONE** — relevant files already modified |
| Overall production readiness | **NO-GO** |
