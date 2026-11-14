# FINLONEXA CRM v2 — Django Startup Diagnostics

Date: 2026-11-14

## Summary

**Confirmed blocker in the Codex execution environment:** Daphne's import-time asyncio event-loop construction blocks because this Python build has no native `_socket.socketpair`, and Python's TCP-based fallback cannot connect to loopback. A bounded local socket probe returned Winsock error `10013` (`WSAEACCES`); the fallback then waited in `accept()`. This reproduces the startup stall before Django reaches server binding.

This establishes the cause of the failed launch attempts in this execution environment. It does **not** establish that the same loopback restriction exists in the user's ordinary Windows terminal. No app source correction is justified until that environment is checked.

## Environment and process preflight

| Check | Result |
|---|---|
| Port 8000 | **PASS — free** before and after diagnostics. |
| Existing Python/Daphne server processes | **PASS — none found** by `Get-Process` name check. |
| Venv interpreter | **PASS —** `.venv\Scripts\python.exe` exists. |
| Python | **PASS —** 3.12.10. |
| Django | **PASS —** 6.0.4 imports. |
| Daphne | **PASS —** 4.2.1 installed. |
| Git status | **PASS — recorded without modification.** There are pre-existing uncommitted CRM changes, including `finlo/mcp_server.py` and MCP reports. These were not opened or edited. Their presence is consistent with ongoing MCP work, but does not prove process ownership. No Python/Daphne server process was found; other MCP processes were not inspected. `Get-CimInstance Win32_Process` was denied, so parent PID/command-line inspection was unavailable. |
| Settings import | **PASS —** `finlo.settings` imports without connecting to the database. No credentials were printed. |

## Stage isolation

| Startup stage | Result | Evidence |
|---|---|---|
| Python interpreter initialization | PASS | Version and interpreter checkpoint printed. |
| Django import | PASS | Django 6.0.4 imported. |
| Settings import | PASS | `finlo.settings` imported. |
| `manage.py` startup helper import | PASS | Progress/banner helpers imported. |
| Runserver banner setup | **FAIL / stall reproduced** | `install_progress()` returned; `install_banner()` did not return. It imports Daphne's runserver command. |
| Django app registry / `django.setup()` | **FAIL / stall reproduced** | In a separate probe that bypassed banner setup, `django.setup()` stalled while populating the `daphne` app, before registry readiness. |
| Django system checks | BLOCKED | Not reached because app population blocks. |
| URL configuration import | BLOCKED | Not reached after the app registry stall. |
| ASGI application import | BLOCKED | Not reached after the app registry stall. |
| Database connection initialization | NOT REACHED | Settings import completed; the app registry stalled at Daphne before Django could reach request handling. No database connection was opened by these probes. |
| APScheduler initialization | NOT REACHED | Core `AppConfig.ready()` is after successful app population; the stall occurs earlier. |
| Development server bind | FAIL | Port 8000 remained free; no server PID remains. |

## Captured stack evidence

The bounded `faulthandler` trace during `install_banner()` was:

```text
socket.py:295 in accept
socket.py:627 in _fallback_socketpair
asyncio/selector_events.py:120 in _make_self_pipe
asyncio/selector_events.py:66 in __init__
asyncio/events.py:720 in new_event_loop
asyncio/events.py:823 in new_event_loop
.venv/Lib/site-packages/daphne/server.py:10 in <module>
.venv/Lib/site-packages/daphne/management/commands/runserver.py:15 in <module>
finlo/utils/startup/banner.py:29 in install
```

The second independent trace had the same socket/asyncio/Daphne frames, reached through:

```text
daphne/apps.py:6 importing daphne.server
... django/apps/config.py:create
... django/apps/registry.py:populate
... django/__init__.py:setup
```

A standalone bounded socket probe confirmed:

```text
NATIVE_SOCKETPAIR_AVAILABLE False
LOOPBACK_CONNECT_EX 10013
TimeoutError at listener.accept()
```

Thus the `accept()` wait is not evidence of a database or APScheduler wait. In this runtime, the Python fallback attempts a local TCP connection that the environment denies.

The initial full server attempt printed only the project startup banner. A repeated direct probe captured the stack above. Diagnostic children had self-imposed deadlines and exited; no pre-existing process was terminated. The runserver process itself was not launched during this read-only diagnosis.

## APScheduler review

Static inspection only:

- `CoreConfig.ready()` starts the scheduler only for a server process and only when `RUN_MAIN == "true"` (runserver autoreloader child) or the executable is Daphne.
- The normal runserver parent does not meet that guard, avoiding parent/child duplicate startup.
- `start_scheduler()` registers jobs at 12-hour, 4-hour and 1-hour intervals, then calls `scheduler.start()`; it does not synchronously execute those maintenance jobs at startup.
- The previously reported `RuntimeError: cannot schedule new futures after interpreter shutdown` is consistent with a separate scheduler shutdown/lifecycle issue. It was not reproduced here and cannot explain this stall because startup never reaches `CoreConfig.ready()`.

No scheduler behavior was changed or dynamically exercised.

## Root cause and uncertainty

**Confirmed for this diagnostic environment:** low-level loopback TCP is denied, and Daphne import invokes asyncio's selector event loop, which requests `socket.socketpair()`. Because native socketpair is unavailable, the Python fallback waits for the denied loopback connection. This accounts for the previous banner-only startup and absence of a port-8000 listener in this environment.

**Not established:** whether the user's normal Windows Python process also lacks native socketpair or is blocked by Windows Firewall/security policy. The Windows runtime used here reports `WSAEACCES`, but sandbox restrictions can produce that result. Do not attribute it to CRM source code or change firewall/security settings based on this evidence alone.

## Minimal remediation plan

No source changes are recommended from this run. The smallest next verification is in the user's ordinary, non-sandboxed PowerShell session:

1. Run a short Python probe that checks `_socket.socketpair` availability and constructs/closes `socket.socketpair()` with a short external deadline.
2. If it succeeds, retry the normal server command from that same terminal and capture the visible traceback/progress output; then compare with this environment.
3. If it fails with `WSAEACCES`, have the machine administrator review local loopback/Winsock/security policy for that Python executable. Do not disable security controls or change firewall settings blindly.

Only if the same stack reproduces outside the sandbox should a minimal Windows-compatible Daphne/Python remediation be evaluated. Keep Daphne installed for the ASGI/WebSocket application; do not remove it or bypass its event-loop initialization without compatibility tests.

## Verification plan after environment access is restored

- Confirm port 8000 free, start only the intended server, and verify `/login/` plus bounded `/health/` requests.
- Capture startup logs and confirm `django.setup()`, system checks, URL import, ASGI initialization and bind completion.
- Observe APScheduler startup/shutdown separately, without running maintenance tasks or database writes.
- Run browser acceptance only in a separate authenticated context with a disposable identity.

## Status

- Environment/process preflight: **PASS** (with process-inspection limitations above).
- Startup stall reproduction and stack attribution: **PASS**.
- Application-level root cause: **NOT CONFIRMED**; the confirmed blocker is local socket permission in this execution environment.
- Django checks, URL/ASGI startup, DB, scheduler runtime and server bind: **BLOCKED** at Daphne import.
- Source remediation: **NOT APPLIED**; read-only diagnosis only.
- MCP files/processes: **NOT TOUCHED**.

