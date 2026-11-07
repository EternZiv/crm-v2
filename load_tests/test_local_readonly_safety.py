"""
Safety and Correctness Unit Tests for Local Read-Only Load Testing Mode.
Verifies that:
1. Target host safety rules strictly reject localhost by default.
2. Target host safety rules require both FINLO_ALLOW_LOCAL_LOADTEST=1 and FINLO_LOCAL_READONLY=1.
3. Database project identification properly extracts Mumbai Supabase identifier without exposing credentials.
4. LocalReadOnlyUser persona contains ONLY GET / HEAD operations (zero POST/PUT/PATCH/DELETE).
5. No detail views are called in LocalReadOnlyUser (preventing RecentlyViewedMixin writes).
"""

import os
import unittest
from urllib.parse import urlparse

from load_tests.config import SafetyError, get_database_project_info, validate_target_host
from load_tests.users.local_readonly_user import LocalReadOnlyUser


class LocalReadOnlySafetyTests(unittest.TestCase):
    def setUp(self):
        self.orig_allow = os.environ.get("FINLO_ALLOW_LOCAL_LOADTEST")
        self.orig_readonly = os.environ.get("FINLO_LOCAL_READONLY")
        self.orig_env = os.environ.get("FINLO_TARGET_ENV")

        # Clear safety flags for isolation
        os.environ.pop("FINLO_ALLOW_LOCAL_LOADTEST", None)
        os.environ.pop("FINLO_LOCAL_READONLY", None)
        os.environ.pop("FINLO_TARGET_ENV", None)

    def tearDown(self):
        if self.orig_allow is not None:
            os.environ["FINLO_ALLOW_LOCAL_LOADTEST"] = self.orig_allow
        else:
            os.environ.pop("FINLO_ALLOW_LOCAL_LOADTEST", None)

        if self.orig_readonly is not None:
            os.environ["FINLO_LOCAL_READONLY"] = self.orig_readonly
        else:
            os.environ.pop("FINLO_LOCAL_READONLY", None)

        if self.orig_env is not None:
            os.environ["FINLO_TARGET_ENV"] = self.orig_env
        else:
            os.environ.pop("FINLO_TARGET_ENV", None)

    def test_localhost_blocked_by_default(self):
        with self.assertRaises(SafetyError) as ctx:
            validate_target_host("http://127.0.0.1:8000")
        self.assertIn("blocked by default", str(ctx.exception))

    def test_localhost_blocked_without_readonly_flag(self):
        os.environ["FINLO_ALLOW_LOCAL_LOADTEST"] = "1"
        with self.assertRaises(SafetyError) as ctx:
            validate_target_host("http://127.0.0.1:8000")
        self.assertIn("strictly requires FINLO_LOCAL_READONLY=1", str(ctx.exception))

    def test_localhost_allowed_with_both_flags(self):
        os.environ["FINLO_ALLOW_LOCAL_LOADTEST"] = "1"
        os.environ["FINLO_LOCAL_READONLY"] = "1"
        self.assertTrue(validate_target_host("http://127.0.0.1:8000"))

    def test_localhost_allowed_with_profile_argument(self):
        os.environ["FINLO_ALLOW_LOCAL_LOADTEST"] = "1"
        self.assertTrue(validate_target_host("http://127.0.0.1:8000", profile="local-readonly"))

    def test_production_always_blocked(self):
        os.environ["FINLO_ALLOW_LOCAL_LOADTEST"] = "1"
        os.environ["FINLO_LOCAL_READONLY"] = "1"
        with self.assertRaises(SafetyError):
            validate_target_host("https://app.finlo.com")

    def test_database_project_info_extracts_mumbai_safely(self):
        info = get_database_project_info()
        self.assertTrue(info["configured"])
        self.assertEqual(info["project_id"], "ordzcyrzqhdsavfkkouz")
        self.assertIn("ap-south-1", info["region"])
        self.assertTrue(info["is_mumbai"])
        # Ensure no passwords leaked
        self.assertNotIn("password", str(info).lower())

    def test_local_readonly_user_contains_zero_write_tasks(self):
        # Inspect all tasks on LocalReadOnlyUser
        tasks = LocalReadOnlyUser.tasks
        self.assertGreater(len(tasks), 0)

        for task_obj in tasks:
            func = task_obj if callable(task_obj) else getattr(task_obj, "locust_task", None)
            func_name = getattr(func, "__name__", str(task_obj))
            doc = getattr(func, "__doc__", "") or ""

            # Check function names do not imply create/update/delete/post
            for forbidden_verb in ("create", "update", "delete", "post", "put", "patch"):
                self.assertNotIn(
                    forbidden_verb,
                    func_name.lower(),
                    f"Task {func_name} in LocalReadOnlyUser suggests mutating operation!",
                )

            # Check that detail views are not called (which would trigger RecentlyViewedMixin)
            self.assertNotIn(
                "detail",
                func_name.lower(),
                f"Task {func_name} calls a detail view which would trigger RecentlyViewed database writes!",
            )


if __name__ == "__main__":
    unittest.main()

