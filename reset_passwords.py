import urllib.request
import urllib.parse
import json

BASE = "http://localhost:8000/api"

def req(method, path, data=None, token=None, form=False):
    url = BASE + path
    headers = {}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r)
        txt = resp.read().decode()
        return resp.status, json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, {"detail": txt}

# Admin login
code, d = req("POST", "/auth/login", {"username": "admin@example.com", "password": "Admin123!"}, form=True)
print("Admin login:", code)
at = d["access_token"]

# Find manager
code, users = req("GET", "/users?search=manager", token=at)
print("Users:", [(u["id"], u["email"], u["role"]) for u in users])

# Reset all test users passwords
for email, new_pwd in [
    ("manager@example.com", "Manager123!"),
    ("employee@example.com", "Employee123!"),
    ("inactivemgr@example.com", "Inactive123!"),
]:
    uid = next((u["id"] for u in users if u["email"] == email), None)
    if uid:
        code, d = req("PUT", f"/users/{uid}", {"password": new_pwd}, token=at)
        print(f"Reset pwd {email}: {code}")
        # Verify login
        code, d = req("POST", "/auth/login", {"username": email, "password": new_pwd}, form=True)
        print(f"  Verify login {email}: {code}")

# Ensure there is at least 1 Employee for team_members stat
if not any(u["email"] == "employee@example.com" for u in users):
    code, d = req("POST", "/auth/register", {
        "email": "employee@example.com", "first_name": "Evan", "last_name": "Employee",
        "password": "Employee123!", "role": "employee"
    })
    print(f"Create employee: {code}")
