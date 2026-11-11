# FINLO RBAC Test Runner Recovery

## Root cause

The isolated settings loaded the production `INSTALLED_APPS` list, including `daphne`. On Windows, importing Daphne during Django app population created an asyncio self-pipe and blocked in `socket.accept()` before tests could be discovered. A bounded `faulthandler` capture showed the stack in `daphne.server -> asyncio.new_event_loop -> socket._fallback_socketpair`.

## Minimal fix

`finlo/settings/security_test.py` now removes only `daphne` from the isolated test app list. Production settings are unchanged. Daphne is a server integration and is not required for model, authorization, or request tests.

## Result

Command:

```text
.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization finlo.contrib.core.test_rbac_repair --settings=finlo.settings.security_test --verbosity=1 --noinput
```

Result: **33 tests passed**, 0 failures, 0 errors, in **174.648 seconds**. The test database was an in-memory SQLite database and was destroyed at the end. `manage.py check --settings=finlo.settings.security_test` reported no issues.

## Isolation

No live Supabase connection was used by this test run. No migrations, account changes, or production data mutations were performed.
