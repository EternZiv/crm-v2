"""
Finlo CRM v2 — Staging Database Initialization Script.
Gated by strict database isolation verification before running migrations and data seeding.
"""

import argparse
import os
import subprocess
import sys

from scripts.verify_db_isolation import verify_staging_database


def init_staging_database(user_count: int = 250, confirm: bool = False):
    print("=" * 70)
    print("FINLO CRM v2 — STAGING DATABASE INITIALIZATION")
    print("=" * 70)

    # 1. Mandatory Gate: Verify Database Identity & Isolation
    is_safe_staging = verify_staging_database()
    if not is_safe_staging:
        print("\n[ABORTED] Preflight verification failed. Migrations and seeding will NOT proceed.", file=sys.stderr)
        sys.exit(1)

    if not confirm:
        print(
            "\n[CONFIRMATION REQUIRED] Pass '--confirm' to execute migrations and seed users against this staging DB.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Run Migrations
    print("\n--- Running Django Migrations on Confirmed Staging DB ---")
    python_exe = sys.executable
    res_migrate = subprocess.run([python_exe, "manage.py", "migrate", "--noinput"])
    if res_migrate.returncode != 0:
        print("\n[ERROR] Migrations failed. Check connection and logs.", file=sys.stderr)
        sys.exit(res_migrate.returncode)

    # 3. Seed Synthetic Test Users
    print(f"\n--- Seeding {user_count} Staging Test Users ---")
    from load_tests.seed_staging_users import seed_staging_users
    seed_staging_users(count=user_count, output_csv="load_tests/data/test_users.csv")

    print("\n" + "=" * 70)
    print("STAGING DATABASE INITIALIZATION COMPLETE")
    print(f"  - Database schema migrated successfully.")
    print(f"  - {user_count} test accounts seeded across 3 companies and 6 hierarchy roles.")
    print("  - Credentials exported to 'load_tests/data/test_users.csv'.")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Initialize isolated staging database with migrations and test users.")
    parser.add_argument("--confirm", action="store_true", help="Confirmation flag required to execute migrations.")
    parser.add_argument("--user-count", type=int, default=250, help="Number of synthetic users to seed (default: 250).")
    args = parser.parse_args()

    init_staging_database(user_count=args.user_count, confirm=args.confirm)


if __name__ == "__main__":
    main()

