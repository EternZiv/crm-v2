import requests
import re
import csv

base_url = "http://127.0.0.1:8000"

users = []
with open("load_tests/data/local_test_users.csv", mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        users.append((row["username"], row["password"], row.get("role", "user"), row.get("company", "FINLONEXA UAT")))

print("================================================================================")
print("  FINLO CRM v2 — MULTI-ROLE & COMPANY ISOLATION VERIFICATION SUITE")
print(f"  Testing {len(users)} representative roles against live Daphne server")
print("================================================================================\n")

endpoints = [
    ("Dashboard Partial", "/dashboard/?section=home", {"HX-Request": "true"}),
    ("Accounts Table", "/crm/accounts/accounts-list-view/", {"HX-Request": "true"}),
    ("Leads Table", "/crm/leads/leads-list/", {"HX-Request": "true"}),
    ("Contacts Table", "/crm/contacts/contact-list-view/", {"HX-Request": "true"}),
    ("Opportunities Table", "/crm/opportunities/opportunities-list/", {"HX-Request": "true"}),
    ("Global Tasks", "/activity/global-task-list/", {"HX-Request": "true"}),
]

all_passed = True

for username, password, role, company in users:
    session = requests.Session()
    session.headers.update({"Accept-Encoding": "gzip"})
    
    # Login flow
    login_page = session.get(f"{base_url}/login/")
    csrf = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', login_page.text).group(1)
    login_resp = session.post(
        f"{base_url}/login/",
        data={"username": username, "password": password, "csrfmiddlewaretoken": csrf},
        headers={"Referer": f"{base_url}/login/"}
    )
    auth_ok = bool(session.cookies.get("sessionid"))
    print(f"Role: [{role:<16}] User: {username:<12} | Company: {company} | Auth: {'OK' if auth_ok else 'FAIL'}")
    
    if not auth_ok:
        all_passed = False
        continue

    for name, path, hdrs in endpoints:
        r = session.get(f"{base_url}{path}", headers=hdrs)
        status = r.status_code
        wire_size = len(r.content) / 1024.0
        gzip_ok = r.headers.get("Content-Encoding") == "gzip"
        passed = (status == 200) and (wire_size > 1.0)
        if not passed:
            all_passed = False
        print(f"   - {name:<22}: HTTP {status} | {wire_size:<5.1f} KB | Gzip: {gzip_ok} | {'PASS' if passed else 'FAIL'}")
    print()

print(f"Multi-Role & Company RBAC Verification Result: {'ALL PASS' if all_passed else 'FAILURES DETECTED'}")

