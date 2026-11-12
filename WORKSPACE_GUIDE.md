# FINLO workspace guide

Runtime application folders: `finlo/`, `finlo_crm/`, `booking/`, `calls/`, `custom_fields/`, `templates/`, `static/`. Preserve migrations, translations and app assets. `finlo_jalali/` is an optional extension, not disposable data.

Operations and documentation: `docs/`, `.github/`, `debian/`, `windows-installer/`, `sync_db/`, deployment and investigation reports. Keep these unless their workflows are explicitly retired.

Local state: `.venv/`, `.env`, encryption/initialization keys and uploaded media must be preserved. Never copy real secrets into examples or deploy local media as application source.

Generated artifacts: Python `__pycache__`, Ruff caches and collected `staticfiles/` can be regenerated. Do not delete or regenerate them while a build/server operation depends on them.

The isolated `.pool-eval-deps/` packages were removed during cleanup; they were never the active virtual environment. Pool evaluation scripts are retained as diagnostic tools, not runtime dependencies. Reinstall their reviewed isolated dependencies before running them. Psycopg3 adoption remains NO-GO; production requirements still use psycopg2.

Cleanup did not remove source modules, database migrations, business data, keys, uploads, reports or the active virtual environment. Existing user deletions and unrelated edits were preserved. Both Python version files currently agree on Python 3.12 and are retained for their respective deployment consumers.
