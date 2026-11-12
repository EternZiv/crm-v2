# FINLO page, settings, dashboard and navigation audit

Date: 2026-11-12. Audit only; no application repair or deployment in this pass.

## Coverage and limits

- 65 distinct registered menu/core destinations sampled. See the complete matrix below.
- 2,279 URL patterns inventoried, including API/action/detail endpoints. These were NOT all executed.
- 418 enabled application HTML templates parsed successfully.
- 131 inline JavaScript blocks passed syntax screening after neutralizing Django tags; this is not runtime proof.
- Top-level static/assets/js files passed Node syntax checks.
- Browser: existing ASM session retained. Dashboard, Leads, Opportunities, Accounts, Contacts, Reports, Dashboard list, Calendar, My Review Jobs, My Settings, Password Management and Google Calendar settings rendered.
- Sales, People, Analytics, Schedule and My Jobs submenus rendered. Sales/People stayed open during tested navigation. Calendar Week/Month switching retained primary/sub-navigation.
- NOT TESTED: every record/detail URL, form submission, CRUD, email delivery/sync, automation execution, external calendar/meeting/call connectivity, mobile viewport, and all role combinations.
- Admin settings browser acceptance is BLOCKED by the existing ASM role. Backend samples used an existing authorized test identity with isolated signed sessions; no account changes.

## Measurement method

Each route ran in its own bounded child process, normally with one cold and one warm Django Client GET. Cold includes first-request URL resolver/template initialization. Warm reuses process-local caches. These are synchronous backend diagnostic timings, NOT production ASGI, browser TTFB or click-to-usable benchmarks. Profiling and SQL fingerprinting add overhead; no percentile claims are made.

The initial subset used an unsafe session-level read-only guard. It was stopped and replaced by a transaction-local guard. Later samples include two extra safety SET statements and transaction overhead in SQL counts/timings. Earlier and later samples therefore have slightly different overhead. Authentication/bootstrap outside the timed request, persistent session writes and shared Redis caches are excluded. Do not interpret results as exact live-server latency.

Cursor execute timings include driver/network/pooler/database waiting; they do not isolate PostgreSQL server execution or prove lock contention. Query parameters and result records are never logged.

## Confirmed findings and priorities

1. **Export Data eagerly loads metadata for many modules.** /export-view/: 9.004s cold / 3.239s warm, 55 / 30 instrumented queries. custom_fields/utils.py:127 performed 20 definition lookups (2.310s cold / 1.029s warm); :117 performed 20 cold ContentType lookups (1.024s). These represent distinct model lookups, not proven identical-parameter duplicates. ExportView.get_available_models in finlo/contrib/core/views/export_data.py builds module/field metadata before a module is selected. Next repair: batch request-scoped metadata or defer fields until an authorized module is selected. Preserve field permissions and scopes.
2. **Dashboard still generates below-fold data on the server.** finlo/contrib/dashboard/views/home.py:147 calls generate_table_data on cache miss. Measured baseline: 5.769s cold / 1.363s warm, 38 / 10 queries, 2.570s / 0.663s cursor time; about 0.279s / 0.301s exclusive template time. Campaign table loading remains present (utils.py:758). Browser viewport-lazy chart initialization does not defer these backend queries. Next repair: scoped, demand-loaded widget endpoints, with export forcing needed widgets to finish.
3. **Cold URL resolver initialization is material.** A sampled cold Inbox request spent 0.987s exclusively in django.utils.regex_helper.normalize, plus 0.302s flatten_result, 0.270s next_char and related iteration. Warm samples do not show that overhead. This is worker-cold work across the large route set, not a query executed on every page. Evaluate worker startup warming of URL reversing without crawling business views.
4. **The welcome overlay deliberately blocks interaction for five seconds.** static/assets/js/page_motion.js:22 removes a full-screen overlay after 5000ms; page_motion.css gives it the highest overlay z-index. It does not prefetch all page data. This was previously requested behavior, not a new defect. It makes an under-one-second first-visit usable-page target impossible while enabled.
5. **Settings search can trigger a full settings crawl.** finlo/contrib/core/views/core.py:492 starts a daemon thread; :628 recursively renders menu destinations and nested hx-get targets (depth 2). Triggered on search cache miss, not every page load. This is a code-confirmed extra workload, but its wall time was NOT measured: it was not invoked against live settings because GET handlers may initialize preferences. The index key includes user/language but omits company/policy revision; company-switch/revocation behavior needs isolated testing. The crawl has no explicit connection-cleanup finally. Do not remove security checks to optimize it.
6. **Duplicate message container IDs reproduced.** Contacts DOM had two messages-container IDs, but one header and one primary sidebar. templates/index.html includes messages.html globally and finlo/contrib/generics/templates/chart_view.html:27 includes it again. global.js:1167 uses an ID-based toast selector. Duplicate IDs are confirmed; missed/duplicate toast behavior is a risk not yet reproduced through a write workflow. Settings accordion template also repeats id="base-content" per group; its current handler uses nextElementSibling, so broken accordion behavior is not established.
7. **Shared frontend payload remains on all pages.** index.html loads HTMX, jQuery, Hyperscript, Flowbite, SweetAlert2 and Select2 globally, plus global.js. Those seven scripts total approximately 701KB uncompressed. Parser-blocking dependencies precede deferred UI libraries. This is a payload/parse candidate, not a measured main-thread bottleneck. Move libraries only after checking their consumers. PNG/PDF and Sortable on-demand work is preserved.
8. **Full-document notification context materializes all unread rows.** finlo/context_processors.py:145-149 evaluates an unbounded unread queryset; repeated context evaluation is request-cached and HTMX skips it. Cost scales with unread volume; current browser account had zero unread messages. Do not claim this caused current multi-second latency.
9. **Permission batching remains present.** sales_authorization.py:153 caches grant/deny sets on the request user. Sampled grant/deny SQL fingerprints generally occurred once each, not once per menu item. A grant-query outlier of 1.189s occurred on warm Export Data; one outlier does not establish an RBAC architecture defect. Retain authorization and request-scoped batching.

## Browser observations

Automation click-to-visible-heading samples (include automation overhead and do NOT establish complete chart usability): Dashboard 3.787s; Leads 2.481s; Opportunities 2.612s; Accounts 3.470s; Contacts 3.458s; Reports 2.920s. These are single samples, not cold/warm medians. No under-one-second acceptance claim.

- A Contacts chart HTMX request returned 400 once. Later navigation rendered its chart successfully. Root cause is UNCONFIRMED; it occurred during the early audit period and cannot yet be separated from audit interference/aborted navigation.
- Dashboard list returned 500 during audit contamination, then rendered successfully after cleanup. This is NOT counted as a confirmed product defect.
- No Method Not Allowed/raw chart JavaScript was seen in tested core-page DOM. Browser console retained the two earlier request-error entries; later Contacts rendered with a canvas.

## Audit incident and database safety

The first harness incorrectly used SET default_transaction_read_only and SET statement_timeout at session scope behind the transaction pooler. The settings leaked to pooled backend sessions and affected a legitimate dashboard GET initializer. Only the audit parent/child processes were stopped. Audit-introduced overrides were reset to PostgreSQL reset values; subsequent paired checks repeatedly showed read-only off and the original 120000ms timeout on both sampled backends. Dashboard list recovered in the browser. The harness now uses SET TRANSACTION READ ONLY and SET LOCAL statement_timeout inside a bounded transaction, plus SQL write guards and isolated local caches/signed sessions.

No migrations, schema changes, explicit business-record writes, account resets, role changes, commits or deployments were performed. No live CRUD/rollback tests were attempted. Existing CRM GET handlers may initialize user preferences during ordinary browser navigation; no Save/Submit action was used. The incident is retained here rather than being presented as an application bug.

## Per-page matrix

PASS below means the sampled GET rendered HTTP 200 without an observed exception; it does not mean complete functional acceptance. A 302-only route is BLOCKED pending its intended fragment/redirect flow. Guard-blocked writes are BLOCKED, not confirmed product failures.

| Route | Result | Cold seconds | Warm/fragment seconds | SQL count cold / second | SQL seconds cold / second |
|---|---|---:|---:|---:|---:|
| /dashboard/?section=home | PASS (GET only) | 5.769 | 1.363 | 38 / 10 | 2.570 / 0.663 |
| /settings-view/ | PASS (GET only) | 5.230 | 1.026 | 12 / 7 | 1.042 / 0.747 |
| /my-settings-view/ | PASS (GET only) | 4.761 | 0.665 | 15 / 7 | 1.416 / 0.492 |
| /approvals/approval-process-view/ | BLOCKED | 2.223 | 0.115 | 4 / 2 | 0.196 / 0.098 |
| /review-process/review-processes/ | BLOCKED | 2.517 | 0.396 | 4 / 2 | 0.212 / 0.379 |
| /company-information/ | PASS (GET only) | 5.408 | 1.257 | 12 / 7 | 1.369 / 0.963 |
| /user-view/ | PASS (GET only) | 6.764 | 1.984 | 23 / 16 | 2.192 / 1.307 |
| /role-permission-view/ | PASS (GET only) | 5.178 | 0.919 | 12 / 7 | 0.926 / 0.620 |
| /booking/booking-settings/ | BLOCKED | 2.431 | 0.124 | 4 / 2 | 0.192 / 0.102 |
| /department-view/ | PASS (GET only) | 5.088 | 1.466 | 22 / 15 | 1.289 / 0.960 |
| /branches-view/ | PASS (GET only) | 6.300 | 1.661 | 23 / 16 | 1.759 / 1.038 |
| /sales-regions/ | PASS (GET only) | 5.827 | 1.365 | 23 / 16 | 1.555 / 0.980 |
| /sales-teams/ | PASS (GET only) | 6.690 | 1.637 | 23 / 16 | 1.811 / 1.132 |
| /dashboard/dashboard-list-view/?section=analytics | PASS (GET only) | 4.617 | 1.494 | 23 / 17 | 1.418 / 1.025 |
| /crm/contacts/contacts-view/?section=people | PASS (GET only) | 4.576 | 1.678 | 26 / 21 | 1.668 / 1.150 |
| /sales-assignments/ | PASS (GET only) | 6.092 | 1.929 | 25 / 18 | 1.808 / 1.318 |
| /roles-view/ | PASS (GET only) | 6.093 | 1.594 | 17 / 12 | 1.782 / 1.154 |
| /team-role-view/ | PASS (GET only) | 5.383 | 1.475 | 24 / 17 | 1.521 / 0.996 |
| /customer-role-view/ | PASS (GET only) | 5.500 | 1.680 | 24 / 17 | 1.531 / 1.179 |
| /partner-role-view/ | PASS (GET only) | 6.238 | 1.547 | 24 / 17 | 1.413 / 1.043 |
| /crm/scoring/scoring-rule-view/ | PASS (GET only) | 5.900 | 2.615 | 23 / 17 | 1.655 / 2.077 |
| /import-view/ | PASS (GET only) | 5.341 | 1.470 | 14 / 9 | 1.329 / 1.082 |
| /export-view/ | PASS (GET only) | 9.004 | 3.239 | 55 / 30 | 4.940 / 2.762 |
| /recycle-bin-view/ | PASS (GET only) | 5.991 | 1.667 | 23 / 17 | 1.500 / 1.178 |
| /version-info-view/ | PASS (GET only) | 5.753 | 1.186 | 14 / 9 | 0.886 / 0.780 |
| /calendar/google-integration/settings/ | PASS (GET only) | 2.693 | 3.240 | 6 / 11 | 0.360 / 1.027 |
| /meeting/integration/settings/ | PASS (GET only) | 6.157 | 2.266 | 21 / 16 | 2.119 / 1.930 |
| /calls/settings/ | PASS (GET only) | 5.813 | 1.992 | 21 / 16 | 1.547 / 1.606 |
| /notifications/notification-template-view/ | PASS (GET only) | 6.215 | 2.324 | 24 / 17 | 2.525 / 1.927 |
| /mail/mail-server/ | PASS (GET only) | 5.063 | 1.709 | 24 / 18 | 1.678 / 1.281 |
| /mail/incoming-mail-server/ | PASS (GET only) | 6.525 | 1.880 | 24 / 18 | 2.394 / 1.466 |
| /mail/mail-template-view/ | PASS (GET only) | 5.185 | 1.682 | 23 / 17 | 1.418 / 1.228 |
| /mail/mail-history/ | PASS (GET only) | 6.745 | 2.357 | 23 / 17 | 1.921 / 1.647 |
| /mail/inbox-view/ | PASS (GET only) | 6.313 | 1.606 | 23 / 17 | 1.452 / 1.106 |
| /automations/automation-view/ | PASS (GET only) | 5.938 | 1.623 | 23 / 17 | 1.526 / 1.154 |
| /cadences/cadence-view/ | PASS (GET only) | 4.877 | 1.616 | 23 / 17 | 1.392 / 1.130 |
| /workflow/workflow-rule-view/ | PASS (GET only) | 5.871 | 1.843 | 23 / 17 | 1.660 / 1.286 |
| /theme/color-theme-view/ | PASS (GET only) | 5.064 | 1.178 | 17 / 12 | 1.641 / 0.873 |
| /duplicates/matching-rules/ | PASS (GET only) | 4.708 | 1.503 | 17 / 12 | 1.124 / 1.076 |
| /duplicates/duplicate-rules/ | PASS (GET only) | 6.775 | 1.746 | 24 / 18 | 2.024 / 1.166 |
| /field-requirements/ | PASS (GET only) | 6.199 | 2.487 | 23 / 17 | 1.634 / 1.992 |
| /form-layouts/ | PASS (GET only) | 4.951 | 1.407 | 21 / 14 | 1.425 / 1.044 |
| /crm/leads/lead-stage-view/ | PASS (GET only) | 2.759 | 4.195 | 6 / 21 | 0.619 / 1.534 |
| /crm/leads/leads-assignment-view/ | PASS (GET only) | 2.770 | 3.761 | 6 / 20 | 0.570 / 1.249 |
| /crm/leads/mail-to-lead-view/ | PASS (GET only) | 2.932 | 3.925 | 6 / 19 | 0.372 / 1.509 |
| /crm/leads/form-builder/ | PASS (GET only) | 2.018 | 2.524 | 6 / 12 | 0.358 / 0.864 |
| /crm/opportunities/opportunity-stage-view/ | PASS (GET only) | 2.007 | 3.893 | 6 / 21 | 0.362 / 1.852 |
| /crm/opportunities/team-selling/ | PASS (GET only) | 1.906 | 2.734 | 6 / 11 | 0.364 / 1.041 |
| /crm/opportunities/opportunity-split-view/ | BLOCKED | 2.687 | 1.346 | 6 / 5 | 0.635 / 0.310 |
| /crm/opportunities/big-deal-alert-view/ | PASS (GET only) | 1.943 | 2.641 | 6 / 13 | 0.361 / 0.994 |
| /crm/forecast/forecast-type-view/ | PASS (GET only) | 2.796 | 3.548 | 6 / 21 | 0.363 / 1.525 |
| /crm/forecast/forecast-target-view/ | PASS (GET only) | 2.391 | 3.852 | 6 / 24 | 0.349 / 1.433 |
| /custom-fields/ | PASS (GET only) | 5.529 | 1.793 | 23 / 17 | 1.814 / 1.371 |
| /my-profile-view/ | PASS (GET only) | 4.852 | 1.072 | 17 / 9 | 1.731 / 0.788 |
| /regional-formating-view/ | PASS (GET only) | 5.244 | 1.489 | 18 / 10 | 1.927 / 0.988 |
| /change-password-view/ | PASS (GET only) | 5.172 | 1.043 | 18 / 10 | 1.241 / 0.781 |
| /user-login-history-view/ | FAIL/INVESTIGATE: TransactionManagementError | 5.511 | — | 25 / — | 1.192 / — |
| /user-holiday-view/ | FAIL/INVESTIGATE: TransactionManagementError | 4.666 | — | 25 / — | 1.352 / — |
| /calendar/google-calendar/settings/ | PASS (GET only) | 2.000 | 2.633 | 6 / 15 | 0.359 / 1.001 |
| /shortkeys/short-key-view/ | PASS (GET only) | 6.657 | 2.601 | 27 / 18 | 1.922 / 1.203 |
| /meeting/user/settings/ | PASS (GET only) | 6.129 | 1.104 | 17 / 9 | 1.539 / 0.819 |
| /crm/opportunities/opportunity-team-view/ | BLOCKED | 2.170 | 1.383 | 6 / 5 | 0.373 / 0.305 |
| /calls/user-settings/ | PASS (GET only) | 4.851 | 0.852 | 17 / 9 | 1.337 / 0.624 |
| /crm/leads/leads-view/?section=sales | PASS (GET only) | 6.510 | 2.377 | 27 / 22 | 2.426 / 1.574 |
| /crm/accounts/accounts-view/?section=people | PASS (GET only) | 9.030 | 2.731 | 26 / 21 | 2.970 / 2.070 |

## Next work and readiness

Repair sequence: export metadata batching/lazy selection; true server-side widget deferral; toast container deduplication; bounded settings-search indexing with cleanup; then targeted browser/ASGI timing and isolated mutation tests. Decide whether to retain the requested welcome delay before setting a first-visit usability target.

Production/performance sign-off: NO-GO. Browser TTFB, complete cold/warm click-to-usable, load/concurrency, external integrations, role-specific admin browser flows and staging CRUD remain unverified. Psycopg3 adoption remains NO-GO; active database/dependency configuration is unchanged.

Artifacts added: page_readonly_audit.py, page_template_script_audit.py, build_page_audit_report.py and FINLO_* audit JSON/Markdown outputs. Runtime product files were not changed in this audit pass. Rollback: remove only these audit artifacts if no longer wanted; preserve all pre-existing dirty work. Do not rerun older profiling scripts with session-level SET commands behind the transaction pooler.
