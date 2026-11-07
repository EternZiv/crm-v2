# Finlo CRM v2 — 1,000-User Enterprise Load Testing Framework

A modular, production-ready Locust-based load testing framework for **Finlo CRM v2**, engineered to simulate up to **1,000 concurrent virtual users** across multi-tenant companies and sales hierarchy roles (`SUPER_ADMIN`, `HEAD_OF_SALES`, `RSM`, `SSM`, `ASM`, `BDO`).

---

## 1. Architecture Assessment

### 1.1 Authentication & Session Handling
- **Login Flow**: Real browser-like authentication through `GET /login/` (extracting `csrftoken` cookie and hidden form input), followed by `POST /login/` with `username`, `password`, `csrfmiddlewaretoken`, and `next`.
- **Session Lifecycle**: Authentication succeeds with HTTP 302 redirect and an authenticated `sessionid` cookie containing `_auth_user_id`, `_auth_user_backend`, and `active_company_id`.
- **Lockout Mechanism**: Django cache tracks failed login attempts by IP. Exceeding 5 failed attempts locks out the IP for 15 minutes (`login_lockout_{ip}`). The framework uses valid test credential leasing to avoid lockout contention.
- **RBAC Compliance**: Does not bypass Django permissions or manufacture session cookies.

### 1.2 HTMX Request Patterns & Headers
Finlo CRM relies heavily on HTMX for partial view rendering and interactive components:
- Full shell views (`/dashboard/?section=home`, `/crm/leads/leads-view/?section=sales`) load base navigation, stylesheets, and scripts.
- In-app transitions and tables execute partial GET/POST requests returning HTML fragments (`#mainContent`, `#subSidebar`, table rows).
- The framework sends explicit HTMX headers:
  ```http
  HX-Request: true
  HX-Target: #mainContent
  HX-Current-URL: /crm/leads/leads-view/?section=sales
  X-CSRFToken: <token>
  X-Requested-With: XMLHttpRequest
  ```

### 1.3 Core CRM Endpoints Covered
- **Dashboard**:
  - Full Shell: `GET /dashboard/?section=home`
  - HTMX Partial: `GET /dashboard/?section=home` (`HX-Request: true`)
- **Leads**:
  - Full Shell: `GET /crm/leads/leads-view/?section=sales`
  - HTMX List Partial: `GET /crm/leads/leads-list/`
  - Search/Filter Partial: `GET /crm/leads/leads-list/?search=<query>`
  - Analytics Chart: `GET /crm/leads/leads-chart/`
  - Record Detail: `GET /crm/leads/leads-detail/<id>/`
  - Safe Creation: `POST /crm/leads/leads-create-single/`
- **Accounts**:
  - Full Shell: `GET /crm/accounts/accounts-view/?section=people`
  - HTMX List Partial: `GET /crm/accounts/accounts-list-view/`
  - Record Detail: `GET /crm/accounts/account-detail-view/<id>/`
  - Safe Creation: `POST /crm/accounts/account-single-create-form-view/`
- **Contacts**:
  - Full Shell: `GET /crm/contacts/contacts-view/?section=people`
  - HTMX List Partial: `GET /crm/contacts/contact-list-view/`
  - Record Detail: `GET /crm/contacts/contact-detail-view/<id>/`
  - Safe Creation: `POST /crm/contacts/contact-single-create-form/`
- **Opportunities**:
  - Full Shell: `GET /crm/opportunities/opportunities-view/?section=sales`
  - HTMX List Partial: `GET /crm/opportunities/opportunities-list/`
  - Pipeline Chart: `GET /crm/opportunities/opportunities-chart/`
  - Record Detail: `GET /crm/opportunities/opportunity-detail/<id>/`
  - Safe Creation: `POST /crm/opportunities/opportunity-create-single/`
- **Activities & Tasks**:
  - Full Shell: `GET /activity/activity-view/?section=activity`
  - Global Tasks: `GET /activity/global-task-list/`
  - Task Creation: `POST /activity/task-create-form/`

### 1.4 Multi-Tenancy & Sales Hierarchy
- Multi-company isolation is enforced at the database and query level via `request.active_company` (`Company` foreign key on models).
- Sales hierarchy roles (`SUPER_ADMIN` > `HEAD_OF_SALES` > `RSM` > `SSM` > `ASM` > `BDO`) restrict visibility:
  - BDOs only view their assigned records.
  - ASMs view records within their area.
  - RSMs view regional company branches.
  - Head of Sales & Super Admin view company-wide metrics.

### 1.5 Celery, Redis & Channels (WebSockets)
- **Celery**: Processes asynchronous workflows (lead scoring, audit logs, notification dispatches).
- **Redis**: Backend for Celery broker and Django Channels layer.
- **WebSockets**: Mounted at `ws/notifications/` and `ws/calls/` using ASGI/Daphne.

### 1.6 Database Connection Limits & Staging Requirements
- Staging PostgreSQL must use transaction pooling (e.g., Supavisor port `6543` or PgBouncer).
- Direct connections (port `5432`) will exhaust database process slots under 1,000 concurrent web requests.
- `DB_CONN_MAX_AGE` should be configured based on Daphne worker count.

---

## 2. Staging Environment Setup Instructions

### 2.1 Staging Infrastructure Sizing (1,000 Users)
- **Application Tier (Daphne ASGI)**: 4 to 8 CPU cores, 8 GB RAM (or 2-4 container instances behind load balancer).
- **Worker Tier (Celery)**: 4 worker processes with concurrency 8.
- **Database Tier (PostgreSQL)**: Minimum 4 vCPU, 8 GB RAM with connection pooling enabled (pool size 50-100).
- **Redis**: 2 GB RAM (for channel layer and Celery queue).

### 2.2 Staging Configuration Safeguards
In the staging `.env`:
```ini
# Staging database (NEVER point to production or local development)
DATABASE_URL=postgres://user:pass@staging-pooler.example.com:6543/finlo_staging?sslmode=require

# Suppress outbound notifications & emails
EMAIL_BACKEND=django.core.mail.backends.dummy.EmailBackend
CELERY_BROKER_URL=redis://staging-redis.example.com:6379/0
CHANNEL_REDIS_URL=redis://staging-redis.example.com:6379/1

# Staging Environment Identification
FINLO_TARGET_ENV=staging
```

### 2.3 OS Kernel Tuning on Load Injectors
When generating 1,000 concurrent connections from a Linux load generator:
```bash
# Increase file descriptor limit
ulimit -n 65535

# Expand ephemeral port range
sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535"
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
```

---

## 3. Synthetic Test Users & Data Requirements

### 3.1 Seeding Staging Test Users
To test realistic RBAC without session lock contention, seed 200–500 distinct test users across multiple companies:
```bash
python load_tests/seed_staging_users.py --count 250 --output load_tests/data/test_users.csv
```
This provisions:
- 3 Companies (`Staging HQ`, `Staging Branch East`, `Staging Branch West`).
- 6 Hierarchy roles (60% BDO, 15% ASM, 10% SSM, 10% RSM, 4% Head of Sales, 1% Super Admin).
- Generates `load_tests/data/test_users.csv`.

### 3.2 Synthetic Data Tagging
All test-created records strictly use the prefix:
```text
LOADTEST_
```
Examples:
- Account: `LOADTEST_Account_a1b2c3d4`
- Lead: `LOADTEST_Lead Prospect_a1b2c3d4`, company `LOADTEST_Enterprise_a1b2c3d4`
- Contact: `LOADTEST_Contact User_a1b2c3d4`
- Opportunity: `LOADTEST_Deal_a1b2c3d4`
- Task: `LOADTEST_Task_a1b2c3d4`

---

## 4. Configuration Profiles

| Profile | Users | Spawn Rate | Duration | Think Time | Mode | Purpose |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **10** | 10 | 2/s | 3m | 2–5s | Single | Baseline smoke test |
| **50** | 50 | 5/s | 5m | 2–6s | Single | Light business concurrency |
| **100** | 100 | 10/s | 10m | 2–7s | Single | Standard daytime business load |
| **250** | 250 | 20/s | 15m | 2–8s | Distributed (2 workers) | Peak business hour traffic |
| **500** | 500 | 25/s | 20m | 2–8s | Distributed (4 workers) | High stress & burst load |
| **1,000** | 1,000 | 50/s | 30m | 2–10s | Distributed (8 workers) | Enterprise maximum capacity |

---

## 5. Safe Execution Instructions

### 5.1 Environment Safety Guard
The framework strictly validates `--host` against disallowed patterns (`localhost`, `127.0.0.1`, `*.production.com`, `finlo.com`).
Execution against production or development will immediately halt with `SafetyError`.

To confirm the staging target, set:
```bash
export FINLO_TARGET_ENV=staging
```

### 5.2 Single-Host Execution Commands

#### 10-User Smoke Test:
```bash
locust -f load_tests/locustfile.py --headless \
  --users 10 --spawn-rate 2 --run-time 3m \
  --host https://staging-crm.example.com \
  --html reports/report_10users.html --csv reports/report_10users
```

#### 50-User Baseline Test:
```bash
locust -f load_tests/locustfile.py --headless \
  --users 50 --spawn-rate 5 --run-time 5m \
  --host https://staging-crm.example.com \
  --html reports/report_50users.html --csv reports/report_50users
```

#### 100-User Test:
```bash
locust -f load_tests/locustfile.py --headless \
  --users 100 --spawn-rate 10 --run-time 10m \
  --host https://staging-crm.example.com \
  --html reports/report_100users.html --csv reports/report_100users
```

---

### 5.3 Distributed Load Generation (500 to 1,000 Users)

When testing 1,000 concurrent users, run Locust in distributed mode across multiple worker processes or machines.

#### Step 1: Start Locust Master (Terminal 1)
```bash
locust -f load_tests/locustfile.py --master \
  --expect-workers 8 --headless \
  --users 1000 --spawn-rate 50 --run-time 30m \
  --host https://staging-crm.example.com \
  --html reports/report_1000users.html --csv reports/report_1000users
```

#### Step 2: Start 8 Locust Workers (Terminal 2 or distributed machines)
```bash
# Start 8 workers on the master machine or across a cluster
for i in {1..8}; do
  locust -f load_tests/locustfile.py --worker --master-host=127.0.0.1 &
done
```

---

## 6. CSV & HTML Reporting Support

Locust automatically records and exports detailed metric distributions:
- **HTML Report** (`reports/report_1000users.html`):
  - Graphical response time over time
  - Requests per second (RPS) timeline
  - Error rate percentage timeline
  - Virtual user count ramp curve
- **CSV Datasets**:
  - `_stats.csv`: p50, p90, p95, p99, min, max, avg response times per endpoint.
  - `_failures.csv`: Detailed failure messages and status codes.
  - `_stats_history.csv`: Time-series log of throughput and latency.

---

## 7. Metrics & Observability Checklist

During staging load tests, monitor:
1. **Application Throughput & Latency**:
   - Total RPS and error rate (< 0.5% target).
   - p95 response time (< 1,500 ms target for HTMX partials; < 3,000 ms for full shell).
   - Rate limit / lockout count (`login_lockout_{ip}`).
2. **Server Resources (Daphne / Django)**:
   - CPU utilization (< 75% per core).
   - RSS memory (detect potential memory leaks).
   - Active thread count and open file descriptors.
3. **Database Tier (PostgreSQL / Supavisor)**:
   - Active client connections vs. pool max limit.
   - Transaction pool waiting time.
   - Slow query log (`SELECT * FROM pg_stat_activity WHERE state != 'idle'`).
4. **Asynchronous Queues (Redis / Celery)**:
   - Redis memory and connected clients.
   - Celery queue depth (`celery -A finlo inspect active`).
5. **WebSocket Connections (Django Channels)**:
   - Number of persistent WebSocket sessions on `ws/notifications/`.

---

## 8. Cleanup & Rollback Procedure

After load tests finish, run the cleanup script to remove all synthetic records:

### Preview Count (Dry Run):
```bash
python load_tests/cleanup.py --dry-run
```

### Execute Purge:
```bash
python load_tests/cleanup.py --confirm
```

Output:
```text
============================================================
FINLO CRM — SYNTHETIC LOAD TEST DATA CLEANUP
Target Prefix: 'LOADTEST_'
Dry Run Mode: False
============================================================
  Found 142    synthetic Leads
  Found 88     synthetic Opportunities
  Found 95     synthetic Contacts
  Found 110    synthetic Accounts
  Found 85     synthetic Tasks / Activities
------------------------------------------------------------
[SUCCESS] Successfully purged synthetic load test records:
  - Leads deleted: 142
  - Opportunities deleted: 88
  - Contacts deleted: 95
  - Accounts deleted: 110
  - Tasks deleted: 85
============================================================
```

---

## 9. Known Limitations

1. **Single-IP Egress & Rate Limiting**:
   - Running 1,000 concurrent virtual users from a single client machine / IP will send thousands of requests from the same IP address. If users fail login or test credentials are misconfigured, Finlo's IP brute-force protection (`login_lockout_{ip}`) will lock out the IP. Ensure staging user credentials are valid and pre-seeded.
2. **PostgreSQL Direct Connection Saturation**:
   - PostgreSQL requires an external connection pooler (e.g. Supavisor / PgBouncer in transaction mode). Direct connections (`port 5432`) without connection pooling will quickly trigger `FATAL: remaining connection slots are reserved for non-replication superuser connections`.
3. **Daphne Event Loop Blocking**:
   - Heavy synchronous Django database queries inside ASGI async workers run via threadpool. Under 1,000 users, ensure adequate Daphne worker instances are spawned.
4. **Local Ephemeral Port Exhaustion**:
   - A single client machine opening 1,000 rapid HTTP connections can exhaust ephemeral TCP sockets (TIME_WAIT). Distributed Locust workers or `net.ipv4.tcp_tw_reuse = 1` must be applied.

