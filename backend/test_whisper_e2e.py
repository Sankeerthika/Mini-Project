"""
Milestone 9: Authorization + upload-regression end-to-end test.

Covers (without heavy Whisper invocation):
- Employee JWT -> 403 on transcribe
- Admin JWT -> 403 on transcribe
- Manager A hitting Manager B's meeting -> 404
- Upload still 201

Run:
  cd backend
  ..\.venv\Scripts\python.exe test_whisper_e2e.py
"""
import os, sys, time, json, io, wave, struct, uuid, urllib.request, urllib.parse, urllib.error, threading, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()

from app.utils.security import hash_password
from app.database import SessionLocal
from app.models.models import User, Meeting, UserRole

TEST_PORT = 8768
BASE = f"http://127.0.0.1:{TEST_PORT}"

cleanup_ids = {"managers": [], "admins": [], "employees": [], "meetings": [], "files": []}

def make_wav(dur=0.5, fr=8000):
    n = int(dur * fr); buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(fr)
        frames = [struct.pack("<h", max(-32768, min(32767, int(5000*random.uniform(-1,1))))) for _ in range(n)]
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


def create_user(role, bucket):
    name = {UserRole.MANAGER: "mgr", UserRole.ADMIN: "adm", UserRole.EMPLOYEE: "emp"}[role]
    email = f"t9_{name}_{uuid.uuid4().hex[:6]}@example.com"
    pw = "T9pass!23"
    db = SessionLocal()
    try:
        u = User(email=email, first_name="T9", last_name=name.upper(), hashed_password=hash_password(pw), role=role, is_active=True)
        db.add(u); db.commit(); db.refresh(u)
        cleanup_ids[bucket].append(u.id)
        return u.id, email, pw
    finally:
        db.close()


def start_uvicorn():
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=TEST_PORT, log_level="error")


def wait_server(to=20):
    dl = time.time() + to
    while time.time() < dl:
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=1) as r:
                if r.status == 200: return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("server unhealthy")


def http(method, path, body=None, headers=None, content_type=None):
    h = dict(headers or {})
    if content_type: h["Content-Type"] = content_type
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.headers.get("Content-Type",""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type",""), e.read()


def login(email, pw):
    s,_,b = http("POST","/api/auth/login",
        body=urllib.parse.urlencode({"username":email,"password":pw}).encode(),
        content_type="application/x-www-form-urlencoded")
    assert s == 200, f"login {email} failed {s}: {b.decode()[:500]}"
    d = json.loads(b.decode()); tok = d["access_token"]
    print(f"[login] {email} -> user {d['user']['id']} role {d['user']['role']}")
    return tok


def multipart(fields, files):
    b = "----T9B" + uuid.uuid4().hex
    lines = []
    for k,v in fields.items():
        lines += [f"--{b}".encode(), f'Content-Disposition: form-data; name="{k}"'.encode(), b"", v.encode("utf-8")]
    for k,fn,ct,data in files:
        lines += [f"--{b}".encode(),
                  f'Content-Disposition: form-data; name="{k}"; filename="{fn}"'.encode(),
                  f"Content-Type: {ct}".encode(), b"", data]
    lines += [f"--{b}--".encode(), b""]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={b}"


def upload(tok, wav_bytes, suffix="_a"):
    body, ct = multipart({"title":f"M9 Auth Test Meeting {suffix}","description":"Auth regression"},
                         [("recording", f"m9_test{suffix}.wav", "audio/wav", wav_bytes)])
    s,_,b = http("POST","/api/meetings", body=body, headers={"Authorization": f"Bearer {tok}"}, content_type=ct)
    print(f"[upload {suffix}] HTTP {s}")
    assert s == 201, f"upload {suffix} {s}: {b.decode()[:500]}"
    d = json.loads(b.decode())
    cleanup_ids["meetings"].append(d["id"])
    return d


def main():
    t = threading.Thread(target=start_uvicorn, daemon=True); t.start()
    wait_server()

    _, adm_e, adm_p = create_user(UserRole.ADMIN, "admins")
    _, emp_e, emp_p = create_user(UserRole.EMPLOYEE, "employees")
    mgrA_id, mA_e, mA_p = create_user(UserRole.MANAGER, "managers")
    mgrB_id, mB_e, mB_p = create_user(UserRole.MANAGER, "managers")

    adm_t = login(adm_e, adm_p)
    emp_t = login(emp_e, emp_p)
    mA_t = login(mA_e, mA_p)
    mB_t = login(mB_e, mB_p)

    wavA = make_wav(); wavB = make_wav(); wavExtra = make_wav()
    mA_meeting = upload(mA_t, wavA, "_mA")
    mB_meeting = upload(mB_t, wavB, "_mB")

    print(f"\n[Rule-TR-4.4] Extra upload regression POST -> HTTP 201"); extra = upload(mA_t, wavExtra, "_extra")
    assert extra["status"] == "uploaded", f"expected status=uploaded got {extra['status']!r}"
    print(f"    status={extra['status']!r} (correct 'uploaded')  -> PASS")

    print(f"\n[Rule-TR-4.2] Admin POST /meetings/X/transcribe -> HTTP 403")
    s,_,b = http("POST",f"/api/meetings/{mA_meeting['id']}/transcribe", headers={"Authorization": f"Bearer {adm_t}"})
    print(f"    HTTP {s} (expected 403)")
    assert s == 403, f"expected 403 got {s}: {b.decode()[:400]}"
    print("    -> PASS")

    print(f"\n[Rule-TR-4.1] Employee POST /meetings/X/transcribe -> HTTP 403")
    s,_,b = http("POST",f"/api/meetings/{mA_meeting['id']}/transcribe", headers={"Authorization": f"Bearer {emp_t}"})
    print(f"    HTTP {s} (expected 403)")
    assert s == 403, f"expected 403 got {s}: {b.decode()[:400]}"
    print("    -> PASS")

    print(f"\n[Rule-TR-4.3] ManagerA POST ManagerB's meeting -> HTTP 404")
    s,_,b = http("POST",f"/api/meetings/{mB_meeting['id']}/transcribe", headers={"Authorization": f"Bearer {mA_t}"})
    print(f"    Manager A hits meeting {mB_meeting['id']} (B's) -> HTTP {s} (expected 404)")
    assert s == 404, f"expected 404 got {s}: {b.decode()[:400]}"
    print("    -> PASS")

    print(f"\n[EXTRA] Manager A with invalid meeting id 9999999 -> HTTP 404")
    s,_,b = http("POST","/api/meetings/9999999/transcribe", headers={"Authorization": f"Bearer {mA_t}"})
    assert s == 404, f"expected 404 got {s}"
    print("    -> PASS")

    print("\n=== Task 4: ALL authorization & regression assertions PASSED ===")
    return 0


def cleanup():
    print("\n[cleanup] removing temp rows/files:")
    db = SessionLocal()
    try:
        for mid in cleanup_ids["meetings"]:
            m = db.query(Meeting).filter(Meeting.id == mid).first()
            if m:
                if m.recording_path and os.path.isfile(m.recording_path):
                    try: os.remove(m.recording_path); print(f"  file {os.path.basename(m.recording_path)} removed")
                    except OSError: pass
                db.query(Meeting).filter(Meeting.id == mid).delete()
                print(f"  meeting {mid} deleted")
        for table, cls, bucket in [("admins",User,"admins"),("employees",User,"employees"),("managers",User,"managers")]:
            for uid in cleanup_ids[bucket]:
                db.query(User).filter(User.id == uid).delete()
                print(f"  user {uid} removed ({table})")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    try: code = main()
    finally: cleanup()
    sys.exit(code)
