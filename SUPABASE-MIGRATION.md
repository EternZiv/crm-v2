# Use Supabase PostgreSQL with Finlo CRM

This procedure creates a **fresh Django schema** in Supabase. It deliberately
does not copy records from the existing local SQLite database.

## Current local database

The local `db.sqlite3` is present (about 5.2 MB). A metadata-only inspection
found 159 tables, 184 recorded migrations, 35 installed model apps, and 2,438
total rows. There are two local user rows and other system/audit/permission
rows; no rows were found in the main account, contact, lead, opportunity,
campaign, or forecast tables. **None of these local rows are included in this
fresh Supabase setup.** Keep `db.sqlite3` unchanged as a recovery/reference
copy. Do not run `dumpdata` or `loaddata`.

## Configure credentials privately

1. Create/select the intended Supabase project.
2. In its Dashboard, open **Connect** or **Project Settings > Database** and
   choose the direct connection if the machine supports IPv6, otherwise use
   the **Session Pooler** connection.
3. Set `DATABASE_URL` in the ignored local `.env` file. Require TLS with
   `sslmode=require`; Django settings enforce this for PostgreSQL connections.
   URL-encode special characters in the database password. Never paste the URL
   or password in chat, screenshots, logs, source files, or Git.
4. Keep `DATABASE_URL` unset/blank until the intended project is selected. The
   app uses local SQLite when no URL is set.

Example shape only (not a real credential):

```dotenv
DATABASE_URL=postgresql://DB_USER:URL_ENCODED_PASSWORD@DB_HOST:5432/postgres?sslmode=require
DB_CONN_MAX_AGE=60
DB_CONN_HEALTH_CHECKS=True
```

Share only the non-secret Supabase project reference (`PROJECT_REF`) separately
so it can be matched to the configured host. Do not send database credentials.

## Preflight and approval gate

Before any cloud writes, verify the configured host matches the intended
project reference and run a **read-only** connection check for PostgreSQL
version, database/user identity, SSL state, effective schema, existing tables,
extensions, and required privileges.

If the target schema is not empty or has an existing `django_migrations`
table, stop before migrating. Do not reset Supabase, drop or rename tables,
disable row-level security, or import any local data.

The proposed schema operation, after identity and empty-schema checks, is:

```powershell
.\.venv\Scripts\python.exe manage.py migrate --noinput
```

This applies the migration plan for all configured Django apps, including
auth, sessions, content types, Horilla core, CRM modules, and shared platform
apps. It creates tables/indexes/default migration data in the selected schema.
It does not load the SQLite database's users or business records. Do **not**
run the command until the exact target project, empty-schema preflight, and
operation have been shown and explicitly approved.

After that migration succeeds and is confirmed, create a new initial CRM
administrator with:

```powershell
.\.venv\Scripts\python.exe manage.py create_horilla_user
```

This command writes a new user to Supabase; run it only after separately
confirming the schema setup succeeded and you are ready to create that admin.
The old SQLite user/password will not work against the fresh Supabase
database.

## Configuration and operational notes

- `DATABASE_URL` selects Django's PostgreSQL backend; the installed
  `psycopg2-binary` driver is used. PostgreSQL connections require TLS.
- `DB_CONN_MAX_AGE` controls connection reuse (default 60 seconds);
  `DB_CONN_HEALTH_CHECKS` enables connection health checks.
- Local `.env` values are ignored by Git, and real environment variables take
  precedence over values in `.env`.
- Supabase PostgreSQL does not replace Redis. Celery and scheduled jobs need a
  separate reachable Redis service configured through `REDIS_URL`,
  `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`. Channels uses in-memory
  storage in single-process development; multi-process deployments must set
  `CHANNEL_REDIS_URL` to Redis 5 or newer.
- Uploaded files in `media/` are not PostgreSQL records and are not moved by
  this procedure. Configure object storage separately if needed.
- Django's permissions remain enforced by the server. Supabase Auth and RLS
  do not automatically implement Django users/roles; no policy is disabled or
  modified as part of this procedure.
- Keep the local SQLite file as-is until you have verified the new service.
  For backups/restores, use Supabase's database backup facilities and confirm
  the selected plan's recovery guarantees.
