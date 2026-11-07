import requests
import re

base_url = "http://127.0.0.1:8000"
session = requests.Session()

# 1. Fetch login page and extract CSRF
login_page = session.get(f"{base_url}/login/", headers={"Accept-Encoding": "gzip"})
csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else session.cookies.get("csrftoken")

# 2. Authenticate
login_resp = session.post(
    f"{base_url}/login/",
    data={"username": "test_bdo", "password": "FinloTest2026!", "csrfmiddlewaretoken": csrf_token},
    headers={"Referer": f"{base_url}/login/", "Accept-Encoding": "gzip"}
)
print(f"POST /login/: status={login_resp.status_code}, authenticated={bool(session.cookies.get('sessionid'))}")

endpoints = [
    ("Dashboard Shell", "/dashboard/?section=home", {}),
    ("Dashboard Partial (HTMX)", "/dashboard/?section=home", {"HX-Request": "true"}),
    ("Accounts Shell", "/crm/accounts/accounts-view/", {}),
    ("Accounts Table (HTMX)", "/crm/accounts/accounts-list-view/", {"HX-Request": "true"}),
    ("Leads Shell", "/crm/leads/leads-view/", {}),
    ("Leads Table (HTMX)", "/crm/leads/leads-list/", {"HX-Request": "true"}),
    ("Contacts Shell", "/crm/contacts/contacts-view/", {}),
    ("Contacts Table (HTMX)", "/crm/contacts/contact-list-view/", {"HX-Request": "true"}),
    ("Opportunities Shell", "/crm/opportunities/opportunities-view/", {}),
    ("Opportunities Table (HTMX)", "/crm/opportunities/opportunities-list/", {"HX-Request": "true"}),
    ("Tasks (HTMX Global Task List)", "/activity/global-task-list/", {"HX-Request": "true"}),
]

print("\n--- Verifying Core CRM Modules with HTTP Compression ---")
all_passed = True
for name, path, headers in endpoints:
    headers["Accept-Encoding"] = "gzip"
    r = session.get(f"{base_url}{path}", headers=headers)
    passed = r.status_code == 200 and len(r.content) > 100
    if not passed:
        all_passed = False
    uncompressed_kb = len(r.content) / 1024
    is_gzip = r.headers.get("Content-Encoding") == "gzip"
    print(f"[{'PASS' if passed else 'FAIL'}] {name:<30}: HTTP {r.status_code}, Uncompressed: {uncompressed_kb:.1f} KB, Gzip: {is_gzip}")

print(f"\nFinal Verification Status: {'ALL PASS' if all_passed else 'SOME FAILED'}")
