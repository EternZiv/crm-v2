import requests

session = requests.Session()
login_page = session.get("http://127.0.0.1:8000/login/", headers={"Accept-Encoding": "gzip"})
import re
csrf = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', login_page.text).group(1)
session.post("http://127.0.0.1:8000/login/", data={"username": "test_bdo", "password": "FinloTest2026!", "csrfmiddlewaretoken": csrf})

endpoints = [
    ("Leads Table", "/crm/leads/leads-list/"),
    ("Tasks Table", "/activity/global-task-list/"),
    ("Accounts Table", "/crm/accounts/accounts-list-view/"),
    ("Contacts Table", "/crm/contacts/contact-list-view/"),
    ("Opportunities Table", "/crm/opportunities/opportunities-list/"),
]

print(f"{'Endpoint':<25} | {'Uncompressed':<15} | {'Compressed (Wire)':<20} | {'Compression %':<15}")
print("-" * 80)
for name, path in endpoints:
    r = session.get(f"http://127.0.0.1:8000{path}", headers={"HX-Request": "true", "Accept-Encoding": "gzip"}, stream=True)
    wire_bytes = len(r.raw.read())
    uncompressed = len(r.content)
    ratio = (1 - (wire_bytes / uncompressed)) * 100
    print(f"{name:<25} | {uncompressed/1024:<12.1f} KB | {wire_bytes/1024:<17.1f} KB | {ratio:<14.1f}%")

