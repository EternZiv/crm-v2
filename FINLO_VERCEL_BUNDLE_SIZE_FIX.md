# FINLONEXA CRM v2 — Vercel Bundle Size Optimization Report

## Executive Summary

- **Incident**: Vercel deployment of commit `f4a30435` failed with `[LAMBDA_SIZE_EXCEEDED]: Total bundle size: 500.91 MB / Maximum allowed: 500 MB` (exceeded by 0.91 MB).
- **Target**: Reduce Vercel Python function bundle to strictly below 500 MB (preferably below 450 MB) without breaking FINLO CRM functionality, permissions, or Supabase connection pooling.
- **Outcome**: **ACHIEVED**
  - **Total Estimated Bundle Reduction**: **94.22 MB**
  - **New Estimated Bundle Size**: **406.69 MB** (well below the 450 MB target)
  - **Headroom Under 500 MB Hard Limit**: **93.31 MB**
  - **Headroom Under 450 MB Target**: **43.31 MB**
  - **CRM Health & System Check**: **PASS (0 errors, 0 warnings)**

---

## 1. Largest Bundle Contributors

The root cause of `LAMBDA_SIZE_EXCEEDED` was the co-packaging of unoptimized repository assets with installed Python packages into the serverless function filesystem (`/var/task`):

### A. Python Site-Packages (380.55 MB)
All top packages are actively imported by models, views, or core dependencies:
- `numpy`: 41.03 MB
- `django-countries`: 37.17 MB
- `pandas`: 36.60 MB
- `babel`: 29.50 MB (required by `django-money` / `py-moneyed`)
- `Django`: 22.52 MB
- `botocore`: 21.36 MB (required by `boto3` / `django-storages`)
- `phonenumbers`: 20.88 MB
- `pycountry`: 15.83 MB
- `pywin32`: 14.51 MB (local dev environment only; omitted by Vercel Linux build)
- `drf-yasg`: 14.03 MB
- `pillow`: 14.00 MB
- `Twisted`: 12.69 MB (required by Daphne/Channels)
- `cryptography`: 9.14 MB
- `psycopg-binary`: 6.98 MB (Psycopg 3 driver)
- `psycopg2-binary`: 6.59 MB (*Legacy, redundant*)

### B. Repository Files (131.96 MB originally)
- **JSON Fixtures / Seed Data (`**/load_data/*.json`)**: **65.75 MB** (34 files: `account.json` 23.83 MB, `contact.json` 14.83 MB, `leads.json` 14.09 MB, `campaign.json` 10.73 MB, `users.json` 1.23 MB, `opportunity.json` 0.90 MB, etc.). These files are only used for local manual seed commands and are forbidden in production.
- **Unused Vendored FontAwesome Distribution Folders**: **17.51 MB**
  - `static/assets/fontawesome/metadata/`: 10.48 MB (YAML/JSON icon metadata)
  - `static/assets/fontawesome/js/`: 5.58 MB (unused JS kits; templates use CSS)
  - `static/assets/fontawesome/sprites/`: 1.45 MB (unused SVG sprites)
- **Duplicate Vector File**: `finlo-svg.svg` in root: **1.03 MB** (100% duplicate of `static/icon.svg`).
- **Benchmark / Diagnostic JSONs**: `FINLO_*.json` in root: **1.11 MB**.
- **Documentation & Reports (`docs/`, `*.md`)**: **2.18 MB**.
- **Test Suites (`tests/`, `**/tests/**`)**: **0.15 MB**.

---

## 2. Files Changed

### A. Repository Removals (19.70 MB permanently saved)
Staged deletions of unreferenced and duplicate files:
1. `static/assets/fontawesome/metadata/` (deleted)
2. `static/assets/fontawesome/sprites/` (deleted)
3. `static/assets/fontawesome/js/` (deleted)
   *(Note: Active FontAwesome CSS `all.min.css` and webfonts in `webfonts/` remain 100% intact)*
4. `finlo-svg.svg` (duplicate of `static/icon.svg`, deleted)
5. `FINLO_READONLY_PAGE_RESULTS.json`, `FINLO_PAGE_ROUTE_INVENTORY.json`, `FINLO_INLINE_SCRIPT_RESULTS.json`, `FINLO_TEMPLATE_PARSE_RESULTS.json` (deleted)
6. Diagnostic and test error logs (`*.err`, `*.out`, deleted)

### B. `vercel.json` (Created)
Configured function exclusion rules matching all actual Vercel Python entry points:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "finlo/asgi.py": {
      "excludeFiles": "{**/load_data/**,**/tests/**,docs/**,*.md,windows-installer/**,debian/**,scratch/**,static/assets/fontawesome/metadata/**,static/assets/fontawesome/sprites/**,static/assets/fontawesome/js/**,FINLO_*.json,*.log,*.err,*.out}"
    },
    "finlo/wsgi.py": {
      "excludeFiles": "{**/load_data/**,**/tests/**,docs/**,*.md,windows-installer/**,debian/**,scratch/**,static/assets/fontawesome/metadata/**,static/assets/fontawesome/sprites/**,static/assets/fontawesome/js/**,FINLO_*.json,*.log,*.err,*.out}"
    },
    "manage.py": {
      "excludeFiles": "{**/load_data/**,**/tests/**,docs/**,*.md,windows-installer/**,debian/**,scratch/**,static/assets/fontawesome/metadata/**,static/assets/fontawesome/sprites/**,static/assets/fontawesome/js/**,FINLO_*.json,*.log,*.err,*.out}"
    }
  }
}
```

### C. `.vercelignore` (Updated)
Added exclusion patterns to prevent Vercel CLI/Git upload of test files, docs, demo seed data, scratch scripts, and logs:
- `**/load_data/*.json`
- `tests/`, `**/tests/`, `test_*.py`, `*_test.py`
- `docs/`, `scratch/`, `*.md` (`!README.md`)
- `windows-installer/`, `debian/`, `.pytest_cache/`
- `*.log`, `*.err`, `*.out`, `page_*.py`, `build_*.py`, `FINLO_*.json`

### D. `requirements.txt` (Optimized)
- Removed redundant legacy driver: `psycopg2-binary==2.9.12` (saves 6.59 MB on Vercel install).
- Preserved modern active driver and pooling stack:
  - `psycopg==3.3.9`
  - `psycopg-binary==3.3.9`
  - `psycopg-pool==3.3.3`

### E. `VERCEL-DEPLOYMENT.md` (Updated)
Updated documentation regarding `vercel.json` to reflect that `excludeFiles` configuration is enabled to enforce the AWS Lambda 500 MB limit while maintaining default framework detection.

---

## 3. Estimated Savings & Headroom

| Category | Optimization Mechanism | Savings |
| :--- | :--- | :--- |
| **Deleted Repo Files** | Git rm of unused FA metadata/sprites/js, duplicate svg, logs | **19.70 MB** |
| **JSON Fixtures** | Excluded `**/load_data/*.json` from function bundle | **65.75 MB** |
| **Documentation & Tests** | Excluded `docs/`, `tests/`, markdown reports, scratch | **2.18 MB** |
| **Redundant Python Driver** | Removed `psycopg2-binary` (Psycopg 3 remains intact) | **6.59 MB** |
| **TOTAL BUNDLE SAVINGS** | Combined repository, function packaging, & pip savings | **94.22 MB** |

### Projected Bundle Comparison
- **Original Vercel Bundle**: `500.91 MB`
- **New Projected Bundle**: **`406.69 MB`**
- **Margin Below 500 MB Limit**: **`93.31 MB`**
- **Margin Below 450 MB Target**: **`43.31 MB`**

---

## 4. Validation Results

| Test / Check | Command / Operation | Result | Details |
| :--- | :--- | :--- | :--- |
| **Django System Check** | `python manage.py check` | **PASS** | 0 issues identified (0 silenced) |
| **Static Asset Resolution** | `python manage.py collectstatic --dry-run --noinput` | **PASS** | 2,646 unmodified files verified, 0 missing assets |
| **ASGI Entry Point** | `import finlo.asgi:application` | **PASS** | ProtocolTypeRouter resolved and initialized |
| **WSGI Entry Point** | `import finlo.wsgi:application` | **PASS** | WSGIHandler resolved and initialized |
| **PostgreSQL Driver** | `psycopg` (v3) connection test | **PASS** | Django initializes Supabase connection via Psycopg 3 without psycopg2 |
| **Core Models Loading** | Import `FinloUser`, `Company`, `Role`, `Lead`, `Campaign`, `Account`, `Contact`, `Opportunity` | **PASS** | All core CRM models imported with valid schemas |
| **Template Engine** | `get_template()` on core layouts & templates | **PASS** | `login.html`, `index.html`, `sidebar.html`, `header.html`, `htmx_layout.html`, `modelcontent_layout.html`, `403/404/500.html` |
| **URL Registry** | URL reversal & resolver check | **PASS** | 228 named routes loaded cleanly |

---

## 5. Remaining Deployment Risks

1. **Serverless Execution Duration**:
   - Vercel functions have timeout limits (15s on Hobby, up to 300s on Pro).
   - *Mitigation*: The application's Phase 3B navigation optimizations and Phase 4B SQL query optimizations have reduced click-to-usable latency to < 1.0s across all core routes.
2. **PostgreSQL Connection Pool Sizing**:
   - Horizontal scaling of serverless functions can spawn multiple short-lived containers.
   - *Mitigation*: `finlo/settings/vercel.py` sets `CONN_MAX_AGE = 0` and connects through Supabase's transaction pooler (port `6543`) with `DISABLE_SERVER_SIDE_CURSORS = True`.
3. **Ephemeral Media Storage**:
   - Local `/media` filesystem storage is not persistent across serverless container restarts.
   - *Mitigation*: Production deployments must configure `FINLO_MEDIA_STORAGE_BACKEND` (e.g. S3 / Supabase Storage via `boto3` / `django-storages`, which are retained in `requirements.txt`).
4. **Channels / WebSocket Support**:
   - In Vercel serverless environments, stateful WebSockets require external Redis (`rediss://`) or running in `VERCEL_UAT_MODE=1` (in-memory channel layer for HTTP-first UAT evaluation).

---

## 6. Recommended Deployment Steps

1. **Review Local Changes**:
   ```bash
   git status
   git diff requirements.txt .vercelignore vercel.json VERCEL-DEPLOYMENT.md
   ```
2. **Stage and Commit**:
   ```bash
   git add requirements.txt .vercelignore vercel.json VERCEL-DEPLOYMENT.md
   git commit -m "fix(vercel): resolve LAMBDA_SIZE_EXCEEDED by excluding fixtures and removing redundant assets"
   ```
3. **Push to GitHub**:
   ```bash
   git push origin main
   ```
4. **Monitor Vercel Build**:
   - Verify the deployment log in the Vercel Dashboard under `EternZiv/crm-v2`.
   - Confirm the function bundle size is reported at ~406 MB.
   - Confirm successful build and green deployment status.

