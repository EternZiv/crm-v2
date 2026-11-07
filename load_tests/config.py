"""
Configuration and Safety Policies for Finlo CRM v2 Load Testing Framework.
"""

import os
import re
import sys
from urllib.parse import urlparse

# =============================================================================
# ENVIRONMENT & SAFETY CONFIGURATION
# =============================================================================

LOCAL_READONLY_PROFILE = "local-readonly"

DISALLOWED_HOST_PATTERNS = [
    r"^localhost(:\d+)?$",
    r"^127\.0\.0\.1(:\d+)?$",
    r"^0\.0\.0\.0(:\d+)?$",
    r"^::1$",
    r"^.*\.production\.com$",
    r"^app\.finlo\.com$",
    r"^crm\.finlo\.com$",
    r"^finlo\.com$",
]

ALLOWED_STAGING_KEYWORDS = [
    "staging",
    "stg",
    "uat",
    "loadtest",
    "perf",
    "benchmark",
]


class SafetyError(Exception):
    """Raised when an unsafe target host or configuration is detected."""
    pass


def get_database_project_info():
    """
    Safely inspects the configured DATABASE_URL from environment or .env
    without exposing raw passwords or sensitive credentials.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url and os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        db_url = line.split("=", 1)[1].strip("'\"")
                        break
        except Exception:
            pass

    if not db_url:
        return {
            "configured": False,
            "host": "unknown",
            "project_id": "unknown",
            "region": "unknown",
            "is_mumbai": False,
        }

    parsed = urlparse(db_url)
    username = parsed.username or ""
    hostname = parsed.hostname or ""

    # Supabase connection format: postgres.<project_ref>@<host>
    project_ref = "unknown"
    if username.startswith("postgres."):
        project_ref = username.split(".", 1)[1]
    elif "supabase" in hostname:
        project_ref = hostname.split(".")[0]

    is_mumbai = "ap-south-1" in hostname or "ordzcyrzqhdsavfkkouz" in project_ref

    return {
        "configured": True,
        "host": hostname,
        "project_id": project_ref,
        "region": "ap-south-1 (Mumbai)" if is_mumbai else "other",
        "port": parsed.port or 5432,
        "is_mumbai": is_mumbai,
    }


def validate_target_host(host: str, allow_local_override: bool = False, profile: str = ""):
    """
    Enforces strict environment boundaries.
    Refuses to run against localhost development or production by default.
    Allows local testing only when explicit FINLO_ALLOW_LOCAL_LOADTEST=1 AND
    FINLO_LOCAL_READONLY=1 are set, confirming read-only execution.
    """
    if not host:
        raise SafetyError("Target host is required. Specify via --host or TARGET_URL.")

    parsed = urlparse(host)
    hostname = parsed.netloc or parsed.path
    hostname_clean = hostname.split("@")[-1].lower()

    # 1. Check local execution
    is_local = any(
        re.match(p, hostname_clean)
        for p in [r"^localhost(:\d+)?$", r"^127\.0\.0\.1(:\d+)?$", r"^0\.0\.0\.0(:\d+)?$", r"^::1$"]
    )

    if is_local:
        allow_local = allow_local_override or os.environ.get("FINLO_ALLOW_LOCAL_LOADTEST", "0") == "1"
        is_readonly = os.environ.get("FINLO_LOCAL_READONLY", "0") == "1" or profile == LOCAL_READONLY_PROFILE

        if not allow_local:
            raise SafetyError(
                f"[SAFETY VIOLATION] Target host '{hostname_clean}' is a local environment. "
                "Load testing against localhost development is blocked by default to protect development data. "
                "To explicitly authorize a local read-only load test against Mumbai, set FINLO_ALLOW_LOCAL_LOADTEST=1."
            )

        if not is_readonly:
            raise SafetyError(
                f"[SAFETY VIOLATION] Target host '{hostname_clean}' is running against Mumbai database. "
                "Local testing strictly requires FINLO_LOCAL_READONLY=1 or --profile local-readonly. "
                "Write operations, synthetic provisioning, and cleanup are forbidden against Mumbai."
            )

        db_info = get_database_project_info()
        print(f"[SAFETY VALIDATED] Localhost execution authorized for host: {hostname_clean}", file=sys.stderr)
        print(f"[DATABASE IDENTIFIED] Connected database project: {db_info['project_id']} in {db_info['region']}", file=sys.stderr)
        print("[SAFETY POLICY] Mode: STRICT LOCAL READ-ONLY (No mutations permitted)", file=sys.stderr)
        return True

    # 2. Check disallowed production patterns
    for pattern in DISALLOWED_HOST_PATTERNS:
        if re.match(pattern, hostname_clean):
            raise SafetyError(
                f"[SAFETY VIOLATION] Target host '{hostname_clean}' matches disallowed pattern '{pattern}'. "
                "Load testing against production is strictly blocked. "
                "Target must be a designated staging environment (e.g. https://staging-crm.example.com)."
            )

    # 3. Check staging confirmation
    target_env = os.environ.get("FINLO_TARGET_ENV", "").lower()
    is_staging_confirmed = any(kw in hostname_clean for kw in ALLOWED_STAGING_KEYWORDS) or target_env == "staging"

    if not is_staging_confirmed:
        raise SafetyError(
            f"[SAFETY VIOLATION] Target host '{hostname_clean}' does not contain recognized staging identifiers "
            f"({ALLOWED_STAGING_KEYWORDS}) and FINLO_TARGET_ENV is not set to 'staging'. "
            "Set FINLO_TARGET_ENV=staging to confirm this is an isolated staging instance."
        )

    return True


# =============================================================================
# LOAD PROFILES
# =============================================================================

LOAD_PROFILES = {
    "1": {
        "description": "Baseline 1-user sanity check (all endpoints 200 OK)",
        "users": 1,
        "spawn_rate": 1,
        "duration": "2m",
        "min_wait": 2.0,
        "max_wait": 4.0,
        "distributed": False,
        "recommended_workers": 1,
    },
    "10": {
        "description": "Light local concurrency (10 concurrent users)",
        "users": 10,
        "spawn_rate": 2,
        "duration": "3m",
        "min_wait": 2.0,
        "max_wait": 5.0,
        "distributed": False,
        "recommended_workers": 1,
    },
    "25": {
        "description": "Moderate local load (25 concurrent users)",
        "users": 25,
        "spawn_rate": 5,
        "duration": "5m",
        "min_wait": 2.0,
        "max_wait": 5.0,
        "distributed": False,
        "recommended_workers": 1,
    },
    "50": {
        "description": "Upper single-machine ASGI + cloud DB limit (50 concurrent users)",
        "users": 50,
        "spawn_rate": 5,
        "duration": "5m",
        "min_wait": 2.0,
        "max_wait": 6.0,
        "distributed": False,
        "recommended_workers": 1,
    },
    "100": {
        "description": "Standard business hours load (100 concurrent users)",
        "users": 100,
        "spawn_rate": 10,
        "duration": "10m",
        "min_wait": 2.0,
        "max_wait": 7.0,
        "distributed": False,
        "recommended_workers": 2,
    },
    "250": {
        "description": "Peak business hours load (250 concurrent users)",
        "users": 250,
        "spawn_rate": 15,
        "duration": "10m",
        "min_wait": 2.0,
        "max_wait": 8.0,
        "distributed": False,
        "recommended_workers": 2,
    },
    "500": {
        "description": "High stress & burst load (Requires explicit approval)",
        "users": 500,
        "spawn_rate": 20,
        "duration": "15m",
        "min_wait": 2.0,
        "max_wait": 8.0,
        "distributed": True,
        "recommended_workers": 4,
    },
    "1000": {
        "description": "Enterprise scale load test (Requires explicit approval)",
        "users": 1000,
        "spawn_rate": 25,
        "duration": "20m",
        "min_wait": 2.0,
        "max_wait": 10.0,
        "distributed": True,
        "recommended_workers": 8,
    },
}

# Default synthetic prefix for all test data to ensure 100% isolation & cleanup
SYNTHETIC_DATA_PREFIX = "LOADTEST_"
