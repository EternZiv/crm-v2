"""
Finlo CRM v2 — Staging Database Isolation & Identity Verification Script.
Ensures migrations, user seeding, and load test cleanups can NEVER touch
the Mumbai development database, Tokyo backup database, or production.
"""

import os
import re
import sys
from urllib.parse import urlparse

# Known protected database project references and identifiers
FORBIDDEN_DATABASE_IDENTIFIERS = [
    "ordzcyrzqhdsavfkkouz",  # Mumbai Development Supabase Project Ref
    "tokyo",                 # Tokyo Backup DB
    "production",            # Production environments
    "prod",
]


def verify_staging_database(database_url: str = None, expected_project_ref: str = None) -> bool:
    """
    Validates that the active or target database is an isolated staging instance.
    Raises RuntimeError and exits with code 1 if any protected or development database is matched.
    """
    db_url = database_url or os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("[ERROR] DATABASE_URL is empty or not provided.", file=sys.stderr)
        return False

    parsed = urlparse(db_url)
    user = parsed.username or ""
    host = parsed.hostname or ""
    port = parsed.port or 5432
    db_name = parsed.path.lstrip("/")

    print("=" * 65)
    print("FINLO CRM — DATABASE ISOLATION VERIFICATION")
    print("=" * 65)
    print(f"Target Host: {host}:{port}")
    print(f"Target Database: {db_name}")

    # Extract Supabase project ref if pooler format (postgres.<project_ref>)
    project_ref = None
    if "." in user:
        project_ref = user.split(".")[-1]
        print(f"Detected Supabase Project Ref: {project_ref}")

    # 1. Check for Forbidden Project References
    for forbidden in FORBIDDEN_DATABASE_IDENTIFIERS:
        if (project_ref and forbidden in project_ref.lower()) or (forbidden in host.lower()) or (forbidden in user.lower()):
            print(
                f"\n[CRITICAL SAFETY VIOLATION] Target database matches protected identifier '{forbidden}'!\n"
                f"  Matched User/Host: {user}@{host}\n"
                "  Database modification against Mumbai development or Tokyo backup is strictly BLOCKED.\n"
                "  Aborting immediately.",
                file=sys.stderr,
            )
            return False

    # 2. Check Expected Staging Project Ref
    exp_ref = expected_project_ref or os.environ.get("STAGING_PROJECT_REF")
    if exp_ref:
        if project_ref != exp_ref:
            print(
                f"\n[SAFETY MISMATCH] Detected project ref '{project_ref}' does not match "
                f"expected STAGING_PROJECT_REF '{exp_ref}'. Aborting.",
                file=sys.stderr,
            )
            return False
        print(f"[VERIFIED] Project ref matches expected staging: '{exp_ref}'")

    # 3. Check Target Environment Flag
    target_env = os.environ.get("FINLO_TARGET_ENV", "").lower()
    if target_env != "staging" and os.environ.get("FINLO_ALLOW_LOCAL_LOADTEST", "0") != "1":
        print(
            "\n[SAFETY BLOCKED] FINLO_TARGET_ENV is not set to 'staging'.\n"
            "You must explicitly set 'FINLO_TARGET_ENV=staging' to verify staging operations.",
            file=sys.stderr,
        )
        return False

    # 4. Check Connection Pooling Port
    if port == 6543:
        print("[INFO] Connected via Port 6543 (Transaction Pooler - Recommended for 1,000 users)")
    elif port == 5432:
        print("[INFO] Connected via Port 5432 (Session Pooler / Direct - Recommended for smoke/baseline tests)")
    else:
        print(f"[INFO] Connected via custom port {port}")

    # 5. Live Read-Only Connection & Metadata Check
    try:
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=10)
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version();")
            row = cur.fetchone()
            cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
            table_count = cur.fetchone()[0]
            cur.execute("SELECT ssl_is_used();")
            ssl_used = cur.fetchone()[0]

        conn.close()

        print(f"\n[CONNECTION SUCCESS]")
        print(f"  Live Database: {row[0]}")
        print(f"  Connected User: {row[1]}")
        print(f"  SSL In Use: {ssl_used}")
        print(f"  Public Tables Count: {table_count}")
        print(f"  Engine: {row[2].split(',')[0]}")
        print("=" * 65)
        print("[ISOLATION VERIFIED] Safe staging database confirmed.\n")
        return True

    except Exception as exc:
        print(f"\n[CONNECTION ERROR] Could not connect to database: {exc}", file=sys.stderr)
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify database isolation before staging operations.")
    parser.add_argument("--url", default=None, help="Database URL to inspect (defaults to DATABASE_URL env var).")
    parser.add_argument("--project-ref", default=None, help="Expected staging Supabase project reference.")
    args = parser.parse_args()

    success = verify_staging_database(database_url=args.url, expected_project_ref=args.project_ref)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

