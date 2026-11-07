"""
Finlo CRM v2 — Synthetic Load Test Data Cleanup & Rollback Script.
Safely queries and deletes all synthetic entities created with the 'LOADTEST_' prefix.
"""

import argparse
import os
import sys

# Prefix to match
PREFIX = "LOADTEST_"


def run_django_orm_cleanup(dry_run: bool = False):
    """Purges synthetic load test records via Django ORM."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")
    try:
        import django
        django.setup()
    except Exception as e:
        print(f"[ERROR] Failed to initialize Django: {e}", file=sys.stderr)
        sys.exit(1)

    from django.conf import settings
    # Safety Check: Prevent running cleanup against production
    db_config = settings.DATABASES.get("default", {})
    db_url = os.environ.get("DATABASE_URL", "")
    target_env = os.environ.get("FINLO_TARGET_ENV", "").lower()

    if target_env != "staging" and os.environ.get("FINLO_ALLOW_LOCAL_LOADTEST", "0") != "1":
        print(
            "\n[SAFETY GUARD] Cleanup refused: FINLO_TARGET_ENV is not set to 'staging'.\n"
            "To prevent accidental data loss, cleanup will only run against a confirmed staging environment.\n"
            "Set 'FINLO_TARGET_ENV=staging' to proceed.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from django.db import transaction
    from finlo.contrib.activity.models import Activity
    from finlo_crm.accounts.models import Account
    from finlo_crm.contacts.models import Contact
    from finlo_crm.leads.models import Lead
    from finlo_crm.opportunities.models import Opportunity

    print("=" * 60)
    print("FINLO CRM — SYNTHETIC LOAD TEST DATA CLEANUP")
    print(f"Target Prefix: '{PREFIX}'")
    print(f"Dry Run Mode: {dry_run}")
    print("=" * 60)

    # 1. Leads
    leads_qs = Lead.objects.filter(first_name__startswith=PREFIX) | Lead.objects.filter(lead_company__startswith=PREFIX)
    leads_count = leads_qs.count()

    # 2. Opportunities
    opps_qs = Opportunity.objects.filter(name__startswith=PREFIX)
    opps_count = opps_qs.count()

    # 3. Contacts
    contacts_qs = Contact.objects.filter(first_name__startswith=PREFIX)
    contacts_count = contacts_qs.count()

    # 4. Accounts
    accounts_qs = Account.objects.filter(name__startswith=PREFIX)
    accounts_count = accounts_qs.count()

    # 5. Activities & Tasks
    tasks_qs = Activity.objects.filter(title__startswith=PREFIX)
    tasks_count = tasks_qs.count()

    print(f"  Found {leads_count:<6} synthetic Leads")
    print(f"  Found {opps_count:<6} synthetic Opportunities")
    print(f"  Found {contacts_count:<6} synthetic Contacts")
    print(f"  Found {accounts_count:<6} synthetic Accounts")
    print(f"  Found {tasks_count:<6} synthetic Tasks / Activities")

    total = leads_count + opps_count + contacts_count + accounts_count + tasks_count
    print("-" * 60)
    print(f"  Total records matching prefix: {total}")

    if dry_run or total == 0:
        print("[DRY RUN COMPLETE] No records were deleted.")
        return

    # Execute deletion in an atomic transaction
    with transaction.atomic():
        deleted_leads, _ = leads_qs.delete()
        deleted_opps, _ = opps_qs.delete()
        deleted_contacts, _ = contacts_qs.delete()
        deleted_accounts, _ = accounts_qs.delete()
        deleted_tasks, _ = tasks_qs.delete()

    print("\n[SUCCESS] Successfully purged synthetic load test records:")
    print(f"  - Leads deleted: {deleted_leads}")
    print(f"  - Opportunities deleted: {deleted_opps}")
    print(f"  - Contacts deleted: {deleted_contacts}")
    print(f"  - Accounts deleted: {deleted_accounts}")
    print(f"  - Tasks deleted: {deleted_tasks}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Purge synthetic load test data from Finlo CRM staging.")
    parser.add_argument("--dry-run", action="store_true", help="Count records without deleting.")
    parser.add_argument("--confirm", action="store_true", help="Confirmation flag required to execute deletion.")
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("[SAFETY GUARD] You must specify --confirm to execute record deletion, or --dry-run to preview.", file=sys.stderr)
        sys.exit(1)

    run_django_orm_cleanup(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

