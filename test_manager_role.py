import urllib.request
import urllib.parse
import urllib.error
import json
import sys

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

def test(name, cond, expected=None, got=None):
    ok = bool(cond)
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status}: {name}")
    if not ok:
        if expected is not None:
            print(f"   Expected: {expected}")
        if got is not None:
            print(f"   Got:      {got}")
    return ok

results = []

# 0. Register test users
print("=== SETUP: Registering test users ===")
for email, fname, lname, role, pwd in [
    ("manager@example.com", "Mia", "Manager", "manager", "Manager123!"),
    ("employee@example.com", "Evan", "Employee", "employee", "Employee123!"),
    ("inactivemgr@example.com", "Ina", "InactiveMgr", "manager", "Inactive123!"),
]:
    code, d = req("POST", "/auth/register", {
        "email": email, "first_name": fname, "last_name": lname,
        "password": pwd, "role": role
    })
    if code == 201:
        print(f"  Created {email}")
    elif code == 400 and "already exists" in str(d.get("detail", "")):
        print(f"  Already exists: {email}")
    else:
        print(f"  [{code}] {email}: {d}")

# Deactivate inactivemgr using admin
admin_code, admin_login = req("POST", "/auth/login", {
    "username": "admin@example.com", "password": "Admin123!"
}, form=True)
admin_token = admin_login["access_token"]
print(f"  Admin login: {admin_code}")

# Look up inactivemgr id
_, users = req("GET", "/users?search=inactivemgr", token=admin_token)
inactive_id = None
for u in users:
    if u["email"] == "inactivemgr@example.com":
        inactive_id = u["id"]
        break
if inactive_id:
    code, d = req("PATCH", f"/users/{inactive_id}/status", {"is_active": False}, token=admin_token)
    print(f"  Deactivated inactivemgr: {code}")

print("\n=== BEGIN TESTS ===")

# TEST 1: Admin login
code, d = req("POST", "/auth/login", {"username": "admin@example.com", "password": "Admin123!"}, form=True)
admin_token = d.get("access_token")
results.append(test("1. Admin login works",
    code == 200 and admin_token is not None,
    expected="200 + access_token",
    got=(code, d.get("detail", d))))

# TEST 2: Manager login
code, d = req("POST", "/auth/login", {"username": "manager@example.com", "password": "Manager123!"}, form=True)
manager_token = d.get("access_token")
results.append(test("2. Manager login works",
    code == 200 and manager_token is not None,
    expected="200 + access_token",
    got=(code, d.get("detail", d))))

# TEST 3: GET /api/auth/me for Manager
code, me = req("GET", "/auth/me", token=manager_token)
required_keys = {"id", "first_name", "last_name", "email", "role", "is_active"}
results.append(test("3. auth/me works for Manager (includes required fields)",
    code == 200 and required_keys.issubset(set(me.keys())) and me["role"] == "manager",
    expected=f"200 + keys={required_keys}, role=manager",
    got=(code, me)))

# TEST 4: GET /api/manager/statistics for Manager
code, stats = req("GET", "/manager/statistics", token=manager_token)
stats_keys = {"total_meetings", "total_tasks", "pending_tasks", "completed_tasks", "overdue_tasks", "team_members"}
results.append(test("4. GET /api/manager/statistics works for Manager",
    code == 200 and stats_keys.issubset(set(stats.keys())),
    expected=f"200 + keys={stats_keys}",
    got=(code, stats)))

# TEST 5: Admin cannot access Manager-only API
code, d = req("GET", "/manager/statistics", token=admin_token)
results.append(test("5. Admin cannot access Manager-only API (expect 403)",
    code == 403,
    expected="403 Forbidden",
    got=(code, d)))

# TEST 6: Employee cannot access Manager-only API
code_e, emp_login = req("POST", "/auth/login", {"username": "employee@example.com", "password": "Employee123!"}, form=True)
employee_token = emp_login.get("access_token") if code_e == 200 else None
if employee_token:
    code, d = req("GET", "/manager/statistics", token=employee_token)
    results.append(test("6. Employee cannot access Manager-only API (expect 403)",
        code == 403,
        expected="403 Forbidden",
        got=(code, d)))
else:
    results.append(test("6. Employee cannot access Manager-only API (SKIP - no token)", False, got="Employee login failed"))

# TEST 7: Unauthenticated request returns 401
code, d = req("GET", "/manager/statistics")
results.append(test("7. Unauthenticated request returns 401",
    code == 401,
    expected="401 Unauthorized",
    got=(code, d)))

# TEST 8: Inactive Manager cannot use protected Manager APIs
code_i, i_login = req("POST", "/auth/login", {"username": "inactivemgr@example.com", "password": "Inactive123!"}, form=True)
# Login should be blocked because inactive, or if somehow got token, me should be blocked
if code_i == 403:
    results.append(test("8. Inactive Manager cannot use protected APIs (login blocked with 403)", True))
else:
    # If login somehow allowed, test using me endpoint
    tok = i_login.get("access_token")
    if tok:
        code, d = req("GET", "/auth/me", token=tok)
        results.append(test("8. Inactive Manager cannot use protected APIs",
            code == 403,
            expected="403",
            got=(code, d)))
    else:
        results.append(test("8. Inactive Manager cannot use protected APIs",
            code_i != 200,
            expected="login not allowed",
            got=(code_i, i_login)))

# TEST 9: Admin dashboard API still works
code, s = req("GET", "/admin/statistics", token=admin_token)
results.append(test("9. Admin dashboard statistics API still works",
    code == 200 and "total_users" in s,
    expected="200 with total_users",
    got=(code, s)))

# TEST 10: Admin user management still works (list + create)
code, ulist = req("GET", "/users", token=admin_token)
results.append(test("10. Admin user management list still works",
    code == 200 and isinstance(ulist, list),
    expected="200 with list",
    got=(code, type(ulist).__name__)))

print("\n=== SUMMARY ===")
passed = sum(results)
total = len(results)
print(f"Passed: {passed}/{total}")
sys.exit(0 if passed == total else 1)
