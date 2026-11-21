import os, sys, time, json, io, wave, struct, uuid, urllib.request, urllib.parse, urllib.error, threading, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.utils.security import hash_password
from app.database import SessionLocal
from app.models.models import User, Meeting, UserRole

TEST_PORT = 8766
BASE = f"http://127.0.0.1:{TEST_PORT}"

MANAGER_EMAIL = f"verify_m8_{uuid.uuid4().hex[:6]}@example.com"
MANAGER_PASSWORD = "VerifyM8!23"


def make_small_wav_bytes(duration_sec: float = 0.5, framerate: int = 8000) -> bytes:
    n_samples = int(duration_sec * framerate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        samples = []
        for i in range(n_samples):
            val = int(5000 * random.uniform(-1, 1))
            samples.append(struct.pack("<h", max(-32768, min(32767, val))))
        wf.writeframes(b"".join(samples))
    return buf.getvalue()


def create_manager():
    db = SessionLocal()
    try:
        u = User(
            email=MANAGER_EMAIL,
            first_name="Verify",
            last_name="ManagerM8",
            hashed_password=hash_password(MANAGER_PASSWORD),
            role=UserRole.MANAGER,
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        print(f"[DB] Created manager id={u.id} email={MANAGER_EMAIL}")
        return u.id
    finally:
        db.close()


def start_uvicorn():
    import uvicorn
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=TEST_PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def wait_for_server(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=1.0) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("Server did not become healthy")


def http(method, path, body=None, headers=None, content_type=None):
    h = dict(headers or {})
    if content_type:
        h["Content-Type"] = content_type
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


def login(email, password):
    status, ct, body = http(
        "POST", "/api/auth/login",
        body=urllib.parse.urlencode({"username": email, "password": password}).encode("utf-8"),
        content_type="application/x-www-form-urlencoded",
    )
    assert status == 200, f"Login failed {status}: {body.decode()[:500]}"
    data = json.loads(body.decode())
    print(f"[HTTP] Login OK: user_id={data['user']['id']} role={data['user']['role']}")
    return data["access_token"]


def encode_multipart(fields, files):
    boundary = "----VerifyM8" + uuid.uuid4().hex
    lines = []
    for name, value in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        lines.append(b"")
        lines.append(value.encode("utf-8"))
    for name, filename, content, mime in files:
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode())
        lines.append(f"Content-Type: {mime}".encode())
        lines.append(b"")
        lines.append(content)
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"


def main():
    print("=" * 80)
    print("Milestone 8 DIRECT VERIFICATION (artifacts preserved for inspection)")
    print("=" * 80)

    mgr_id = create_manager()

    t = threading.Thread(target=start_uvicorn, daemon=True)
    t.start()
    wait_for_server()

    token = login(MANAGER_EMAIL, MANAGER_PASSWORD)
    auth = {"Authorization": f"Bearer {token}"}

    wav_bytes = make_small_wav_bytes()
    print(f"\n[DATA] Synthetic WAV: {len(wav_bytes)} bytes")

    mp_body, mp_ct = encode_multipart(
        fields={
            "title": "Milestone 8 Direct Verify Meeting",
            "description": "Uploaded for final M8 verification.",
        },
        files=[("recording", "verify_m8.wav", wav_bytes, "audio/wav")],
    )

    # === 1. HTTP Upload ===
    print("\n--- VERIFICATION 1: POST /api/meetings HTTP 201 ---")
    status, ct, raw = http("POST", "/api/meetings", body=mp_body, headers=auth, content_type=mp_ct)
    text = raw.decode("utf-8", errors="replace")
    print(f"HTTP status: {status}")
    print(f"Response body: {text[:1200]}")
    assert status == 201, f"FAIL: Expected 201 got {status}"
    created = json.loads(text)
    meeting_id = created["id"]
    print(f"PASS: HTTP 201. Meeting id={meeting_id}")
    print(f"  original_filename = {created.get('original_filename')}")
    print(f"  content_type      = {created.get('content_type')}")
    print(f"  file_size         = {created.get('file_size')}")
    print(f"  status            = {created.get('status')}")
    print(f"  recording_path in response? {'recording_path' in created}")

    # === 2. Database Direct Query ===
    print("\n--- VERIFICATION 2: Direct PostgreSQL Query via SQLAlchemy ---")
    db = SessionLocal()
    try:
        row = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        assert row is not None, f"FAIL: Meeting id={meeting_id} NOT FOUND in database"
        print(f"PASS: Meeting row EXISTS in PostgreSQL")
        print(f"  id                = {row.id}")
        print(f"  title             = {row.title}")
        print(f"  original_filename = {row.original_filename}")
        print(f"  recording_path    = {row.recording_path}")
        print(f"  content_type      = {row.content_type}")
        print(f"  file_size         = {row.file_size}")
        print(f"  status            = {row.status}")
        print(f"  created_by_id     = {row.created_by_id} (matches manager id={mgr_id}: {row.created_by_id == mgr_id})")
        recording_path = row.recording_path
    finally:
        db.close()

    # === 3. GET /api/meetings ===
    print("\n--- VERIFICATION 3: GET /api/meetings returns the meeting ---")
    status, ct, raw = http("GET", "/api/meetings", headers=auth)
    assert status == 200, f"FAIL: Expected 200 got {status}"
    meetings = json.loads(raw.decode())
    print(f"Total meetings returned: {len(meetings)}")
    found = next((m for m in meetings if m["id"] == meeting_id), None)
    assert found is not None, f"FAIL: New meeting id={meeting_id} NOT in GET list"
    print(f"PASS: Meeting id={found['id']} in list with status={found['status']!r}")
    print(f"  title={found['title']!r}")
    print(f"  original_filename={found.get('original_filename')!r}")
    print(f"  recording_path in list item? {'recording_path' in found}")

    # === 4. Uploaded File on Disk ===
    print("\n--- VERIFICATION 4: Uploaded file exists in backend/uploads/ ---")
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    stored_exists = os.path.isfile(recording_path)
    stored_size = os.path.getsize(recording_path) if stored_exists else 0
    print(f"Expected path: {recording_path}")
    print(f"File exists? {stored_exists}")
    print(f"File size: {stored_size} bytes (expected {len(wav_bytes)})")
    assert stored_exists, f"FAIL: File does NOT exist at {recording_path}"
    assert stored_size == len(wav_bytes), f"FAIL: Size mismatch {stored_size} vs {len(wav_bytes)}"
    with open(recording_path, "rb") as f:
        disk_bytes = f.read()
    print(f"Contents match uploaded bytes? {disk_bytes == wav_bytes}")
    assert disk_bytes == wav_bytes, "FAIL: File contents differ!"
    basename = os.path.basename(recording_path)
    print(f"PASS: Stored file uploads/{basename} exists with correct bytes.")

    # === 5. Manager Auth ===
    print("\n--- VERIFICATION 5: Manager authorization works, Admin blocked ---")
    db = SessionLocal()
    try:
        admin_email = f"verify_admin_{uuid.uuid4().hex[:6]}@example.com"
        a = User(
            email=admin_email,
            first_name="Verify",
            last_name="AdminM8",
            hashed_password=hash_password("VerifyAdmin!23"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        admin_id = a.id
    finally:
        db.close()
    admin_token = login(admin_email, "VerifyAdmin!23")
    status2, _, raw2 = http("POST", "/api/meetings", body=mp_body, headers={"Authorization": f"Bearer {admin_token}"}, content_type=mp_ct)
    print(f"Admin POST -> HTTP {status2} (expected 403)")
    assert status2 == 403, f"FAIL: Admin expected 403 got {status2}"
    print(f"PASS: Admin correctly blocked with HTTP 403")

    print("\n" + "=" * 80)
    print("ALL 5 VERIFICATIONS PASSED")
    print("=" * 80)
    print(f"\nArtifacts LEFT IN PLACE for inspection:")
    print(f"  Manager user: id={mgr_id} email={MANAGER_EMAIL}")
    print(f"  Admin user:   id={admin_id} email={admin_email}")
    print(f"  Meeting row:  id={meeting_id} (PostgreSQL meetings table)")
    print(f"  Audio file:   {recording_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
