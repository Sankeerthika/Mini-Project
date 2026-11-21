import urllib.request
import urllib.parse
import json
import sys

BASE = "http://localhost:8000/api"

def req(method, path, token=None, data=None, form=False):
    url = BASE + path
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = e.read().decode()
        return e.code, body

failures = []
def check(label, condition, detail=""):
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label} -- {detail}")
        failures.append(label)

# 1. Admin Login
code, data = req("POST", "/auth/login", data={"username":"admin@example.com","password":"Admin123!"}, form=True)
check("1. Admin login works", code == 200, f"code={code} {json.dumps(data)[:200]}")
if code != 200:
    print("ABORT: cannot proceed without admin login")
    sys.exit(1)
token = data["access_token"]
print(f"       role={data['user']['role']} email={data['user']['email']} token_len={len(token)}")

# PRE-CLEANUP: reactivate prior test users so registration tests are idempotent
# We reactivate instead of delete (no DELETE /users API).
_TEST_EMAILS = ["alice2@example.com", "bob2@example.com", "hacker2@x.com", "created@admin.com"]
_cc, _existing = req("GET", "/users", token=token)
if _cc == 200 and isinstance(_existing, list):
    for _u in _existing:
        if _u.get("email") in _TEST_EMAILS and _u.get("is_active") == False:
            req("PATCH", f"/users/{_u['id']}/status", token=token, data={"is_active": True})

def find_by_email(email):
    sc, lst = req("GET", f"/users?search={email}", token=token)
    if sc == 200 and isinstance(lst, list):
        for u in lst:
            if u.get("email") == email:
                return u
    return None

# 2. GET /auth/me
code, me = req("GET", "/auth/me", token=token)
check("2. GET /auth/me works", code == 200 and me.get("email") == "admin@example.com", f"code={code}")
if code == 200:
    print(f"       {me['first_name']} {me['last_name']} role={me['role']} active={me['is_active']}")

# 3. Admin statistics
code, stats = req("GET", "/admin/statistics", token=token)
check("3. Admin statistics works", code == 200 and stats['total_admins'] >= 1, f"code={code} stats={stats}")
if code == 200:
    print(f"       users={stats['total_users']} admins={stats['total_admins']} managers={stats['total_managers']} employees={stats['total_employees']}")

# 4. GET /api/users
code, users = req("GET", "/users", token=token)
check("4. GET /users works (admin)", code == 200, f"code={code}")
if code == 200:
    print(f"       {len(users)} user(s) returned")

# 5. Register Employee (public) — idempotent: accept 201 OR existing user
code, emp = req("POST", "/auth/register", data={"first_name":"Alice","last_name":"Smith","email":"alice2@example.com","password":"alice123","role":"employee"})
if code != 201:
    found = find_by_email("alice2@example.com")
    if found and found.get("role") == "employee":
        emp = found
        req("PUT", f"/users/{emp['id']}", token=token, data={"password":"alice123"})
        req("PATCH", f"/users/{emp['id']}/status", token=token, data={"is_active": True})
        code = 201
check("5. Register Employee public works", code == 201, f"code={code} {json.dumps(emp)[:200]}")
if code == 201:
    print(f"       id={emp['id']} role={emp['role']} email={emp['email']}")

# 6. Register Manager (public) — idempotent
code, mgr = req("POST", "/auth/register", data={"first_name":"Bob","last_name":"Jones","email":"bob2@example.com","password":"bob123","role":"manager"})
if code != 201:
    found = find_by_email("bob2@example.com")
    if found and found.get("role") == "manager":
        mgr = found
        req("PUT", f"/users/{mgr['id']}", token=token, data={"password":"bob123"})
        req("PATCH", f"/users/{mgr['id']}/status", token=token, data={"is_active": True})
        code = 201
check("6. Register Manager public works", code == 201, f"code={code} {json.dumps(mgr)[:200]}")
if code == 201:
    print(f"       id={mgr['id']} role={mgr['role']} email={mgr['email']}")

# 7. Try register Admin -> MUST FAIL 403
code, bad = req("POST", "/auth/register", data={"first_name":"H","last_name":"X","email":"hacker2@x.com","password":"x","role":"admin"})
check("7. Register Admin BLOCKED with 403", code == 403, f"got code={code} {json.dumps(bad)[:200]}")

# 8. Employee login
code, empTok = req("POST", "/auth/login", data={"username":"alice2@example.com","password":"alice123"}, form=True)
if code == 200:
    # Employee -> /users must be 403
    code2, bad2 = req("GET", "/users", token=empTok["access_token"])
    check("8. Employee -> GET /users BLOCKED with 403", code2 == 403, f"code={code2}")
else:
    check("8. Employee login FAILED (could not test step 8)", False, f"login code={code}")

# 9. Manager login
code, mgrTok = req("POST", "/auth/login", data={"username":"bob2@example.com","password":"bob123"}, form=True)
if code == 200:
    code2, bad2 = req("GET", "/users", token=mgrTok["access_token"])
    check("9. Manager -> GET /users BLOCKED with 403", code2 == 403, f"code={code2}")
else:
    check("9. Manager login FAILED (could not test step 9)", False, f"login code={code}")

# 10. Admin deactivates Alice
code, found = req("GET", "/users?search=alice2", token=token)
if code == 200 and len(found) > 0:
    alice = None
    for f in found:
        if f.get("email") == "alice2@example.com":
            alice = f
            break
    if alice is None:
        alice = found[0]
    alice_id = alice["id"]
    code, data = req("PATCH", f"/users/{alice_id}/status", token=token, data={"is_active": False})
    check("10. Admin deactivates Alice", code == 200 and data.get("is_active") == False, f"code={code}")
    # Test login now blocked 403
    code2, bad2 = req("POST", "/auth/login", data={"username":"alice2@example.com","password":"alice123"}, form=True)
    check("11. Deactivated Alice login BLOCKED with 403", code2 == 403, f"code={code2} detail={json.dumps(bad2)[:150]}")
else:
    check("10. Could not find Alice (skip)", False, f"search returned code={code}")

# 12. Invalid JWT
code, bad = req("GET", "/auth/me", token="garbage.token.123")
check("12. Invalid JWT returns 401", code == 401, f"code={code}")

# 13. Admin creates a user — idempotent: accept 201 OR existing user
code, new = req("POST", "/users", token=token, data={"first_name":"CreatedBy","last_name":"Admin","email":"created@admin.com","password":"pass123","role":"employee"})
if code != 201:
    found = find_by_email("created@admin.com")
    if found:
        new = found
        req("PUT", f"/users/{new['id']}", token=token, data={"password":"pass123"})
        req("PATCH", f"/users/{new['id']}/status", token=token, data={"is_active": True})
        code = 201
check("13. Admin creates user via POST /users", code == 201, f"code={code} {str(new)[:150]}")
if code == 201:
    # Ensure role is employee before step 14 (PUT will change to manager)
    if new.get("role") != "employee":
        req("PUT", f"/users/{new['id']}", token=token, data={"role":"employee"})
    # 14. Edit user role to manager
    code2, edited = req("PUT", f"/users/{new['id']}", token=token, data={"role":"manager"})
    check("14. Admin edits user role (PUT)", code2 == 200 and edited.get("role") == "manager", f"code={code2} role={edited.get('role')}")

# 15. Last-admin guard: try deactivating only admin must fail
code, me_resp = req("GET", "/auth/me", token=token)
my_id = me_resp.get("id") if code == 200 else None
code, admins = req("GET", "/users?role=admin", token=token)
guard_tested = False
guard_ok = False
if code == 200 and my_id is not None:
    active_admins = [a for a in admins if a.get("is_active") and a.get("id") != my_id]
    other_active_ids = [a["id"] for a in active_admins]
    reactivate_queue = []
    try:
        for oid in other_active_ids:
            dc, dr = req("PATCH", f"/users/{oid}/status", token=token, data={"is_active": False})
            if dc == 200:
                reactivate_queue.append(oid)
        code_chk, _ = req("PATCH", f"/users/{my_id}/status", token=token, data={"is_active": False})
        guard_tested = True
        guard_ok = (code_chk == 400)
    finally:
        for oid in reactivate_queue:
            req("PATCH", f"/users/{oid}/status", token=token, data={"is_active": True})
if guard_tested:
    check("15. Last-active-admin guard prevents deactivation", guard_ok, f"code={code_chk if guard_tested else 'N/A'}")
else:
    check("15. Last-active-admin guard test unavailable", False, f"code={code}, my_id={my_id}")

# Final stats
code, final = req("GET", "/admin/statistics", token=token)
if code == 200:
    print()
    print(f"FINAL: total_users={final['total_users']} admins={final['total_admins']} managers={final['total_managers']} employees={final['total_employees']} meetings={final['total_meetings']} tasks={final['total_tasks']}")

print()
if not failures:
    print("============ ALL TESTS PASSED ============")
else:
    print(f"!!!!! {len(failures)} TESTS FAILED: {failures}")
    sys.exit(1)
