# FINLO focused repair results

Date: 2026-11-12

This pass resumed the existing audit. It did not rerun the broad audit, alter live records, apply migrations, change production settings, or rerun the RBAC suite.

## Export Data

Status: **IMPLEMENTED, FOCUSED TEST GATE PASS; BROWSER RUNTIME BLOCKED**

Before the change, `ExportView.get_available_models()` called `get_export_queryset()` for each authorized registered model and built every model's field list before the user selected a module. The audit baseline was 9.004 seconds cold, 3.239 seconds warm, with 55 and 30 instrumented SQL calls. Twenty custom-field definition lookups accounted for 2.310 seconds cold and 1.029 seconds warm; twenty cold ContentType lookups accounted for 1.024 seconds.

Changed files:

- `finlo/contrib/core/views/export_data.py`: available modules now return labels and empty field arrays. A `fields=1` GET loads fields only for explicitly requested modules. Authorization is checked again for each requested module; unauthorized modules return no fields. The existing POST export path remains responsible for final permission and selected-field validation.
- `finlo/contrib/core/templates/export/export_view.html`: the column dialog requests field metadata after module selection and before opening. The existing checkbox names and POST form contract are preserved.
- `finlo/contrib/core/test_export_optimization.py`: focused tests cover empty initial field metadata, authorized metadata, unauthorized module filtering, and POST validation.

The standard Django DiscoverRunner was the startup blocker: `django.setup()` and test import/discovery completed, but `setup_databases()` spent more than 180 seconds applying the full migration graph to the isolated test database. This was a test-environment setup bottleneck, not an Export Data import or execution failure. A single bounded subprocess using `security_test` settings and `unittest` (the tests are `SimpleTestCase` and require no database) bypassed database creation safely. Result: **4/4 PASS in 0.030s**. No production settings were changed and no active server was restarted.

No valid after SQL/timing sample was collected because the active server status remains inconclusive and the isolated database-backed runner is still too slow for this focused gate. The 9.004/3.239-second figures remain before-only baselines; exact SQL/timing comparability is unavailable. The authorized and unauthorized metadata paths were verified with isolated request objects and mocked identities, not live records. Browser export-field loading is **BLOCKED**.

## Dashboard

Status: **BLOCKED / NO CHANGE**

The audit confirmed that `finlo/contrib/dashboard/views/home.py` calls `generate_chart_data()` and `generate_table_data()` together on a cache miss. The dashboard template and edit/export paths expect the combined block order and complete data context. A safe server-side deferral requires a dedicated authorized widget endpoint and cache/invalidation rules; no Dashboard change was made in this pass.

The prior diagnostic baseline remains 5.769 seconds cold and 1.363 seconds warm, with 38 and 10 instrumented SQL calls. No after measurement exists.

Charts, filters, drag-and-drop, edit mode and PDF export were preserved.

## Duplicate toast container

Status: **IMPLEMENTED, STATIC VERIFICATION PASSED**

Removed the second `messages.html` include from `finlo/contrib/generics/templates/chart_view.html`. The global messages container in `templates/index.html` remains, so notification rendering is retained while duplicate `messages-container` IDs are removed from chart pages.

## Settings search

Status: **NOT CHANGED**

The existing background indexer remains bounded to depth two and permission-filtered, but company/policy cache-key behavior and cleanup were not changed because the Export Data runtime gate was blocked. No settings-search optimization is claimed.

## Database safety

No session-level PostgreSQL `SET` commands were used in this repair pass. The old diagnostic harness is not reused. No database records, roles, permissions, migrations, accounts or production settings were modified.

## Verification summary

- Python compilation: PASS for modified Export Data view and focused test module.
- JavaScript syntax: PASS for the existing global script.
- Diff whitespace check: PASS.
- Focused Export Data tests: PASS (4/4, no database setup required).
- Standard Django database setup: BLOCKED/UNUSUALLY SLOW (>180s applying migrations); no production change made.
- Export before/after timing: BLOCKED; before-only baseline retained.
- Dashboard before/after timing: BLOCKED; no Dashboard code changed.
- Browser verification: BLOCKED.
- RBAC regression suite: NOT RERUN; authorization internals were not changed.

The next safe step is a bounded browser or live read-only request against a confirmed running server to measure the new `fields=1` endpoint. Dashboard refactoring remains intentionally out of scope until that runtime acceptance gate is satisfied.
