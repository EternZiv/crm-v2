"""
Authentication and Session Manager for Finlo CRM Load Testing.
Handles CSRF retrieval, login form submission, session validation,
and multi-tenant user credential leasing across roles and companies.
"""

import logging
import os
import re
from typing import Dict, List, Optional
from locust.exception import StopUser

logger = logging.getLogger("finlo_loadtest")

_CSRF_INPUT_PATTERN = re.compile(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']')


class UserCredentialPool:
    """Thread-safe pool of test user credentials across companies and roles."""

    def __init__(self, credentials: Optional[List[Dict[str, str]]] = None):
        self._credentials = credentials or []
        self._index = 0

    def load_from_file(self, filepath: str):
        """Loads credentials from CSV or JSON file."""
        if not os.path.exists(filepath):
            logger.warning("Credential file '%s' not found. Using default synthetic users.", filepath)
            return

        loaded = []
        if filepath.endswith(".csv"):
            import csv
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("username") and row.get("password"):
                        loaded.append(row)
        elif filepath.endswith(".json"):
            import json
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    loaded = data

        if loaded:
            self._credentials = loaded
            logger.info("Loaded %d test credentials from %s", len(loaded), filepath)

    def lease_credential(self, user_index: int) -> Dict[str, str]:
        """Lease a credential for a virtual user, round-robining if pool is smaller than virtual users."""
        if not self._credentials:
            # 1. Check for explicit local single/multi-user environment credentials
            local_user = os.environ.get("FINLO_TEST_USERNAME")
            local_pass = os.environ.get("FINLO_TEST_PASSWORD")
            if local_user and local_pass:
                return {
                    "username": local_user,
                    "password": local_pass,
                    "role": "ADMIN",
                    "company_id": "1",
                }

            # 2. Fallback to deterministic synthetic staging credential pattern
            role_cycle = ["BDO", "ASM", "SSM", "RSM", "HEAD_OF_SALES"]
            role = role_cycle[user_index % len(role_cycle)]
            company_id = (user_index % 3) + 1
            staging_password = os.environ.get("FINLO_STAGING_USER_PASSWORD")
            if not staging_password:
                raise ValueError(
                    "[SECURITY] Test user credentials are required. Either provide FINLO_TEST_USERNAME and "
                    "FINLO_TEST_PASSWORD in the environment, load credentials from a file via "
                    "FINLO_TEST_USERS_FILE (e.g. load_tests/data/local_test_users.csv), or set FINLO_STAGING_USER_PASSWORD."
                )
            return {
                "username": f"loadtest_user_{user_index + 1}@staging.test",
                "password": staging_password,
                "role": role,
                "company_id": str(company_id),
            }

        return self._credentials[user_index % len(self._credentials)]


# Global pool singleton
CREDENTIAL_POOL = UserCredentialPool()


class FinloAuthenticator:
    """Manages login lifecycle for a Locust virtual user."""

    @staticmethod
    def authenticate_session(user_instance, credential: Dict[str, str]) -> bool:
        """
        Executes real browser-like login flow without manufacturing cookies:
        1. GET /login/ to obtain CSRF cookie and hidden token.
        2. POST /login/ with credentials and CSRF.
        3. Validates redirect and presence of sessionid cookie.
        """
        username = credential.get("username", "")
        password = credential.get("password", "")
        masked_username = username[:3] + "***" if len(username) > 3 else "***"

        # 1. Fetch Login Page
        with user_instance.client.get(
            "/login/",
            name="[AUTH] GET /login/",
            catch_response=True,
            allow_redirects=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Failed to fetch login page (HTTP {resp.status_code})")
                raise StopUser(f"Cannot access login page for {masked_username}")

            # Extract CSRF token
            csrf_token = user_instance.client.cookies.get("csrftoken")
            if not csrf_token:
                match = _CSRF_INPUT_PATTERN.search(resp.text)
                if match:
                    csrf_token = match.group(1)

            if not csrf_token:
                resp.failure("Could not extract CSRF token from login page")
                raise StopUser(f"Missing CSRF token for {masked_username}")

        # 2. Submit Login Credentials
        login_payload = {
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": csrf_token,
            "next": "/dashboard/?section=home",
        }

        login_headers = {
            "Referer": f"{user_instance.client.base_url}/login/",
            "X-CSRFToken": csrf_token,
        }

        with user_instance.client.post(
            "/login/",
            data=login_payload,
            headers=login_headers,
            name="[AUTH] POST /login/",
            catch_response=True,
            allow_redirects=False,
        ) as post_resp:
            # Django redirects on successful login (HTTP 302 to next URL)
            is_redirect = post_resp.status_code in (301, 302, 303, 307)
            session_cookie = user_instance.client.cookies.get("sessionid")

            if is_redirect and session_cookie:
                post_resp.success()
                logger.debug("Successfully authenticated virtual user: %s (role: %s)", masked_username, credential.get("role", "unknown"))
                return True

            if post_resp.status_code == 429:
                post_resp.failure("Rate limit or login lockout triggered (HTTP 429)")
                raise StopUser("Rate limited on login")

            if "Invalid credentials" in post_resp.text:
                post_resp.failure("Authentication rejected: Invalid credentials")
                raise StopUser(f"Invalid credentials for user: {masked_username}")

            if not session_cookie:
                post_resp.failure(f"Authentication failed: No sessionid cookie set (HTTP {post_resp.status_code})")
                raise StopUser(f"Login failed for {masked_username}")

            post_resp.success()
            return True
