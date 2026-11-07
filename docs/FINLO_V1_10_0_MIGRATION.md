# Finlo v1.10.0 Migration Guide

**Execution-ready runbook for moving Finlo support apps into `finlo.contrib` and dropping the `finlo_` prefix.**

> **Scope of this guide:** The 15 support apps listed in section 1. **`finlo_crm` is deferred to a follow-up migration** and is NOT covered here — leave its files, tables, and app label untouched during this refactor.
>
> **Database strategy:** All database state changes are expressed as Django migrations using `migrations.RunSQL(...)` with `reverse_sql`. No standalone Python scripts touch `django_migrations` or `django_content_type`. No ORM calls against those tables.
>
> **Target DB:** PostgreSQL (the SQL in this guide uses PG-specific syntax: `ALTER TABLE ... RENAME`, `pg_constraint`, `pg_indexes`, `DO $$ ... $$`, `jsonb`).

---

## Table of Contents

1. [App Refactoring](#1-app-refactoring)
2. [Codebase Updates](#2-codebase-updates)
3. [Permissions Migration](#3-permissions-migration)
4. [Database Migration Strategy (RunSQL only)](#4-database-migration-strategy-runsql-only)
5. [Foreign Key Dependency Handling](#5-foreign-key-dependency-handling)
6. [Indexes, Constraints, Sequences](#6-indexes-constraints-sequences)
7. [Execution Plan (strict order)](#7-execution-plan-strict-order)
8. [Rollback Plan](#8-rollback-plan)
9. [Risks & Edge Cases](#9-risks--edge-cases)
10. [Testing Checklist](#10-testing-checklist)
11. [Optional Automation / Verification Queries](#11-optional-automation--verification-queries)

---

## 1. App Refactoring

### 1.1 Canonical mapping

| # | Old package | Old app label | New package | New app label |
|---|---|---|---|---|
| 1 | `finlo_activity` | `finlo_activity` | `finlo.contrib.activity` | `activity` |
| 2 | `finlo_automations` | `finlo_automations` | `finlo.contrib.automations` | `automations` |
| 3 | `finlo_cadences` | `finlo_cadences` | `finlo.contrib.cadences` | `cadences` |
| 4 | `finlo_calendar` | `finlo_calendar` | `finlo.contrib.calendar` | `calendar` |
| 5 | `finlo_core` | `finlo_core` | `finlo.contrib.core` | `core` |
| 6 | `finlo_dashboard` | `finlo_dashboard` | `finlo.contrib.dashboard` | `dashboard` |
| 7 | `finlo_duplicates` | `finlo_duplicates` | `finlo.contrib.duplicates` | `duplicates` |
| 8 | `finlo_generics` | `finlo_generics` | `finlo.contrib.generics` | `generics` |
| 9 | `finlo_keys` | `finlo_keys` | `finlo.contrib.keys` | `keys` |
| 10 | `finlo_mail` | `finlo_mail` | `finlo.contrib.mail` | `mail` |
| 11 | `finlo_notifications` | `finlo_notifications` | `finlo.contrib.notifications` | `notifications` |
| 12 | `finlo_processes.approvals` | `approvals` | `finlo.contrib.process.approvals` | `approvals` |
| 13 | `finlo_processes.reviews` | `reviews` | `finlo.contrib.process.reviews` | `reviews` |
| 14 | `finlo_reports` | `finlo_reports` | `finlo.contrib.reports` | `reports` |
| 15 | `finlo_theme` | `finlo_theme` | `finlo.contrib.theme` | `theme` |
| 16 | `finlo_utils` | `finlo_utils` | `finlo.contrib.utils` | `utils` |

> **Note on `finlo_processes`:** the sub-app labels (`approvals`, `reviews`) already have no `finlo_` prefix, so the label itself doesn't change — but tables (e.g. `approvals_approval`) and `django_migrations` entries stay on the same label and don't need the SQL rewrites in section 4. Only the import path changes.
>
> **Note on `finlo_crm`:** out of scope for this migration. Do not move its directory, do not add RunSQL for its tables.

### 1.2 Directory move

Preserve git history using `git mv`:

```bash
# Create the new package
mkdir -p finlo/contrib
touch finlo/contrib/__init__.py

# Move each app (run once per app from the repo root)
git mv finlo_activity       finlo/contrib/activity
git mv finlo_automations    finlo/contrib/automations
git mv finlo_cadences       finlo/contrib/cadences
git mv finlo_calendar       finlo/contrib/calendar
git mv finlo_core           finlo/contrib/core
git mv finlo_dashboard      finlo/contrib/dashboard
git mv finlo_duplicates     finlo/contrib/duplicates
git mv finlo_generics       finlo/contrib/generics
git mv finlo_keys           finlo/contrib/keys
git mv finlo_mail           finlo/contrib/mail
git mv finlo_notifications  finlo/contrib/notifications
git mv finlo_processes      finlo/contrib/process
git mv finlo_reports        finlo/contrib/reports
git mv finlo_theme          finlo/contrib/theme
git mv finlo_utils          finlo/contrib/utils
```

Commit this as a single `[UPDT] CONTRIB: Move support apps under finlo.contrib` commit — do **not** include any other changes in this commit, so reviewers see pure renames.

### 1.3 `AppLauncher` subclass update

Before (example: `finlo_activity/apps.py`):

```python
class FinloActivityConfig(AppLauncher):
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo_activity"
    verbose_name = _("Activity")
    url_prefix = "activity/"
    url_module = "finlo_activity.urls"
    url_namespace = "finlo_activity"
    auto_import_modules = ["registration", "methods", "menu", "signals"]

    def get_api_paths(self):
        return [{
            "pattern": "/activity/",
            "view_or_include": "finlo_activity.api.urls",
            "name": "finlo_activity_api",
            "namespace": "finlo_activity",
        }]
```

After (`finlo/contrib/activity/apps.py`):

```python
class ActivityConfig(AppLauncher):
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.activity"
    label = "activity"                                    # NEW — pins the app_label
    verbose_name = _("Activity")
    url_prefix = "activity/"
    url_module = "finlo.contrib.activity.urls"
    url_namespace = "activity"
    auto_import_modules = ["registration", "methods", "menu", "signals"]

    def get_api_paths(self):
        return [{
            "pattern": "/activity/",
            "view_or_include": "finlo.contrib.activity.api.urls",
            "name": "activity_api",
            "namespace": "activity",
        }]
```

**Key fields that change:** `name`, `label` (add explicitly), `url_module`, `url_namespace`, `get_api_paths()` entries. Apply the same pattern to every app.

> **Why set `label` explicitly?** By default Django derives `label` from the trailing component of `name`. Setting it explicitly makes the label (`activity`) independent of the dotted path, and more importantly locks in the name that must match `django_migrations.app` and `django_content_type.app_label` after the SQL updates in section 4.

### 1.4 `finlo_processes` nested case

`finlo/contrib/process/__init__.py` stays empty. Its two sub-apps keep their existing labels:

```python
# finlo/contrib/process/approvals/apps.py
class ApprovalsConfig(AppLauncher):
    name = "finlo.contrib.process.approvals"
    label = "approvals"                 # UNCHANGED from before
    url_module = "finlo.contrib.process.approvals.urls"
    url_namespace = "approvals"
    # ...
```

Because `label` is unchanged, no rows in `django_migrations`, `django_content_type`, or table names need to be rewritten for `approvals` / `reviews`. Only code-level imports change.

---

## 2. Codebase Updates

All of this is **pure text refactoring** — nothing touches the database. Do it in a single commit immediately after the directory move.

### 2.1 `INSTALLED_APPS`

Edit [finlo/settings/base.py](../finlo/settings/base.py) — replace each string:

```python
INSTALLED_APPS = [
    # ...
    "finlo.contrib.core",
    "finlo.contrib.generics",
    "finlo.contrib.reports",
    "finlo.contrib.dashboard",
    "finlo.contrib.utils",
    "finlo.contrib.notifications",
    "finlo.contrib.mail",
    "finlo.contrib.automations",
    "finlo.contrib.activity",
    "finlo.contrib.calendar",
    "finlo.contrib.keys",
    "finlo.contrib.theme",
    "finlo.contrib.duplicates",
    "finlo.contrib.process.approvals",
    "finlo.contrib.process.reviews",
    "finlo.contrib.cadences",
    # finlo_crm  — leave as-is, not part of this migration
]
```

### 2.2 Python imports

Rewrite every `from finlo_<app> ...` and `import finlo_<app>`:

```
from finlo_activity.models import Activity      →  from finlo.contrib.activity.models import Activity
from finlo_core.models import FinloCoreModel  →  from finlo.contrib.core.models import FinloCoreModel
import finlo_mail                               →  from finlo.contrib import mail
```

Also watch for dotted-string references used by Django:

```python
# settings.py / AppLauncher fields / celery
"finlo_activity.signals"               →  "finlo.contrib.activity.signals"
"finlo_core.tasks.my_task"             →  "finlo.contrib.core.tasks.my_task"

# Model string refs in ForeignKey / M2M (rare but exist)
models.ForeignKey("finlo_core.FinloUser", ...)  →  models.ForeignKey("core.FinloUser", ...)
```

> The FK string reference uses the **app_label**, not the package path. So it becomes `"core.FinloUser"` (new app_label), not `"finlo.contrib.core.FinloUser"`.

### 2.3 URL reversals

```python
reverse("finlo_activity:activity_list")     →  reverse("activity:activity_list")
reverse_lazy("finlo_core:user_detail", ...)  →  reverse_lazy("core:user_detail", ...)
```

Also `{% url 'finlo_activity:...' %}` in templates.

### 2.4 Templates — static file paths

Replace every fully-qualified static reference:

```django
{% static 'finlo_activity/css/activity.css' %}   →  {% static 'activity/css/activity.css' %}
{% static 'finlo_theme/assets/img/icons/edit.svg' %}  →  {% static 'theme/assets/img/icons/edit.svg' %}
```

After the `git mv`, each app's static files live at `finlo/contrib/<app>/static/<app>/...`. The collected static namespace becomes `<app>/...` — which matches the templates above.

> Some apps already used abbreviated paths (e.g. `{% static 'cadences/css/cadence_detail.css' %}` in [finlo_cadences/templates/cadence_detail.html](../finlo_cadences/templates/cadence_detail.html)). These were already correct and need no change — just verify the static file actually lives at the unprefixed path after the move.

### 2.5 Global-replace checklist

Run these searches across the entire repo (exclude `migrations/`, `.git/`, virtualenvs):

| Pattern | Replacement | Notes |
|---|---|---|
| `from finlo_<app>` | `from finlo.contrib.<app>` | 15 apps |
| `import finlo_<app>` | `from finlo.contrib import <app>` | 15 apps |
| `"finlo_<app>.` | `"finlo.contrib.<app>.` | Celery task names, app-string refs |
| `'finlo_<app>:` | `'<app>:` | URL namespaces |
| `"finlo_<app>:` | `"<app>:` | URL namespaces |
| `{% static 'finlo_<app>/` | `{% static '<app>/` | Template static paths |
| `"finlo_<app>.<model>"` | `"<app>.<model>"` | FK string refs — use **label**, not package |
| `register_model_for_feature(app_label="finlo_<app>"` | `register_model_for_feature(app_label="<app>"` | `registration.py` files |
| `user.has_perm("finlo_<app>.<code>")` | `user.has_perm("<app>.<code>")` | Permission codename strings |
| `ContentType.objects.get(app_label="finlo_<app>"` | `ContentType.objects.get(app_label="<app>"` | Explicit content-type lookups |

> **Do not** run a naive find-and-replace across `migrations/` folders. Migration files reference the old label via `dependencies = [("finlo_activity", "0001_initial")]` and those must stay intact until the `django_migrations` table has been rewritten (section 4a). Django matches migration records by (`app`, `name`) tuples.
>
> **After** the RunSQL rewrite lands, a second code pass should update the migration files themselves so the in-memory migration graph matches the DB — see step 4 of section 7.

### 2.6 Hard-to-grep landmines

These don't follow a mechanical pattern — review each manually:

- **Signal dispatch by string:** `@receiver(signal, sender="finlo_core.FinloUser")` → `sender="core.FinloUser"`.
- **Auditlog config:** if `AUDITLOG_INCLUDE_TRACKING_MODELS` lists model strings, update them.
- **DRF router basenames** that embed the app label.
- **Fixture files** (`*.json`, `*.yaml`) with `"model": "finlo_activity.activity"` entries.
- **Menu registrations** (`menu.py` in each app) — if they use `reverse_lazy("finlo_<app>:...")`.
- **Celery beat schedules** (`celery_schedule_module` on `AppLauncher`) — task names are dotted paths.
- **`GenericForeignKey`/`ContentType`** filters that filter by `app_label=...`.

---

## 3. Permissions Migration

### 3.1 How Django permissions are stored

`auth_permission` has columns `(id, name, content_type_id, codename)`. The `content_type_id` is an FK into `django_content_type`. The app label lives **only** in `django_content_type.app_label` — it is NOT duplicated in `auth_permission`. So once section 4b rewrites `django_content_type.app_label`, every `Permission` row automatically reports the new label via `perm.content_type.app_label`.

**What this means:**

- `auth_group_permissions` and `auth_user_user_permissions` store FK IDs only — they need **no SQL changes**. Row integrity is preserved.
- Code that checks permissions by string (`user.has_perm("finlo_activity.view_activity")`) **does** break and must be updated (section 2.5, row "Permission codename strings").
- The four-layer CRM permission model is unaffected at the data layer — `FieldPermission` and `Role` tables continue to reference permissions via FK.

### 3.2 Verification queries (post-migration)

```sql
-- Every permission should resolve to a new-style app_label
SELECT ct.app_label, ct.model, COUNT(p.id) AS perm_count
FROM django_content_type ct
LEFT JOIN auth_permission p ON p.content_type_id = ct.id
WHERE ct.app_label LIKE 'finlo_%'
GROUP BY ct.app_label, ct.model;
-- Expected: 0 rows after migration.

-- Confirm group-permission assignments survived
SELECT g.name, COUNT(gp.permission_id) AS perms_assigned
FROM auth_group g
LEFT JOIN auth_group_permissions gp ON gp.group_id = g.id
GROUP BY g.name
ORDER BY g.name;
-- Compare counts to the snapshot you took before migration.
```

### 3.3 Custom CRM permission tables

If the CRM project defines supplementary permission tables that denormalize `app_label` as text (grep for `app_label` columns on custom tables), those need a targeted `UPDATE`. Add a RunSQL block for each such table using the template in section 4a.

---

## 4. Database Migration Strategy (RunSQL only)

Create a single new Django app dedicated to this migration — call it `finlo_v1_10_0_migration`. It contains no models, just a sequence of data migrations that run the SQL below in order.

```
finlo/contrib/_v1_10_0_migration/
├── __init__.py
├── apps.py                 # AppLauncher subclass with label="_v1_10_0_migration"
└── migrations/
    ├── __init__.py
    ├── 0001_migrations_table.py   # Section 4a
    ├── 0002_content_types.py      # Section 4b
    ├── 0003_rename_tables.py      # Section 4c + 4d
    ├── 0004_fk_constraints.py     # Section 5
    ├── 0005_indexes.py            # Section 6
    └── 0006_auditlog.py           # Section 4e
```

Add `"finlo.contrib._v1_10_0_migration"` to `INSTALLED_APPS` immediately after `finlo.contrib.core`. Leave it registered for at least one release after the migration ships so rollback is possible.

Each migration has `run_before = []` and `dependencies = []` deliberately empty — except that `0001` must run before any other migration for the renamed apps. Enforce that by declaring:

```python
dependencies = [
    ("activity",        "__latest__"),   # forces Django to consider activity migrated first
    # ... one entry per renamed app, using the NEW label
]
```

Actually — because the renames change `django_migrations.app`, you can't reference the new label until `0001` has run. Instead, run `0001` manually via `python manage.py migrate _v1_10_0_migration 0001` before Django's normal autoloader sees the renamed app configs. The execution order in section 7 handles this.

### 4a. Update `django_migrations`

**Raw SQL:**

```sql
BEGIN;

UPDATE django_migrations SET app = 'activity'       WHERE app = 'finlo_activity';
UPDATE django_migrations SET app = 'automations'    WHERE app = 'finlo_automations';
UPDATE django_migrations SET app = 'cadences'       WHERE app = 'finlo_cadences';
UPDATE django_migrations SET app = 'calendar'       WHERE app = 'finlo_calendar';
UPDATE django_migrations SET app = 'core'           WHERE app = 'finlo_core';
UPDATE django_migrations SET app = 'dashboard'      WHERE app = 'finlo_dashboard';
UPDATE django_migrations SET app = 'duplicates'     WHERE app = 'finlo_duplicates';
UPDATE django_migrations SET app = 'generics'       WHERE app = 'finlo_generics';
UPDATE django_migrations SET app = 'keys'           WHERE app = 'finlo_keys';
UPDATE django_migrations SET app = 'mail'           WHERE app = 'finlo_mail';
UPDATE django_migrations SET app = 'notifications'  WHERE app = 'finlo_notifications';
UPDATE django_migrations SET app = 'reports'        WHERE app = 'finlo_reports';
UPDATE django_migrations SET app = 'theme'          WHERE app = 'finlo_theme';
UPDATE django_migrations SET app = 'utils'          WHERE app = 'finlo_utils';

-- Verify: no rows should remain with finlo_ prefix for migrated apps
SELECT app, COUNT(*) FROM django_migrations
WHERE app LIKE 'finlo_%' AND app != 'finlo_crm'
GROUP BY app;
-- Expected: 0 rows.

COMMIT;
```

**Django migration (`_v1_10_0_migration/migrations/0001_migrations_table.py`):**

```python
from django.db import migrations

APPS = [
    ("finlo_activity",      "activity"),
    ("finlo_automations",   "automations"),
    ("finlo_cadences",      "cadences"),
    ("finlo_calendar",      "calendar"),
    ("finlo_core",          "core"),
    ("finlo_dashboard",     "dashboard"),
    ("finlo_duplicates",    "duplicates"),
    ("finlo_generics",      "generics"),
    ("finlo_keys",          "keys"),
    ("finlo_mail",          "mail"),
    ("finlo_notifications", "notifications"),
    ("finlo_reports",       "reports"),
    ("finlo_theme",         "theme"),
    ("finlo_utils",         "utils"),
]

FORWARD = "\n".join(
    f"UPDATE django_migrations SET app = '{new}' WHERE app = '{old}';"
    for old, new in APPS
)

REVERSE = "\n".join(
    f"UPDATE django_migrations SET app = '{old}' WHERE app = '{new}';"
    for old, new in APPS
)


class Migration(migrations.Migration):
    initial = True
    atomic = True
    dependencies = []
    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
```

### 4b. Update `django_content_type`

**Raw SQL:**

```sql
BEGIN;

UPDATE django_content_type SET app_label = 'activity'       WHERE app_label = 'finlo_activity';
UPDATE django_content_type SET app_label = 'automations'    WHERE app_label = 'finlo_automations';
UPDATE django_content_type SET app_label = 'cadences'       WHERE app_label = 'finlo_cadences';
UPDATE django_content_type SET app_label = 'calendar'       WHERE app_label = 'finlo_calendar';
UPDATE django_content_type SET app_label = 'core'           WHERE app_label = 'finlo_core';
UPDATE django_content_type SET app_label = 'dashboard'      WHERE app_label = 'finlo_dashboard';
UPDATE django_content_type SET app_label = 'duplicates'     WHERE app_label = 'finlo_duplicates';
UPDATE django_content_type SET app_label = 'generics'       WHERE app_label = 'finlo_generics';
UPDATE django_content_type SET app_label = 'keys'           WHERE app_label = 'finlo_keys';
UPDATE django_content_type SET app_label = 'mail'           WHERE app_label = 'finlo_mail';
UPDATE django_content_type SET app_label = 'notifications'  WHERE app_label = 'finlo_notifications';
UPDATE django_content_type SET app_label = 'reports'        WHERE app_label = 'finlo_reports';
UPDATE django_content_type SET app_label = 'theme'          WHERE app_label = 'finlo_theme';
UPDATE django_content_type SET app_label = 'utils'          WHERE app_label = 'finlo_utils';

-- Verify
SELECT app_label, COUNT(*) FROM django_content_type
WHERE app_label LIKE 'finlo_%' AND app_label != 'finlo_crm'
GROUP BY app_label;
-- Expected: 0 rows.

COMMIT;
```

**Django migration (`_v1_10_0_migration/migrations/0002_content_types.py`):**

```python
from django.db import migrations

APPS = [
    ("finlo_activity",      "activity"),
    ("finlo_automations",   "automations"),
    ("finlo_cadences",      "cadences"),
    ("finlo_calendar",      "calendar"),
    ("finlo_core",          "core"),
    ("finlo_dashboard",     "dashboard"),
    ("finlo_duplicates",    "duplicates"),
    ("finlo_generics",      "generics"),
    ("finlo_keys",          "keys"),
    ("finlo_mail",          "mail"),
    ("finlo_notifications", "notifications"),
    ("finlo_reports",       "reports"),
    ("finlo_theme",         "theme"),
    ("finlo_utils",         "utils"),
]

FORWARD = "\n".join(
    f"UPDATE django_content_type SET app_label = '{new}' WHERE app_label = '{old}';"
    for old, new in APPS
)

REVERSE = "\n".join(
    f"UPDATE django_content_type SET app_label = '{old}' WHERE app_label = '{new}';"
    for old, new in APPS
)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("_v1_10_0_migration", "0001_migrations_table")]
    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
```

### 4c. Rename tables

Django names tables `<app_label>_<model_name_lower>`. All tables prefixed with `finlo_<app>_` must be renamed to `<app>_`.

**Discovery (run on staging to build the exact list):**

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND (
    tablename LIKE 'finlo_activity_%'      OR
    tablename LIKE 'finlo_automations_%'   OR
    tablename LIKE 'finlo_cadences_%'      OR
    tablename LIKE 'finlo_calendar_%'      OR
    tablename LIKE 'finlo_core_%'          OR
    tablename LIKE 'finlo_dashboard_%'     OR
    tablename LIKE 'finlo_duplicates_%'    OR
    tablename LIKE 'finlo_generics_%'      OR
    tablename LIKE 'finlo_keys_%'          OR
    tablename LIKE 'finlo_mail_%'          OR
    tablename LIKE 'finlo_notifications_%' OR
    tablename LIKE 'finlo_reports_%'       OR
    tablename LIKE 'finlo_theme_%'         OR
    tablename LIKE 'finlo_utils_%'
  )
ORDER BY tablename;
```

**Raw SQL — table rename examples:**

```sql
ALTER TABLE finlo_activity_activity RENAME TO activity_activity;
ALTER TABLE finlo_core_finlouser   RENAME TO core_finlouser;
-- ... one per discovered table
```

**Django migration using a PL/pgSQL loop (`_v1_10_0_migration/migrations/0003_rename_tables.py`):**

Use a data-driven loop rather than hard-coding hundreds of ALTER statements. PostgreSQL auto-updates FK *references* on RENAME, so a simple per-table loop is safe.

```python
from django.db import migrations

APP_PREFIXES = [
    ("finlo_activity_",      "activity_"),
    ("finlo_automations_",   "automations_"),
    ("finlo_cadences_",      "cadences_"),
    ("finlo_calendar_",      "calendar_"),
    ("finlo_core_",          "core_"),
    ("finlo_dashboard_",     "dashboard_"),
    ("finlo_duplicates_",    "duplicates_"),
    ("finlo_generics_",      "generics_"),
    ("finlo_keys_",          "keys_"),
    ("finlo_mail_",          "mail_"),
    ("finlo_notifications_", "notifications_"),
    ("finlo_reports_",       "reports_"),
    ("finlo_theme_",         "theme_"),
    ("finlo_utils_",         "utils_"),
]


def _rename_sql(pairs):
    blocks = []
    for old_prefix, new_prefix in pairs:
        blocks.append(f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename LIKE '{old_prefix}%'
          LOOP
            EXECUTE format(
              'ALTER TABLE public.%I RENAME TO %I',
              r.tablename,
              '{new_prefix}' || substring(r.tablename from {len(old_prefix) + 1})
            );
          END LOOP;
        END $$;
        """)
    return "\n".join(blocks)


FORWARD = _rename_sql(APP_PREFIXES)
REVERSE = _rename_sql([(new, old) for old, new in APP_PREFIXES])


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("_v1_10_0_migration", "0002_content_types")]
    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
```

### 4d. ManyToMany join tables

M2M tables follow Django's default naming: `<app_label>_<model>_<field>`, e.g. `finlo_activity_activity_assigned_to`. The loop in 4c already catches these because they share the `finlo_<app>_` prefix. **No additional migration needed** — verify with:

```sql
SELECT tablename FROM pg_tables
WHERE schemaname = 'public' AND tablename LIKE 'finlo_%' AND tablename != 'finlo_crm_%';
-- Expected: 0 rows (ignoring finlo_crm which is out of scope).
```

> If any M2M table was given a custom name via `db_table` in a `through` model, the loop misses it. Grep the codebase for `db_table = "finlo_` and add explicit `ALTER TABLE` statements for those.

### 4e. Update `auditlog_logentry`

`django-auditlog` stores:
- `object_repr` (text) — human-readable row representation, may embed app label.
- `changes` (jsonb or text depending on auditlog version) — per-field change dict.
- `content_type_id` (FK) — already handled by 4b.

The `content_type_id` FK means filtered lookups by app work correctly post-migration. But if `object_repr` or `changes` text embeds strings like `"finlo_activity.Activity object (1)"`, those stay stale.

**Raw SQL:**

```sql
BEGIN;

-- object_repr: plain text REPLACE (safe — only affects exact-match substrings)
UPDATE auditlog_logentry
SET object_repr = REPLACE(object_repr, 'finlo_activity.',      'activity.')
WHERE object_repr LIKE '%finlo_activity.%';

-- Repeat one UPDATE per app, or use the loop below

-- changes column (jsonb): convert to text, replace, convert back
UPDATE auditlog_logentry
SET changes = REPLACE(changes::text, 'finlo_activity.', 'activity.')::jsonb
WHERE changes::text LIKE '%finlo_activity.%';

COMMIT;
```

**Django migration (`_v1_10_0_migration/migrations/0006_auditlog.py`):**

```python
from django.db import migrations

APPS = [
    ("finlo_activity",      "activity"),
    ("finlo_automations",   "automations"),
    ("finlo_cadences",      "cadences"),
    ("finlo_calendar",      "calendar"),
    ("finlo_core",          "core"),
    ("finlo_dashboard",     "dashboard"),
    ("finlo_duplicates",    "duplicates"),
    ("finlo_generics",      "generics"),
    ("finlo_keys",          "keys"),
    ("finlo_mail",          "mail"),
    ("finlo_notifications", "notifications"),
    ("finlo_reports",       "reports"),
    ("finlo_theme",         "theme"),
    ("finlo_utils",         "utils"),
]


def _build(old_to_new_pairs):
    parts = []
    for old, new in old_to_new_pairs:
        parts.append(f"""
        UPDATE auditlog_logentry
        SET object_repr = REPLACE(object_repr, '{old}.', '{new}.')
        WHERE object_repr LIKE '%{old}.%';

        UPDATE auditlog_logentry
        SET changes = REPLACE(changes::text, '{old}.', '{new}.')::jsonb
        WHERE changes::text LIKE '%{old}.%';
        """)
    return "\n".join(parts)


FORWARD = _build(APPS)
REVERSE = _build([(new, old) for old, new in APPS])


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("_v1_10_0_migration", "0005_indexes")]
    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
```

> **Caveat on text REPLACE:** if any model field legitimately contains the literal string `finlo_activity.` in its value (not as an app-label reference), this REPLACE will corrupt it. Audit logs rarely contain free-form user text at that path, but if your project has an exception, scope the UPDATE with an additional `AND` clause narrowing to fields where the substring is known to be a reference.

---

## 5. Foreign Key Dependency Handling

### 5.1 What PostgreSQL auto-renames on `ALTER TABLE ... RENAME`

| Rewritten automatically | Left alone |
|---|---|
| FK *target* references to the renamed table (the FK still points to the right table) | FK constraint **names** (`finlo_core_finlouser_id_abc123_fk_finlo_core_...`) |
| The table entry in `pg_class` | Index names (`finlo_activity_activity_date_idx`) |
| Primary key sequence (`<table>_id_seq` when renamed via `ALTER SEQUENCE` or auto-associated) | Explicit sequence names (custom `db_column_sequence`) |
|  | Trigger names |
|  | Unique constraint names |
|  | Check constraint names |

So after section 4c runs, **the data integrity is intact** — FKs continue to work. But the object names are misleading: the table `core_finlouser` has FK constraints named `finlo_core_finlouser_...`. Django's autodetector may try to "fix" these on a future migration by DROP+CREATE, which locks tables. Rename them explicitly now.

### 5.2 Discovery query

```sql
-- Find FKs whose NAME still references an old app prefix
SELECT
    conname                      AS constraint_name,
    conrelid::regclass           AS on_table,
    confrelid::regclass          AS references_table
FROM pg_constraint
WHERE contype = 'f'
  AND (
        conname LIKE 'finlo_activity_%'      OR
        conname LIKE 'finlo_automations_%'   OR
        conname LIKE 'finlo_cadences_%'      OR
        conname LIKE 'finlo_calendar_%'      OR
        conname LIKE 'finlo_core_%'          OR
        conname LIKE 'finlo_dashboard_%'     OR
        conname LIKE 'finlo_duplicates_%'    OR
        conname LIKE 'finlo_generics_%'      OR
        conname LIKE 'finlo_keys_%'          OR
        conname LIKE 'finlo_mail_%'          OR
        conname LIKE 'finlo_notifications_%' OR
        conname LIKE 'finlo_reports_%'       OR
        conname LIKE 'finlo_theme_%'         OR
        conname LIKE 'finlo_utils_%'
      )
ORDER BY on_table, conname;
```

### 5.3 Rename example

```sql
ALTER TABLE core_finlouser
RENAME CONSTRAINT finlo_core_finlouser_company_id_abc123_fk_finlo_core_company_id
              TO core_finlouser_company_id_abc123_fk_core_company_id;
```

### 5.4 Django migration (`_v1_10_0_migration/migrations/0004_fk_constraints.py`)

```python
from django.db import migrations

OLD_PREFIXES = [
    "finlo_activity_",
    "finlo_automations_",
    "finlo_cadences_",
    "finlo_calendar_",
    "finlo_core_",
    "finlo_dashboard_",
    "finlo_duplicates_",
    "finlo_generics_",
    "finlo_keys_",
    "finlo_mail_",
    "finlo_notifications_",
    "finlo_reports_",
    "finlo_theme_",
    "finlo_utils_",
]


def _rename_constraints(prefixes, direction):
    """
    direction='forward'  -> strip 'finlo_' from matching constraint names
    direction='reverse'  -> re-add 'finlo_'
    """
    blocks = []
    for prefix in prefixes:
        if direction == "forward":
            old_like = prefix + "%"
            new_prefix = prefix.removeprefix("finlo_")
            old_trim = len(prefix)
        else:
            new_prefix = "finlo_" + prefix.removeprefix("finlo_")
            old_like = prefix.removeprefix("finlo_") + "%"
            old_trim = len(prefix.removeprefix("finlo_"))

        blocks.append(f"""
        DO $$
        DECLARE r RECORD;
        DECLARE new_name TEXT;
        BEGIN
          FOR r IN
            SELECT conname, conrelid::regclass AS tbl
            FROM pg_constraint
            WHERE conname LIKE '{old_like}' AND contype IN ('f', 'p', 'u', 'c')
          LOOP
            new_name := '{new_prefix}' || substring(r.conname from {old_trim + 1});
            EXECUTE format(
              'ALTER TABLE %s RENAME CONSTRAINT %I TO %I',
              r.tbl, r.conname, new_name
            );
          END LOOP;
        END $$;
        """)
    return "\n".join(blocks)


FORWARD = _rename_constraints(OLD_PREFIXES, "forward")
REVERSE = _rename_constraints(OLD_PREFIXES, "reverse")


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("_v1_10_0_migration", "0003_rename_tables")]
    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
```

### 5.5 Verification

```sql
SELECT conname FROM pg_constraint
WHERE conname LIKE 'finlo_%'
  AND conname NOT LIKE 'finlo_crm_%';
-- Expected: 0 rows.
```

---

## 6. Indexes, Constraints, Sequences

### 6.1 Rename behavior summary

| Object | Renamed on `ALTER TABLE ... RENAME`? | Action required |
|---|---|---|
| Table itself | Yes | — |
| FK target references | Yes (implicit) | — |
| PK sequence (`<table>_id_seq` linked via `SERIAL`/`IDENTITY`) | **Sometimes** — PG ≥ 14 renames implicit identity sequences; older or explicit `SERIAL` sequences may not | Verify and rename if needed |
| Primary-key constraint | No | Rename (section 5.4 loop covers) |
| Unique constraint | No | Rename (section 5.4 loop covers) |
| Check constraint | No | Rename (section 5.4 loop covers) |
| Foreign-key constraint | No | Rename (section 5.4 loop covers) |
| Indexes (non-constraint) | No | Rename (this section) |
| Triggers | No | Rename if any Finlo code creates triggers |

### 6.2 Per-table audit

```sql
\d+ core_finlouser
-- Look at "Indexes:" and "Foreign-key constraints:" sections
-- anything prefixed finlo_<app>_ needs renaming
```

### 6.3 Index rename — Django migration (`_v1_10_0_migration/migrations/0005_indexes.py`)

```python
from django.db import migrations

OLD_PREFIXES = [
    "finlo_activity_",
    "finlo_automations_",
    "finlo_cadences_",
    "finlo_calendar_",
    "finlo_core_",
    "finlo_dashboard_",
    "finlo_duplicates_",
    "finlo_generics_",
    "finlo_keys_",
    "finlo_mail_",
    "finlo_notifications_",
    "finlo_reports_",
    "finlo_theme_",
    "finlo_utils_",
]


def _rename_indexes(prefixes, direction):
    blocks = []
    for prefix in prefixes:
        if direction == "forward":
            old_like = prefix + "%"
            new_prefix = prefix.removeprefix("finlo_")
            old_trim = len(prefix)
        else:
            old_like = prefix.removeprefix("finlo_") + "%"
            new_prefix = "finlo_" + prefix.removeprefix("finlo_")
            old_trim = len(prefix.removeprefix("finlo_"))

        blocks.append(f"""
        DO $$
        DECLARE r RECORD;
        DECLARE new_name TEXT;
        BEGIN
          FOR r IN
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public' AND indexname LIKE '{old_like}'
          LOOP
            new_name := '{new_prefix}' || substring(r.indexname from {old_trim + 1});
            -- Skip if it's a constraint-backing index (already renamed in 0004)
            IF NOT EXISTS (
              SELECT 1 FROM pg_constraint
              WHERE conname = r.indexname
            ) THEN
              EXECUTE format('ALTER INDEX public.%I RENAME TO %I', r.indexname, new_name);
            END IF;
          END LOOP;
        END $$;
        """)

        # Also handle sequences
        blocks.append(f"""
        DO $$
        DECLARE r RECORD;
        DECLARE new_name TEXT;
        BEGIN
          FOR r IN
            SELECT sequencename FROM pg_sequences
            WHERE schemaname = 'public' AND sequencename LIKE '{old_like}'
          LOOP
            new_name := '{new_prefix}' || substring(r.sequencename from {old_trim + 1});
            EXECUTE format('ALTER SEQUENCE public.%I RENAME TO %I', r.sequencename, new_name);
          END LOOP;
        END $$;
        """)
    return "\n".join(blocks)


FORWARD = _rename_indexes(OLD_PREFIXES, "forward")
REVERSE = _rename_indexes(OLD_PREFIXES, "reverse")


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("_v1_10_0_migration", "0004_fk_constraints")]
    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
```

### 6.4 Verification

```sql
-- Indexes
SELECT indexname FROM pg_indexes
WHERE indexname LIKE 'finlo_%' AND indexname NOT LIKE 'finlo_crm_%';
-- Expected: 0 rows.

-- Sequences
SELECT sequencename FROM pg_sequences
WHERE sequencename LIKE 'finlo_%' AND sequencename NOT LIKE 'finlo_crm_%';
-- Expected: 0 rows.

-- Constraints (from section 5.5)
SELECT conname FROM pg_constraint
WHERE conname LIKE 'finlo_%' AND conname NOT LIKE 'finlo_crm_%';
-- Expected: 0 rows.
```

---

## 7. Execution Plan (strict order)

Do this on staging first. End-to-end on staging before scheduling production.

### Step 1 — Full DB backup

```bash
pg_dump -Fc -f finlo_pre_v1_10_0_$(date +%Y%m%d_%H%M).dump finlo_prod
```

Verify the dump restores cleanly to a scratch DB before proceeding.

### Step 2 — Freeze writes

Put the application into read-only or maintenance mode. For Celery: `celery control cancel_consumer <queue>`. Deploy a maintenance banner to the load balancer.

### Step 3 — Snapshot pre-migration state

```sql
-- Row counts per table (save output)
SELECT schemaname, tablename,
       (xpath('/row/c/text()', query_to_xml(format('SELECT COUNT(*) AS c FROM %I.%I', schemaname, tablename), false, true, '')))[1]::text::int AS row_count
FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Permission-to-group assignments (for later diff)
SELECT g.name, p.codename, ct.app_label
FROM auth_group g
JOIN auth_group_permissions gp ON gp.group_id = g.id
JOIN auth_permission p ON p.id = gp.permission_id
JOIN django_content_type ct ON ct.id = p.content_type_id
ORDER BY g.name, ct.app_label, p.codename;
```

Save both outputs to compare after migration.

### Step 4 — Deploy code refactor (do NOT run `migrate`)

Deploy the commits from section 1 (`git mv`) and section 2 (import/template rewrites, `INSTALLED_APPS` update, `AppLauncher` field updates). **Critical:** also update `dependencies = [("finlo_activity", ...)]` in the actual app migration files to `[("activity", ...)]` — otherwise Django's migration loader can't match the new app registry entries to the old `django_migrations` rows (it matches by `app` label).

The migration-file rewrites need to happen in a separate commit landed with the same deploy:

```python
# finlo/contrib/activity/migrations/0002_initial.py
class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),          # was ("finlo_core", "0001_initial")
        ("activity", "0001_initial"),      # was ("finlo_activity", "0001_initial")
    ]
```

Do **not** run `python manage.py migrate` yet. Django will fail the graph check because `django_migrations` still has old labels.

### Step 5 — Apply `django_migrations` + `django_content_type` SQL

Because Django's migration loader can't build the graph against a mismatched `django_migrations` table, run the first two migrations bypassing autoloader state:

```bash
python manage.py migrate _v1_10_0_migration 0002_content_types --fake-initial
```

This applies `0001_migrations_table` → `0002_content_types`. After it finishes, `django_migrations.app` and `django_content_type.app_label` are rewritten. Django's graph now lines up with the new `INSTALLED_APPS`.

### Step 6 — Rename tables + M2M tables

```bash
python manage.py migrate _v1_10_0_migration 0003_rename_tables
```

### Step 7 — Rename FK constraints

```bash
python manage.py migrate _v1_10_0_migration 0004_fk_constraints
```

### Step 8 — Rename indexes and sequences

```bash
python manage.py migrate _v1_10_0_migration 0005_indexes
```

### Step 9 — Rewrite audit logs

```bash
python manage.py migrate _v1_10_0_migration 0006_auditlog
```

### Step 10 — Run normal `migrate` and confirm clean graph

```bash
python manage.py migrate
```

Expected output: `No migrations to apply.` If Django reports pending migrations, investigate — most commonly it means the per-app migration files in step 4 weren't updated, or an `AppLauncher` subclass still references the old `name`.

Also run:

```bash
python manage.py makemigrations --dry-run --check
```

Expected: exit code 0, no changes detected.

### Step 11 — Clear content-type cache and smoke test

```python
# Run via `python manage.py shell`
from django.contrib.contenttypes.models import ContentType
ContentType.objects.clear_cache()
```

Restart the web processes, Celery workers, Channels workers. Lift the maintenance banner. Run the checklist in section 10.

---

## 8. Rollback Plan

### 8.1 Primary rollback — restore backup

If anything fails at step 5–10 and the system isn't yet serving traffic:

```bash
dropdb finlo_prod
createdb finlo_prod
pg_restore -d finlo_prod finlo_pre_v1_10_0_YYYYMMDD_HHMM.dump
```

Roll back the code deploy to the pre-migration commit. Total downtime = restore time + redeploy time.

### 8.2 Secondary rollback — migration reverse

Only safe if **no writes have landed** since step 5 (i.e., the app is still in maintenance mode).

```bash
python manage.py migrate _v1_10_0_migration zero
```

This runs each migration's `reverse_sql` in reverse order (0006 → 0001). It rewrites `django_migrations` and `django_content_type` back to `finlo_*` labels, renames tables back, restores constraint/index names, and reverts audit log text.

After that, roll back the code deploy.

> **Why the backup is primary:** the reverse SQL is mechanical, but if any concurrent write has created rows under the new labels, the reverse migration will leave those rows stranded under labels that no longer match running code. The `pg_dump` restore is unconditional.

---

## 9. Risks & Edge Cases

| # | Risk | Mitigation |
|---|---|---|
| 1 | **ContentType cache stale after rewrite** — long-running Celery workers will keep the old `app_label` in memory and look up permissions against a label that no longer exists. | Restart all workers after step 10; `ContentType.objects.clear_cache()` in a post-migrate hook. |
| 2 | **Hardcoded permission strings** — `user.has_perm("finlo_activity.view_activity")` silently returns `False` after migration because no perm matches that string. | Section 2.5 grep sweep; add a runtime deprecation warning in `has_perm` during transition if feasible. |
| 3 | **`ContentType` IDs are stable but `app_label.model` strings are not** — third-party integrations that stored `"finlo_core.finlouser"` as a string will break; those that stored `content_type_id` (integer) keep working. | Audit any external integration for stored app-label strings. IDs in `django_content_type.id` are unchanged by the migration. |
| 4 | **Celery task names** are dotted module paths. Tasks queued before the code deploy will reference `finlo_activity.tasks.send_email` which no longer exists. | Drain Celery queues before step 4 (step 2 covers this). Add aliases via `@shared_task(name="finlo_activity.tasks.send_email")` for one release cycle if long-tail tasks are expected. |
| 5 | **Fixtures** (`dumpdata` output stored in `fixtures/`) reference models by `"<app_label>.<model>"`. Loading old fixtures into a migrated DB fails with `LookupError`. | Regenerate fixtures post-migration: `python manage.py dumpdata > fixtures/new.json`. Document that pre-v1.10.0 fixtures are no longer loadable. |
| 6 | **`finlo_processes` sub-apps** — labels (`approvals`, `reviews`) don't change, only the import path does. Skipping them from section 4's SQL is intentional. | Do not add `approvals`/`reviews` to the APPS list in `_v1_10_0_migration/0001` or `0002`. Confirm with `SELECT app FROM django_migrations WHERE app IN ('approvals','reviews');` before and after — count should be identical. |
| 7 | **`finlo_crm` left as-is** — its tables, content types, and migrations stay prefixed `finlo_crm_*`. All SQL in section 4 explicitly excludes `finlo_crm_` via `AND app_label != 'finlo_crm'` / `WHERE tablename NOT LIKE 'finlo_crm_%'`. | Verify with `SELECT app FROM django_migrations WHERE app = 'finlo_crm';` — rows should exist untouched. |
| 8 | **Custom `db_table` overrides** — if any model sets `class Meta: db_table = "finlo_..."`, the loop in 4c catches it, but the matching `db_table` string in code still needs updating. | Grep `db_table = "finlo_` in models; either update the string (and skip the SQL rename for that table) or leave both alone. Consistency matters more than which you choose. |
| 9 | **Migration graph mismatch** — Django loads `INSTALLED_APPS` before it can inspect `django_migrations`. If `INSTALLED_APPS` says `finlo.contrib.activity` (label `activity`) but `django_migrations` still says `finlo_activity`, the loader emits `InconsistentMigrationHistory`. | Section 7's step 5 uses `--fake-initial` and runs only the `_v1_10_0_migration` app until the table is rewritten, sidestepping the graph check for other apps. Never run bare `python manage.py migrate` between steps 4 and 10. |
| 10 | **Downtime window longer than expected** — the table-rename loop is fast (metadata only) but can wait on locks if any session holds one. | Run each step with `SET lock_timeout = '30s'` so a stuck rename fails fast rather than queuing behind a long-held lock. Maintenance mode in step 2 should prevent this. |
| 11 | **Third-party app with a signal handler** imported as `from finlo_core.models import FinloUser` at module-import time. | Section 2.2 catches this in grep; verify Django starts cleanly (`python manage.py check --deploy`) before step 5. |
| 12 | **Tenant isolation via `company` FK** is unaffected — FK target columns are renamed automatically, data rows untouched. | Run a sanity query post-migration: `SELECT company_id, COUNT(*) FROM core_finlouser GROUP BY company_id;` compare to pre-snapshot. |

---

## 10. Testing Checklist

Run on staging after step 10, on production after step 11.

### 10.1 Smoke tests

- [ ] Django admin: log in, browse every app's change-list, open one record per model.
- [ ] Django system check: `python manage.py check` exits 0.
- [ ] Migration graph check: `python manage.py makemigrations --dry-run --check` exits 0.
- [ ] Django shell: `from finlo.contrib.core.models import FinloUser` works.
- [ ] Django shell: `from django.contrib.contenttypes.models import ContentType; ContentType.objects.get(app_label="activity", model="activity")` returns a row.

### 10.2 API smoke tests

- [ ] Hit one endpoint from each app's `get_api_paths()` with an authenticated request.
- [ ] Confirm DRF router basenames resolve (`reverse("activity-list")` vs. `reverse("finlo_activity-list")`).
- [ ] `/admin/doc/` (if `django.contrib.admindocs` is enabled) lists all models under the new labels.

### 10.3 Permission layers (all four)

- [ ] Model-level: `user.has_perm("activity.view_activity")` returns `True` for an authorized user.
- [ ] Field-level: a `FieldPermission` row for `(user, "activity.activity.date")` still enforces readonly in the form.
- [ ] Row-level (`OWNER_FIELDS`): users see only their own rows in list views; `OwnerFiltersetMixin` still filters.
- [ ] Role hierarchy: a child role still inherits parent permissions; `Role.parent_role` self-FK intact.

### 10.4 Data integrity

- [ ] Row counts per table match the pre-migration snapshot from step 3.
- [ ] `SELECT COUNT(*) FROM core_finlouser;` equals pre-migration `finlo_core_finlouser` count.
- [ ] No orphaned FKs: `SELECT conname FROM pg_constraint WHERE NOT convalidated;` returns 0 rows.
- [ ] M2M spot-check: pick 5 users, compare their group memberships to the pre-snapshot.

### 10.5 Audit log readability

- [ ] Open a record's change history in the admin — entries from before and after the migration both display without errors.
- [ ] `auditlog_logentry.changes` contains no remaining `finlo_<app>.` substrings: `SELECT COUNT(*) FROM auditlog_logentry WHERE changes::text LIKE '%finlo_%' AND changes::text NOT LIKE '%finlo_crm%';` returns 0.

### 10.6 Background jobs

- [ ] Celery worker starts without import errors.
- [ ] APScheduler jobs from `celery_schedule_module` register and fire.
- [ ] Channels consumers connect (WebSocket notifications work).

### 10.7 Multi-tenancy

- [ ] `CompanyFilteredManager` still filters by company on a query against each migrated model.
- [ ] Cross-company access via `all_objects` manager still works.

---

## 11. Optional Automation / Verification Queries

> **Scope note:** code-side refactoring (imports, templates, URL namespaces) is handled manually by the dev team per their decision. This section lists only DB-level verification queries that can be run ad-hoc during or after the migration.

### 11.1 Pre-flight verification

```sql
-- Confirm there are NO remaining finlo_<app>_ tables except finlo_crm_*
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'finlo_%'
  AND tablename NOT LIKE 'finlo_crm_%';
-- Expected after migration: 0 rows.

-- Confirm no stale app_labels in content types
SELECT app_label, COUNT(*) FROM django_content_type
WHERE app_label LIKE 'finlo_%' AND app_label != 'finlo_crm'
GROUP BY app_label;
-- Expected: 0 rows.

-- Confirm no stale django_migrations entries
SELECT app, COUNT(*) FROM django_migrations
WHERE app LIKE 'finlo_%' AND app != 'finlo_crm'
GROUP BY app;
-- Expected: 0 rows.

-- Confirm no stale constraint/index/sequence names
SELECT 'constraint' AS obj_type, conname AS name FROM pg_constraint
  WHERE conname LIKE 'finlo_%' AND conname NOT LIKE 'finlo_crm_%'
UNION ALL
SELECT 'index', indexname FROM pg_indexes
  WHERE indexname LIKE 'finlo_%' AND indexname NOT LIKE 'finlo_crm_%'
UNION ALL
SELECT 'sequence', sequencename FROM pg_sequences
  WHERE sequencename LIKE 'finlo_%' AND sequencename NOT LIKE 'finlo_crm_%';
-- Expected: 0 rows.
```

### 11.2 Row-count parity

```sql
-- For each renamed table, count rows and compare to pre-migration snapshot
SELECT 'activity_activity' AS tbl, COUNT(*) FROM activity_activity
UNION ALL SELECT 'core_horillauser',   COUNT(*) FROM core_finlouser
UNION ALL SELECT 'core_company',       COUNT(*) FROM core_company;
-- ... extend to every migrated table
```

### 11.3 Permission-assignment parity

```sql
-- Compare post-migration group-permission assignments to the pre-snapshot from step 3
SELECT g.name, p.codename, ct.app_label
FROM auth_group g
JOIN auth_group_permissions gp ON gp.group_id = g.id
JOIN auth_permission p ON p.id = gp.permission_id
JOIN django_content_type ct ON ct.id = p.content_type_id
ORDER BY g.name, ct.app_label, p.codename;
-- Expected: identical row-for-row to pre-snapshot, with app_label rewritten from finlo_<x> to <x>.
```

### 11.4 Orphan FK detection

```sql
-- Any FKs that failed validation
SELECT conname, conrelid::regclass AS table, confrelid::regclass AS references
FROM pg_constraint
WHERE contype = 'f' AND NOT convalidated;
-- Expected: 0 rows.
```

### 11.5 Content-type cache sanity

```python
# python manage.py shell
from django.contrib.contenttypes.models import ContentType

for ct in ContentType.objects.filter(app_label__startswith="finlo_").exclude(app_label="finlo_crm"):
    print(f"STALE: {ct.app_label}.{ct.model}")
# Expected: no output.
```

---

## Appendix A — Order-of-operations summary

```
1. pg_dump backup
2. Maintenance mode ON
3. Snapshot row counts + perm assignments
4. Deploy code (git mv, imports, templates, INSTALLED_APPS, migration-file deps)
5. migrate _v1_10_0_migration 0002_content_types  --fake-initial
6. migrate _v1_10_0_migration 0003_rename_tables
7. migrate _v1_10_0_migration 0004_fk_constraints
8. migrate _v1_10_0_migration 0005_indexes
9. migrate _v1_10_0_migration 0006_auditlog
10. migrate  (expect: "No migrations to apply.")
11. ContentType.objects.clear_cache(); restart workers
12. Run section 10 testing checklist
13. Maintenance mode OFF
```

## Appendix B — File-level critical path

Files that MUST be edited in the section-2 code refactor:

- [finlo/settings/base.py](../finlo/settings/base.py) — `INSTALLED_APPS`
- One `apps.py` per app (15 files) — `AppLauncher` subclass: `name`, `label`, `url_module`, `url_namespace`, `get_api_paths()`
- One `urls.py` per app (15 files) — `app_name = "<new_label>"`
- One `registration.py` per app (wherever present) — `register_model_for_feature(app_label="<new_label>", ...)`
- Every template with `{% static 'finlo_<app>/...' %}` references
- Every Python file importing from `finlo_<app>`
- Every app's migration files — `dependencies = [("<new_label>", ...)]`

Files that MUST NOT be edited during this migration:

- Anything under `finlo_crm/` — out of scope.
- `finlo/contrib/process/approvals/migrations/` and `.../reviews/migrations/` contents — these labels are unchanged.
