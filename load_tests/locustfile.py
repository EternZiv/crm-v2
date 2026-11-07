"""
Finlo CRM v2 — Enterprise Load Testing Suite.
Main Locustfile entrypoint defining user classes, lifecycle hooks, and safety enforcement.
Supports both isolated staging testing and strict local read-only execution against Mumbai.
"""

import logging
import os
import sys
from locust import events
from locust.runners import MasterRunner

from load_tests.common.auth import CREDENTIAL_POOL
from load_tests.config import LOCAL_READONLY_PROFILE, get_database_project_info, validate_target_host
from load_tests.users.browser_user import BrowserUser
from load_tests.users.data_entry import DataEntryUser
from load_tests.users.local_readonly_user import LocalReadOnlyUser
from load_tests.users.sales_manager import SalesManagerUser
from load_tests.users.sales_rep import SalesRepUser
from load_tests.users.websocket_user import NotificationWebSocketUser

logger = logging.getLogger("finlo_loadtest")

# Expose virtual user classes to Locust CLI
__all__ = [
    "LocalReadOnlyUser",
    "SalesRepUser",
    "SalesManagerUser",
    "DataEntryUser",
    "BrowserUser",
    "NotificationWebSocketUser",
]


@events.init_command_line_parser.add_listener
def init_parser(parser):
    """Adds custom command line arguments for load profile selection."""
    parser.add_argument(
        "--finlo-profile",
        type=str,
        env_var="FINLO_PROFILE",
        default="local-readonly",
        help="Finlo load test profile: 'local-readonly' (safe read-only) or 'staging' (full suite).",
    )


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Validates target environment safety before any workers spawn or requests fire.
    Enforces strict read-only personas when targeting localhost/Mumbai database.
    """
    host = environment.host
    if not host:
        print("\n[CRITICAL ERROR] No target host specified! Use --host http://127.0.0.1:8000", file=sys.stderr)
        return

    profile = "local-readonly"
    if hasattr(environment, "parsed_options") and environment.parsed_options and hasattr(environment.parsed_options, "finlo_profile"):
        profile = environment.parsed_options.finlo_profile
    else:
        profile = os.environ.get("FINLO_PROFILE", "local-readonly")

    try:
        validate_target_host(host, profile=profile)
    except Exception as exc:
        print(f"\n[SAFETY ABORT] {exc}", file=sys.stderr)
        sys.exit(1)

    is_local = "127.0.0.1" in host or "localhost" in host

    if profile == LOCAL_READONLY_PROFILE or is_local:
        # Enforce that only strictly read-only user classes can run
        forbidden_classes = ["DataEntryUser", "SalesRepUser", "SalesManagerUser"]
        active_class_names = [cls.__name__ for cls in environment.user_classes]

        has_forbidden = any(name in forbidden_classes for name in active_class_names)
        if has_forbidden and is_local and profile != "staging-override":
            print(
                f"[SAFETY GUARD] Replacing mutating user classes ({active_class_names}) "
                f"with [LocalReadOnlyUser] for local execution against Mumbai database.",
                file=sys.stderr,
            )
            environment.user_classes = [LocalReadOnlyUser]


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Prints prominent pre-run safety banner and initializes user credentials pool.
    """
    host = environment.host
    user_count = environment.runner.target_user_count if hasattr(environment.runner, "target_user_count") else "Unknown"
    is_master = isinstance(environment.runner, MasterRunner)
    db_info = get_database_project_info()

    profile = "local-readonly"
    if hasattr(environment, "parsed_options") and environment.parsed_options and hasattr(environment.parsed_options, "finlo_profile"):
        profile = environment.parsed_options.finlo_profile
    else:
        profile = os.environ.get("FINLO_PROFILE", "local-readonly")

    is_local = host and ("127.0.0.1" in host or "localhost" in host)

    print("\n" + "=" * 78)
    print("  FINLO CRM v2 — LOAD TESTING SUITE")
    print("=" * 78)
    print(f"  Target Host:             {host}")
    print(f"  Database Project ID:     {db_info['project_id']}")
    print(f"  Database Host / Region:  {db_info['host']} ({db_info['region']})")
    print(f"  Execution Profile:       {profile.upper()}")
    print(f"  Active Personas:         {[cls.__name__ for cls in environment.user_classes]}")
    if is_local or profile == LOCAL_READONLY_PROFILE:
        print("  Mutating HTTP Methods:   0 (POST/PUT/PATCH/DELETE STRICTLY DISABLED)")
        print("  Synthetic Provisioning:  DISABLED")
        print("  Database Cleanup:        DISABLED")
        print("  Detail View Access:      DISABLED (Bypasses RecentlyViewed writes)")
    print(f"  Target Concurrent Users: {user_count}")
    print(f"  Distributed Master:      {is_master}")
    print("  Emergency Stop:          Press Ctrl+C in PowerShell or run:")
    print("                           taskkill /F /IM locust.exe")
    print("=" * 78 + "\n")

    # Load custom test user pool if provided
    cred_file = os.environ.get("FINLO_TEST_USERS_FILE", "load_tests/data/local_test_users.csv")
    if os.path.exists(cred_file):
        CREDENTIAL_POOL.load_from_file(cred_file)
    else:
        # Check standard staging path if exists
        staging_cred = "load_tests/data/test_users.csv"
        if os.path.exists(staging_cred):
            CREDENTIAL_POOL.load_from_file(staging_cred)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Prints completion notice.
    """
    host = environment.host
    is_local = host and ("127.0.0.1" in host or "localhost" in host)

    print("\n" + "=" * 78)
    print("  FINLO CRM v2 — LOAD TESTING SUITE COMPLETED")
    if is_local:
        print("  Notice: Local read-only mode executed. No CRM records were modified or created.")
        print("  Zero cleanup required against Mumbai database.")
    else:
        print("  NOTICE: Staging mode executed. Remember to run cleanup if synthetic data was created:")
        print("    python load_tests/cleanup.py --host <staging-host>")
    print("=" * 78 + "\n")
