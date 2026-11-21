import sys
import os
import uuid
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.database import SessionLocal
from app.models.models import User, UserRole
from app.utils.security import hash_password

client = TestClient(app)

TMP_DIR = tempfile.mkdtemp()

def _make_dummy_audio(path):
    with open(path, "wb") as f:
        f.write(b"RIFF" + b"\x00" * 44)

def ensure_users(db):
    users = {
        "m1": {"email": "manager_m10_a@example.com", "fname": "M10A", "lname": "Manager", "role": UserRole.MANAGER, "pw": "Test1234!"},
        "m2": {"email": "manager_m10_b@example.com", "fname": "M10B", "lname": "Manager", "role": UserRole.MANAGER, "pw": "Test1234!"},
        "e1": {"email": "employee_m10@example.com", "fname": "M10E", "lname": "Employee", "role": UserRole.EMPLOYEE, "pw": "Test1234!"},
    }
    created = {}
    for key, spec in users.items():
        u = db.query(User).filter(User.email == spec["email"]).first()
        if not u:
            u = User(
                email=spec["email"],
                first_name=spec["fname"],
                last_name=spec["lname"],
                role=spec["role"],
                hashed_password=hash_password(spec["pw"]),
                is_active=True,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        created[key] = u
    return created


def login(email, pw):
    r = client.post("/api/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def upload_meeting(token, title, transcript_to_inject=None):
    path = os.path.join(TMP_DIR, f"dummy_{uuid.uuid4().hex}.wav")
    _make_dummy_audio(path)
    with open(path, "rb") as f:
        files = {"recording": ("dummy.wav", f, "audio/wav")}
        data = {"title": title}
        r = client.post("/api/meetings", headers=auth_header(token), data=data, files=files)
    assert r.status_code == 201, f"Upload meeting failed: {r.status_code} {r.text}"
    meeting_id = r.json()["id"]
    if transcript_to_inject is not None:
        db = SessionLocal()
        try:
            from app.models.models import Meeting, MeetingStatus
            m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            m.transcript = transcript_to_inject
            m.status = MeetingStatus.COMPLETED
            db.commit()
        finally:
            db.close()
    return meeting_id


def cleanup_db():
    db = SessionLocal()
    try:
        from app.models.models import Meeting, User
        emails = ["manager_m10_a@example.com", "manager_m10_b@example.com", "employee_m10@example.com"]
        users = db.query(User).filter(User.email.in_(emails)).all()
        uids = [u.id for u in users]
        if uids:
            db.query(Meeting).filter(Meeting.created_by_id.in_(uids)).delete(synchronize_session=False)
        for u in users:
            db.delete(u)
        db.commit()
    except Exception as e:
        print(f"[CLEANUP WARNING] {e}")
        db.rollback()
    finally:
        db.close()


def main():
    results = []

    def record(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append((name, status, detail))
        print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

    try:
        cleanup_db()

        db = SessionLocal()
        users = ensure_users(db)
        db.close()

        m1_token = login("manager_m10_a@example.com", "Test1234!")
        m2_token = login("manager_m10_b@example.com", "Test1234!")
        e1_token = login("employee_m10@example.com", "Test1234!")

        sample_transcript = (
            "Alice: Welcome everyone. Today we decided we will launch the new feature by 2026-12-01. "
            "Bob: I will prepare the launch plan by the end of next week. "
            "Charlie: I will coordinate the marketing campaign. "
            "Key decision: We are moving the launch date from November to December 1st."
        )

        # 1. Manager can analyze their own transcribed meeting
        mid = upload_meeting(m1_token, "M10 Launch Meeting", transcript_to_inject=sample_transcript)
        r = client.post(f"/api/meetings/{mid}/analyze", headers=auth_header(m1_token))
        record("T1. Manager analyzes own transcribed meeting", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            has_summary = bool(data.get("summary") and data["summary"].strip())
            has_decisions = bool(data.get("key_decisions") and data["key_decisions"].strip())
            has_actions = bool(data.get("action_items_json") and data["action_items_json"].strip())
            record("T1b. Analysis fields populated on response", has_summary and has_decisions and has_actions,
                   f"summary={has_summary}, decisions={has_decisions}, actions={has_actions}")
            try:
                parsed_actions = json.loads(data["action_items_json"]) if has_actions else []
                record("T1c. action_items_json parses to list of objects", isinstance(parsed_actions, list),
                       f"type={type(parsed_actions).__name__}, n={len(parsed_actions) if isinstance(parsed_actions, list) else 'n/a'}")
            except Exception as e:
                record("T1c. action_items_json parses to list of objects", False, f"JSON decode error: {e}")

        # 6. Idempotency: second call should NOT re-trigger service (still returns 200, same content)
        r2 = client.post(f"/api/meetings/{mid}/analyze", headers=auth_header(m1_token))
        record("T6. Idempotency — second analyze call returns 200", r2.status_code == 200, f"status={r2.status_code}")
        if r.status_code == 200 and r2.status_code == 200:
            match_summary = r.json().get("summary") == r2.json().get("summary")
            match_actions = r.json().get("action_items_json") == r2.json().get("action_items_json")
            record("T6b. Idempotency — returned analysis matches first call", match_summary and match_actions,
                   f"summary_eq={match_summary}, actions_eq={match_actions}")

        # 7 & 8. Persistence + GET returns saved analysis
        rget = client.get(f"/api/meetings/{mid}", headers=auth_header(m1_token))
        record("T7+T8. GET meeting returns saved analysis", rget.status_code == 200 and bool(rget.json().get("summary")),
               f"status={rget.status_code}, has_summary={bool(rget.json().get('summary')) if rget.status_code == 200 else 'n/a'}")

        # 2. Meeting without transcript is rejected
        mid_no_trans = upload_meeting(m1_token, "M10 No Transcript Meeting", transcript_to_inject=None)
        r_no_trans = client.post(f"/api/meetings/{mid_no_trans}/analyze", headers=auth_header(m1_token))
        record("T2. Missing transcript returns controlled 4xx", 400 <= r_no_trans.status_code < 500,
               f"status={r_no_trans.status_code}")

        # 3. Manager cannot analyze another manager's meeting
        r_cross = client.post(f"/api/meetings/{mid}/analyze", headers=auth_header(m2_token))
        record("T3. Other manager cannot analyze (404)", r_cross.status_code == 404, f"status={r_cross.status_code}")

        # 4. Employee cannot call the endpoint
        r_emp = client.post(f"/api/meetings/{mid}/analyze", headers=auth_header(e1_token))
        record("T4. Employee cannot analyze endpoint", r_emp.status_code in {401, 403}, f"status={r_emp.status_code}")

        # 5. Unauthorized request is rejected
        r_unauth = client.post(f"/api/meetings/{mid}/analyze")
        record("T5. No auth token rejected (401)", r_unauth.status_code == 401, f"status={r_unauth.status_code}")

        # Invalid meeting id
        r_invalid = client.post("/api/meetings/99999999/analyze", headers=auth_header(m1_token))
        record("TX. Invalid meeting id returns 404", r_invalid.status_code == 404, f"status={r_invalid.status_code}")

    finally:
        cleanup_db()

    print("\n" + "=" * 70)
    print(f"RESULTS: {sum(1 for _, s, _ in results if s == 'PASS')}/{len(results)} PASSED")
    print("=" * 70)
    for name, status, detail in results:
        print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ""))
    failed = [n for n, s, _ in results if s == "FAIL"]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
