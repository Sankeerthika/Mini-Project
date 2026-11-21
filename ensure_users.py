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
at = d["access_token"]

# List ALL users
code, users = req("GET", "/users", token=at)
print("All users:")
for u in users:
    print(f"  id={u['id']} email={u['email']} role={u['role']} active={u['is_active']}")

emails = [u['email'] for u in users]

# Create employee if missing
if "employee@example.com" not in emails:
    code, d = req("POST", "/users", {
        "email": "employee@example.com", "first_name": "Evan", "last_name": "Employee",
        "password": "Employee123!", "role": "employee"
    }, token=at)
    print(f"Create employee via Admin: {code} {d}")

# Create inactivemgr if missing (if not exists already with that name)
if "inactivemgr@example.com" not in emails:
    code, d = req("POST", "/users", {
        "email": "inactivemgr@example.com", "first_name": "Ina", "last_name": "InactiveMgr",
        "password": "Inactive123!", "role": "manager"
    }, token=at)
    print(f"Create inactivemgr via Admin: {code} {d}")
    code, users2 = req("GET", "/users", token=at)
    iid = next(u['id'] for u in users2 if u["email"] == "inactivemgr@example.com")
    code, d = req("PATCH", f"/users/{iid}/status", {"is_active": False}, token=at)
    print(f"  Deactivate: {code}")

# Verify employee login
code, d = req("POST", "/auth/login", {"username": "employee@example.com", "password": "Employee123!"}, form=True)
print(f"Employee login verify: {code}")

# Refresh user list
code, users = req("GET", "/users", token=at)
print("\nFinal users:")
for u in users:
    print(f"  id={u['id']} email={u['email']} role={u['role']} active={u['is_active']}")
