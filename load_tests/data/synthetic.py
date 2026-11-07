"""
Synthetic Data Generator for Finlo CRM Load Testing.
Ensures all entities are strictly prefixed with LOADTEST_ for identification,
data isolation, and clean rollback/cleanup.
"""

import time
import uuid
from typing import Any, Dict
from load_tests.config import SYNTHETIC_DATA_PREFIX


class SyntheticDataGenerator:
    """Generates schema-compliant synthetic payloads for CRM create operations."""

    @staticmethod
    def _uid() -> str:
        return uuid.uuid4().hex[:8]

    @classmethod
    def generate_account(cls, user_id: str = "1") -> Dict[str, Any]:
        tag = cls._uid()
        return {
            "name": f"{SYNTHETIC_DATA_PREFIX}Account_{tag}",
            "website": f"https://{tag}.loadtest.example.com",
            "phone": "+1555019" + str(int(time.time()))[-4:],
            "email": f"account_{tag}@loadtest.example.com",
            "country": "US",
            "city": "Dallas",
            "state": "TX",
            "zip_code": "75001",
            "annual_revenue": "250000.00",
            "employees": "50",
            "description": f"Synthetic load test account generated at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        }

    @classmethod
    def generate_contact(cls, user_id: str = "1", account_id: str = "") -> Dict[str, Any]:
        tag = cls._uid()
        payload = {
            "first_name": f"{SYNTHETIC_DATA_PREFIX}Contact",
            "last_name": f"User_{tag}",
            "email": f"contact_{tag}@loadtest.example.com",
            "phone": "+1555028" + str(int(time.time()))[-4:],
            "mobile": "+1555029" + str(int(time.time()))[-4:],
            "title": "Director of Operations",
            "department": "Operations",
            "country": "US",
            "city": "Austin",
            "state": "TX",
            "description": "Synthetic load test contact",
        }
        if account_id:
            payload["account"] = account_id
        return payload

    @classmethod
    def generate_lead(cls, user_id: str = "1") -> Dict[str, Any]:
        tag = cls._uid()
        return {
            "title": "VP of Technology",
            "first_name": f"{SYNTHETIC_DATA_PREFIX}Lead",
            "last_name": f"Prospect_{tag}",
            "email": f"lead_{tag}@loadtest.example.com",
            "contact_number": "+1555037" + str(int(time.time()))[-4:],
            "lead_company": f"{SYNTHETIC_DATA_PREFIX}Enterprise_{tag}",
            "no_of_employees": "120",
            "industry": "TECHNOLOGY",
            "annual_revenue": "1500000.00",
            "country": "US",
            "state": "CA",
            "city": "San Francisco",
            "zip_code": "94105",
            "requirements": "Looking for CRM migration and cloud hosting",
        }

    @classmethod
    def generate_opportunity(cls, user_id: str = "1", account_id: str = "") -> Dict[str, Any]:
        tag = cls._uid()
        payload = {
            "name": f"{SYNTHETIC_DATA_PREFIX}Deal_{tag}",
            "amount": "75000.00",
            "probability": "50",
            "expected_revenue": "37500.00",
            "close_date": "2027-12-31",
            "type": "New Business",
            "lead_source": "Web",
            "description": "Synthetic opportunity for pipeline load test",
        }
        if account_id:
            payload["account"] = account_id
        return payload

    @classmethod
    def generate_task(cls, user_id: str = "1") -> Dict[str, Any]:
        tag = cls._uid()
        return {
            "title": f"{SYNTHETIC_DATA_PREFIX}Task_{tag}",
            "status": "Not Started",
            "priority": "Normal",
            "due_date": "2027-12-15",
            "description": "Synthetic load test task reminder",
        }
