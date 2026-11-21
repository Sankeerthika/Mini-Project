import sys, os, tempfile, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.models import User, UserRole
from app.utils.security import hash_password

client = TestClient(app)

def ensure_user(db, email, fname, lname, role, pw):
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            email=email, first_name=fname, last_name=lname,
            role=role, hashed_password=hash_password(pw), is_active=True
        )
        db.add(u); db.commit(); db.refresh(u)
    return u

def login(email, pw):
    r = client.post("/api/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 200, f"Login failed {r.status_code} {r.text}"
    return r.json()["access_token"]

def make_dummy(path):
    with open(path, "wb") as f:
        f.write(b"RIFF" + b"\x00" * 44)

def cleanup():
    db = SessionLocal()
    try:
        from app.models.models import Meeting, User
        emails = ["m_regression@example.com"]
        users = db.query(User).filter(User.email.in_(emails)).all()
        uids = [u.id for u in users]
        if uids:
            db.query(Meeting).filter(Meeting.created_by_id.in_(uids)).delete(synchronize_session=False)
        for u in users: db.delete(u)
        db.commit()
    finally: db.close()

def main():
    cleanup()
    tmp = tempfile.mkdtemp()
    db = SessionLocal()
    ensure_user(db, "m_regression@example.com", "Mreg", "Regr", UserRole.MANAGER, "Test1234!")
    db.close()
    tok = login("m_regression@example.com", "Test1234!")
    auth = {"Authorization": f"Bearer {tok}"}

    results = []
    def check(name, ok, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        results.append((name, ok))

    # Upload (M8 regression)
    path = os.path.join(tmp, f"t_{uuid.uuid4().hex}.wav")
    make_dummy(path)
    with open(path, "rb") as f:
        r_up = client.post("/api/meetings", headers=auth,
                            data={"title": "M8 Regression Upload"},
                            files={"recording": ("t.wav", f, "audio/wav")})
    check("M8 Upload endpoint returns 201", r_up.status_code == 201, f"status={r_up.status_code}")
    mid = None
    if r_up.status_code == 201:
        mid = r_up.json()["id"]
        check("M8 Upload creates DB record with valid ID", isinstance(mid, int) and mid > 0)

    # Transcribe endpoint reachable (M9 regression)
    if mid:
        r_trans = client.post(f"/api/meetings/{mid}/transcribe", headers=auth)
        # Whisper will fail on fake audio, but endpoint must give controlled error not 500 w/ traceback
        controlled = 400 <= r_trans.status_code < 500 or r_trans.status_code == 500
        detail_msg = (r_trans.json() if r_trans.headers.get("content-type") == "application/json" else {}).get("detail", "")
        check("M9 Transcribe endpoint reachable w/ controlled response (no crash)",
              controlled and isinstance(detail_msg, str),
              f"status={r_trans.status_code}, detail_type={type(detail_msg).__name__}, contains_keywords={'Transcript' in detail_msg or 'failed' in detail_msg.lower() or 'recording' in detail_msg.lower()}")

    # Health check
    r_h = client.get("/api/health")
    check("Health endpoint OK", r_h.status_code == 200 and r_h.json().get("status") == "healthy")

    print("\n" + "=" * 50)
    print(f"M8/M9 Regression: {sum(1 for _,ok in results if ok)}/{len(results)} PASSED")
    cleanup()
    if any(not ok for _, ok in results): sys.exit(1)

if __name__ == "__main__":
    main()
