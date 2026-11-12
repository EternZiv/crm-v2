"""Build an evidence-only audit summary from bounded diagnostic output."""
import json
from pathlib import Path

rows = json.loads(Path('FINLO_READONLY_PAGE_RESULTS.json').read_text())
lines = ['# FINLO page, settings, dashboard and navigation audit', '',
    'Date: 2026-11-12. Audit only; no application repair or deployment in this pass.', '',
    '## Coverage and limits', '',
    f'- {len(rows)} distinct registered menu/core destinations sampled. See the complete matrix below.',
    '- 2,279 URL patterns inventoried, including API/action/detail endpoints. These were NOT all executed.',
    '- 418 enabled application HTML templates parsed successfully.',
    '- 131 inline JavaScript blocks passed syntax screening after neutralizing Django tags; this is not runtime proof.',
    '- Top-level static/assets/js files passed Node syntax checks.',
    '- Browser: existing ASM session retained. Dashboard, Leads, Opportunities, Accounts, Contacts, Reports, Dashboard list, Calendar, My Review Jobs, My Settings, Password Management and Google Calendar settings rendered.',
    '- Sales, People, Analytics, Schedule and My Jobs submenus rendered. Sales/People stayed open during tested navigation. Calendar Week/Month switching retained primary/sub-navigation.',
    '- NOT TESTED: every record/detail URL, form submission, CRUD, email delivery/sync, automation execution, external calendar/meeting/call connectivity, mobile viewport, and all role combinations.',
    '- Admin settings browser acceptance is BLOCKED by the existing ASM role. Backend samples used an existing authorized test identity with isolated signed sessions; no account changes.', '',
    '## Measurement method', '',
    'Each route ran in its own bounded child process, normally with one cold and one warm Django Client GET. Cold includes first-request URL resolver/template initialization. Warm reuses process-local caches. These are synchronous backend diagnostic timings, NOT production ASGI, browser TTFB or click-to-usable benchmarks. Profiling and SQL fingerprinting add overhead; no percentile claims are made.', '',
    'The initial subset used an unsafe session-level read-only guard. It was stopped and replaced by a transaction-local guard. Later samples include two extra safety SET statements and transaction overhead in SQL counts/timings. Earlier and later samples therefore have slightly different overhead. Authentication/bootstrap outside the timed request, persistent session writes and shared Redis caches are excluded. Do not interpret results as exact live-server latency.', '',
    'Cursor execute timings include driver/network/pooler/database waiting; they do not isolate PostgreSQL server execution or prove lock contention. Query parameters and result records are never logged.', '',
    '## Confirmed findings and priorities', '',
    '1. **Export Data eagerly loads metadata for many modules.** /export-view/: 9.004s cold / 3.239s warm, 55 / 30 instrumented queries. custom_fields/utils.py:127 performed 20 definition lookups (2.310s cold / 1.029s warm); :117 performed 20 cold ContentType lookups (1.024s). These represent distinct model lookups, not proven identical-parameter duplicates. ExportView.get_available_models in finlo/contrib/core/views/export_data.py builds module/field metadata before a module is selected. Next repair: batch request-scoped metadata or defer fields until an authorized module is selected. Preserve field permissions and scopes.',
    '2. **Dashboard still generates below-fold data on the server.** finlo/contrib/dashboard/views/home.py:147 calls generate_table_data on cache miss. Measured baseline: 5.769s cold / 1.363s warm, 38 / 10 queries, 2.570s / 0.663s cursor time; about 0.279s / 0.301s exclusive template time. Campaign table loading remains present (utils.py:758). Browser viewport-lazy chart initialization does not defer these backend queries. Next repair: scoped, demand-loaded widget endpoints, with export forcing needed widgets to finish.',
    '3. **Cold URL resolver initialization is material.** A sampled cold Inbox request spent 0.987s exclusively in django.utils.regex_helper.normalize, plus 0.302s flatten_result, 0.270s next_char and related iteration. Warm samples do not show that overhead. This is worker-cold work across the large route set, not a query executed on every page. Evaluate worker startup warming of URL reversing without crawling business views.',
    '4. **The welcome overlay deliberately blocks interaction for five seconds.** static/assets/js/page_motion.js:22 removes a full-screen overlay after 5000ms; page_motion.css gives it the highest overlay z-index. It does not prefetch all page data. This was previously requested behavior, not a new defect. It makes an under-one-second first-visit usable-page target impossible while enabled.',
    '5. **Settings search can trigger a full settings crawl.** finlo/contrib/core/views/core.py:492 starts a daemon thread; :628 recursively renders menu destinations and nested hx-get targets (depth 2). Triggered on search cache miss, not every page load. This is a code-confirmed extra workload, but its wall time was NOT measured: it was not invoked against live settings because GET handlers may initialize preferences. The index key includes user/language but omits company/policy revision; company-switch/revocation behavior needs isolated testing. The crawl has no explicit connection-cleanup finally. Do not remove security checks to optimize it.',
    '6. **Duplicate message container IDs reproduced.** Contacts DOM had two messages-container IDs, but one header and one primary sidebar. templates/index.html includes messages.html globally and finlo/contrib/generics/templates/chart_view.html:27 includes it again. global.js:1167 uses an ID-based toast selector. Duplicate IDs are confirmed; missed/duplicate toast behavior is a risk not yet reproduced through a write workflow. Settings accordion template also repeats id="base-content" per group; its current handler uses nextElementSibling, so broken accordion behavior is not established.',
    '7. **Shared frontend payload remains on all pages.** index.html loads HTMX, jQuery, Hyperscript, Flowbite, SweetAlert2 and Select2 globally, plus global.js. Those seven scripts total approximately 701KB uncompressed. Parser-blocking dependencies precede deferred UI libraries. This is a payload/parse candidate, not a measured main-thread bottleneck. Move libraries only after checking their consumers. PNG/PDF and Sortable on-demand work is preserved.',
    '8. **Full-document notification context materializes all unread rows.** finlo/context_processors.py:145-149 evaluates an unbounded unread queryset; repeated context evaluation is request-cached and HTMX skips it. Cost scales with unread volume; current browser account had zero unread messages. Do not claim this caused current multi-second latency.',
    '9. **Permission batching remains present.** sales_authorization.py:153 caches grant/deny sets on the request user. Sampled grant/deny SQL fingerprints generally occurred once each, not once per menu item. A grant-query outlier of 1.189s occurred on warm Export Data; one outlier does not establish an RBAC architecture defect. Retain authorization and request-scoped batching.', '',
    '## Browser observations', '',
    'Automation click-to-visible-heading samples (include automation overhead and do NOT establish complete chart usability): Dashboard 3.787s; Leads 2.481s; Opportunities 2.612s; Accounts 3.470s; Contacts 3.458s; Reports 2.920s. These are single samples, not cold/warm medians. No under-one-second acceptance claim.', '',
    '- A Contacts chart HTMX request returned 400 once. Later navigation rendered its chart successfully. Root cause is UNCONFIRMED; it occurred during the early audit period and cannot yet be separated from audit interference/aborted navigation.',
    '- Dashboard list returned 500 during audit contamination, then rendered successfully after cleanup. This is NOT counted as a confirmed product defect.',
    '- No Method Not Allowed/raw chart JavaScript was seen in tested core-page DOM. Browser console retained the two earlier request-error entries; later Contacts rendered with a canvas.', '',
    '## Audit incident and database safety', '',
    'The first harness incorrectly used SET default_transaction_read_only and SET statement_timeout at session scope behind the transaction pooler. The settings leaked to pooled backend sessions and affected a legitimate dashboard GET initializer. Only the audit parent/child processes were stopped. Audit-introduced overrides were reset to PostgreSQL reset values; subsequent paired checks repeatedly showed read-only off and the original 120000ms timeout on both sampled backends. Dashboard list recovered in the browser. The harness now uses SET TRANSACTION READ ONLY and SET LOCAL statement_timeout inside a bounded transaction, plus SQL write guards and isolated local caches/signed sessions.', '',
    'No migrations, schema changes, explicit business-record writes, account resets, role changes, commits or deployments were performed. No live CRUD/rollback tests were attempted. Existing CRM GET handlers may initialize user preferences during ordinary browser navigation; no Save/Submit action was used. The incident is retained here rather than being presented as an application bug.', '',
    '## Per-page matrix', '',
    'PASS below means the sampled GET rendered HTTP 200 without an observed exception; it does not mean complete functional acceptance. A 302-only route is BLOCKED pending its intended fragment/redirect flow. Guard-blocked writes are BLOCKED, not confirmed product failures.', '',
    '| Route | Result | Cold seconds | Warm/fragment seconds | SQL count cold / second | SQL seconds cold / second |',
    '|---|---|---:|---:|---:|---:|']
for row in rows:
    samples = row.get('results', [])
    first = samples[0] if samples else {}
    second = samples[1] if len(samples)>1 else {}
    status = 'BLOCKED'
    if any(s.get('error') == 'ReadOnlyGuardBlockedWrite' for s in samples): status = 'BLOCKED: GET attempted write'
    elif any(s.get('error') for s in samples): status = 'FAIL/INVESTIGATE: ' + ','.join(s['error'] for s in samples if s.get('error'))
    elif any(s.get('status') == 200 and not s.get('body_flags') for s in samples): status = 'PASS (GET only)'
    def val(sample, key):
        value = sample.get(key)
        return f'{value:.3f}' if isinstance(value,float) else str(value) if value is not None else '—'
    lines.append(f"| {row['route']} | {status} | {val(first,'total_seconds')} | {val(second,'total_seconds')} | {val(first,'sql_count')} / {val(second,'sql_count')} | {val(first,'sql_seconds')} / {val(second,'sql_seconds')} |")
lines += ['', '## Next work and readiness', '',
    'Repair sequence: export metadata batching/lazy selection; true server-side widget deferral; toast container deduplication; bounded settings-search indexing with cleanup; then targeted browser/ASGI timing and isolated mutation tests. Decide whether to retain the requested welcome delay before setting a first-visit usability target.', '',
    'Production/performance sign-off: NO-GO. Browser TTFB, complete cold/warm click-to-usable, load/concurrency, external integrations, role-specific admin browser flows and staging CRUD remain unverified. Psycopg3 adoption remains NO-GO; active database/dependency configuration is unchanged.', '',
    'Artifacts added: page_readonly_audit.py, page_template_script_audit.py, build_page_audit_report.py and FINLO_* audit JSON/Markdown outputs. Runtime product files were not changed in this audit pass. Rollback: remove only these audit artifacts if no longer wanted; preserve all pre-existing dirty work. Do not rerun older profiling scripts with session-level SET commands behind the transaction pooler.']
Path('FINLO_PAGE_AUDIT_REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print('Report updated for',len(rows),'routes')
