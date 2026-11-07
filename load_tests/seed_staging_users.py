"""
Finlo CRM v2 — Staging Test User & RBAC Seed Script.
Provisions synthetic users across multiple companies and sales hierarchy roles
for realistic 1,000-user concurrency testing.
Exports 'load_tests/data/test_users.csv' for the Locust runner.
"""

import argparse
import csv
import os
import sys

DEFAULT_USER_COUNT = 200
DEFAULT_PASSWORD = os.environ.get("FINLO_STAGING_USER_PASSWORD")


def seed_staging_users(count: int = DEFAULT_USER_COUNT, output_csv: str = "load_tests/data/test_users.csv"):
    password = DEFAULT_PASSWORD or os.environ.get("FINLO_STAGING_USER_PASSWORD")
    if not password:
        print(
            "\n[SECURITY ERROR] FINLO_STAGING_USER_PASSWORD environment variable is required.\n"
            "Provide secure staging credentials via environment.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")
    try:
        import django
        django.setup()
    except Exception as e:
        print(f"[ERROR] Failed to initialize Django: {e}", file=sys.stderr)
        sys.exit(1)

    # Safety Check: Prevent seeding dev or prod
    target_env = os.environ.get("FINLO_TARGET_ENV", "").lower()
    if target_env != "staging" and os.environ.get("FINLO_ALLOW_LOCAL_LOADTEST", "0") != "1":
        print(
            "\n[SAFETY GUARD] User seeding refused: FINLO_TARGET_ENV is not set to 'staging'.\n"
            "To prevent polluting active development or production databases, user seeding\n"
            "will only run against a confirmed staging environment.\n"
            "Set 'FINLO_TARGET_ENV=staging' to proceed.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from django.db import transaction
    from finlo.contrib.core.models import Company, Department, FinloUser, Role

    print("=" * 60)
    print("FINLO CRM — SEEDING STAGING TEST USERS")
    print(f"Target Count: {count} users")
    print(f"Output File: {output_csv}")
    print("=" * 60)

    # 1. Create or get staging companies
    with transaction.atomic():
        co_hq, _ = Company.objects.get_or_create(company_name="Staging HQ", defaults={"hq": True})
        co_east, _ = Company.objects.get_or_create(company_name="Staging Branch East", defaults={"hq": False})
        co_west, _ = Company.objects.get_or_create(company_name="Staging Branch West", defaults={"hq": False})
        companies = [co_hq, co_east, co_west]

        # 2. Create or get roles
        role_specs = [
            ("SUPER_ADMIN", "Super Admin"),
            ("HEAD_OF_SALES", "Head of Sales"),
            ("RSM", "Regional Sales Manager"),
            ("SSM", "Senior Sales Manager"),
            ("ASM", "Area Sales Manager"),
            ("BDO", "Business Development Officer"),
        ]
        roles = {}
        for key, name in role_specs:
            r, _ = Role.objects.get_or_create(system_key=key, defaults={"role_name": name})
            roles[key] = r

        # 3. Create or get sales department
        dept, _ = Department.objects.get_or_create(name="Sales", defaults={"company": co_hq})

        # 4. Create synthetic users
        user_records = []
        role_distribution = ["BDO"] * 60 + ["ASM"] * 15 + ["SSM"] * 10 + ["RSM"] * 10 + ["HEAD_OF_SALES"] * 4 + ["SUPER_ADMIN"] * 1

        for i in range(1, count + 1):
            username = f"loadtest_user_{i}@staging.test"
            company = companies[i % len(companies)]
            role_key = role_distribution[i % len(role_distribution)]
            role = roles[role_key]

            user, created = FinloUser.objects.get_or_create(
                username=username,
                defaults={
                    "email": username,
                    "first_name": f"LoadUser{i}",
                    "last_name": role_key,
                    "company": company,
                    "role": role,
                    "department": dept,
                    "is_active": True,
                },
            )

            # Ensure password is set
            user.set_password(DEFAULT_PASSWORD)
            user.save()

            user_records.append({
                "username": username,
                "password": DEFAULT_PASSWORD,
                "role": role_key,
                "company_id": str(company.id),
                "company_name": company.company_name,
            })

    # 5. Write to CSV
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["username", "password", "role", "company_id", "company_name"])
        writer.writeheader()
        writer.writerows(user_records)

    print(f"\n[SUCCESS] Successfully seeded {len(user_records)} staging users.")
    print(f"Exported credentials to '{output_csv}' for Locust execution.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Seed staging users and generate Locust credentials file.")
    parser.add_argument("--count", type=int, default=DEFAULT_USER_COUNT, help="Number of users to seed.")
    parser.add_argument("--output", default="load_tests/data/test_users.csv", help="Path to save credentials CSV.")
    args = parser.parse_args()

    seed_staging_users(count=args.count, output_csv=args.output)


if __name__ == "__main__":
    main()

