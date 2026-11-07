# Finlo CRM v2 — Isolated Staging Deployment & Concurrency Plan

This document establishes the architecture, deployment specifications, database isolation protocols, monitoring procedures, and execution criteria for the **Finlo CRM v2 Staging Environment**.

---

## 1. Staging Deployment Architecture

Finlo CRM v2 requires four primary service components to faithfully reproduce production behavior under concurrency:

```
                          [ Client Traffic (Locust) ]
                                      │
                                      ▼
                        [ Reverse Proxy / Nginx ]
                       (SSL Termination / WS Routing)
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
    [ HTTP / HTMX Requests ]                       [ WebSocket Handshakes ]
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      ▼
                      [ Daphne ASGI Application Server ]
                       (finlo.asgi:application :8000)
                                      │
             ┌────────────────────────┼────────────────────────┐
             ▼                        ▼                        ▼
    [ Redis Channel Layer ]   [ Redis Celery Broker ]   [ Staging PostgreSQL ]
         (db 1 :6379)              (db 0 :6379)         (aws-0-REGION.pooler...)
                                      │                     │ Port 6543 / 5432
                                      ▼                     │
                            [ Celery Worker Pool ]          │
                            (finlo worker -c 4) ────────────┘
```

### 1.1 Minimum Required Services
1. **ASGI Application Server (Daphne)**:
   - Command: `daphne -b 0.0.0.0 -p 8000 finlo.asgi:application`
   - Handles HTTP/1.1, HTMX partial swaps, and WebSocket connections (`ws/notifications/`, `ws/calls/`).
2. **Background Worker (Celery)**:
   - Command: `celery -A finlo worker -l info -c 4`
   - Executes asynchronous tasks (lead scoring, workflow automation, audit logging).
3. **In-Memory Store (Redis)**:
   - DB 0: Celery message broker and result backend.
   - DB 1: Django Channels layer (`channels_redis.core.RedisChannelLayer`).
4. **Database Tier (Supabase PostgreSQL)**:
   - Separate, dedicated staging project reference (never Mumbai `ordzcyrzqhdsavfkkouz` or Tokyo backup).

---

## 2. Infrastructure & Resource Sizing

| Component | 10-User Smoke Test | 100-User Baseline | 1,000-User Enterprise Test |
|---|:---:|:---:|:---:|
| **Daphne ASGI** | 1 process (1 vCPU, 1 GB RAM) | 2 workers (2 vCPU, 2 GB RAM) | 4–8 workers behind Nginx (4–8 vCPU, 8 GB RAM) |
| **Celery Workers** | 1 worker (`-c 2`) | 2 workers (`-c 4`) | 4 workers (`-c 8`, 4 vCPU, 4 GB RAM) |
| **Redis** | 256 MB RAM | 512 MB RAM | 2 GB RAM (persistent channel traffic) |
| **PostgreSQL / Pooler** | Session Pooler (5432) or Transaction Pooler (6543) | Transaction Pooler (6543), pool size 25 | Transaction Pooler (6543), pool size 50–100 |
| **Estimated Compute Cost** | Staging Free / Dev Tier | Small VM / Container ($10–20/mo) | Dedicated staging node / cluster ($40–80/mo) |

---

## 3. Environment Variable Checklist

All staging settings are configured in `.env.staging` (derived from [`.env.staging.template`](file:///c:/Users/izhar/Desktop/crm-v2/.env.staging.template)):

| Variable | Staging Setting | Purpose & Safety Enforcement |
|---|---|---|
| `FINLO_TARGET_ENV` | `staging` | **Mandatory gate**: Framework and migration scripts abort if not set to `staging`. |
| `DEBUG` | `0` | Disables verbose tracebacks; matches production performance. |
| `SECRET_KEY` | *(Random 50+ chars)* | Isolated staging secret; never matches production. |
| `ALLOWED_HOSTS` | `staging-crm.example.com` | Restricts traffic to the designated staging hostname. |
| `CSRF_TRUSTED_ORIGINS`| `https://staging-crm.example.com` | Enforces CSRF validation on all incoming forms/HTMX requests. |
| `STAGING_PROJECT_REF` | *e.g. `xyzstagingprojectref`* | Verified by pre-flight check before any database connection. |
| `DATABASE_URL` | `postgresql://postgres.REF:PASS@aws-0-REGION.pooler.supabase.com:6543/postgres?sslmode=require` | Points exclusively to staging Supabase. |
| `DB_CONN_MAX_AGE` | `0` | Immediately releases pooler client slots after each request. |
| `DISABLE_SERVER_SIDE_CURSORS` | `True` | Required for Supabase Transaction Pooler (Port 6543) compatibility. |
| `EMAIL_BACKEND` | `django.core.mail.backends.dummy.EmailBackend` | **Safety**: Completely suppresses real outbound emails. |
| `TWILIO_ACCOUNT_SID` | `AC00000000000000000000000000000000` | Dummy test credentials; prevents outbound phone calls/SMS. |
| `DISABLE_EXTERNAL_WEBHOOKS` | `True` | Suppresses outgoing HTTP webhook dispatches. |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Dedicated staging Redis instance for Celery. |
| `CHANNEL_REDIS_URL` | `redis://127.0.0.1:6379/1` | Dedicated staging Redis DB for Channels WebSockets. |
| `FINLO_STAGING_USER_PASSWORD` | `FinloStagingPass123!` | Standard password for seeded test accounts. |

---

## 4. Database Connection Pooling Options (Supabase)

Supabase offers three connection paths for PostgreSQL. Analysis for Django/ASGI:

### Option A: Transaction Pooler (Port 6543 via Supavisor) — **Recommended for 1,000 Users**
- **How it works**: Client connections borrow a physical database connection only while an active SQL transaction executes, returning it immediately to the pool.
- **Benefits**: 1,000 concurrent virtual users can easily multiplex over 25–50 physical PostgreSQL connections without exhausting backend process limits.
- **Constraints**:
  - `DISABLE_SERVER_SIDE_CURSORS=True` is **mandatory** (named server cursors do not survive transaction boundaries).
  - `DB_CONN_MAX_AGE=0` is recommended to avoid holding idle pooler connections.
  - Session-level SQL commands (`LISTEN/NOTIFY`, `SET timezone`) are not persistent across transactions.

### Option B: Session Pooler (Port 5432 via Supavisor) — **Acceptable for 10–50 Users**
- **How it works**: Maintains a 1:1 mapped connection from the client for the duration of the TCP session.
- **Benefits**: Full PostgreSQL feature support (named cursors, session variables).
- **Constraints**:
  - Pool capacity is capped by the Supabase project tier (typically 15–30 client slots on micro/small).
  - Under 1,000 users, new requests will queue or be rejected with client connection timeouts.

### Option C: Direct Connection (IPv6 / Port 5432 directly to PostgreSQL)
- **Constraint**: Bypasses the pooler and is strictly limited by PostgreSQL `max_connections` (60–100 slots). **Unusable for 1,000 users.**

---

## 5. Database Isolation & Verification Procedure

Before running migrations, data seeding, or load tests, operators **must** run the automated isolation gate:

```bash
python scripts/verify_db_isolation.py --project-ref <your-staging-ref>
```

### Verification Checks:
1. **Forbidden ID Match**: Aborts immediately if the host or username matches Mumbai dev (`ordzcyrzqhdsavfkkouz`) or Tokyo backups.
2. **Ref Consistency**: Confirms the username's Supabase project reference prefix matches `STAGING_PROJECT_REF`.
3. **Target Environment Flag**: Ensures `FINLO_TARGET_ENV=staging` is exported.
4. **Read-Only Metadata Probe**: Connects to the database and prints live database name, user, SSL status, and table count.

---

## 6. Deployment, Initialization & Rollback Instructions

### Step 1: Copy Staging Config
```bash
cp .env.staging.template .env.staging
# Edit .env.staging with your staging credentials
export $(cat .env.staging | xargs)
```

### Step 2: Initialize Database (Migrations + User Seeding)
```bash
python scripts/init_staging_db.py --confirm --user-count 250
```
*Output: Schema migrated, 250 test users seeded, credentials written to `load_tests/data/test_users.csv`.*

### Step 3: Start Staging Services
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
celery -A finlo worker -l info -c 4

# Terminal 3: Start Daphne ASGI Server
daphne -b 0.0.0.0 -p 8000 finlo.asgi:application
```

### Step 4: Post-Test Rollback & Data Purge
```bash
# Preview records to delete (dry run)
python load_tests/cleanup.py --dry-run

# Execute atomic deletion
python load_tests/cleanup.py --confirm
```

---

## 7. Monitoring & Telemetry Plan

Run the staging telemetry monitor during load tests:
```bash
python load_tests/monitoring/telemetry_collector.py --interval 5 --output reports/telemetry_smoke.csv
```

### Telemetry Tracked:
1. **Host Resources**: CPU % utilization, memory used (MB).
2. **Database Pressure**: Active connections, idle in transaction, slow queries (> 2s) from `pg_stat_activity`.
3. **Redis & Celery**: Connected clients, Redis memory, and Celery queue backlog (`llen celery`).

---

## 8. First 10-User Smoke Test & Acceptance Criteria

### Execution Command:
```bash
locust -f load_tests/locustfile.py --headless \
  --users 10 --spawn-rate 2 --run-time 3m \
  --host https://staging-crm.example.com \
  --html reports/smoke_10users.html \
  --csv reports/smoke_10users
```

### Acceptance Criteria:
1. **Zero HTTP Failures**: 100% success rate across all requests (HTTP 200, 201, 302).
2. **Zero Login Lockouts**: 0 responses with HTTP 429 or lockout messages.
3. **Latency Thresholds**:
   - HTMX partials: p95 < **1,500 ms**
   - Full page shell loads: p95 < **3,000 ms**
   - WebSocket connect handshake: p95 < **500 ms**
4. **All 5 Personas Active**: `SalesRepUser`, `SalesManagerUser`, `DataEntryUser`, `BrowserUser`, and `NotificationWebSocketUser` each record successful transactions.
5. **Clean Rollback**: Running `python load_tests/cleanup.py --confirm` successfully purges all created `LOADTEST_` records.

