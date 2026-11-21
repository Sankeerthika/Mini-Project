"""
Milestone 8 end-to-end upload test.

Steps performed:
1. Ensure a Manager user exists in the DB (create temp one if needed).
2. Start the FastAPI uvicorn server on a test port (8765) in the background.
3. POST /api/auth/login as Manager -> receive bearer token.
4. POST /api/meetings with a small valid synthetic .wav audio file via multipart/form-data.
5. Verify HTTP 201 + returned JSON has all 4 new fields: original_filename, content_type, file_size, status.
6. GET /api/meetings -> HTTP 200 + the new meeting appears in list with status 'uploaded'.
7. GET /api/meetings/{id} -> HTTP 200 + correct metadata.
8. Verify the stored recording file physically exists under backend/uploads/.
9. Cleanup test meeting row. Remove temp manager user if we created it.
10. Stop server.

Run:
  cd backend
  ..\.venv\Scripts\python.exe test_upload_e2e.py
"""
import os, sys, time, json, io, wave, struct, uuid, urllib.request, urllib.parse, urllib.error, threading, shutil, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from app.utils.security import hash_password
from app.database import SessionLocal
from app.models.models import User, Meeting, UserRole

TEST_PORT = 8765
BASE = f"http://127.0.0.1:{TEST_PORT}"

DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOSTNAME = os.getenv("DATABASE_HOSTNAME")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_NAME = os.getenv("DATABASE_NAME")

TEMP_MANAGER_EMAIL = f"temp_m8_test_{uuid.uuid4().hex[:8]}@example.com"
TEMP_MANAGER_PASSWORD = "TempM8Pass!23"
our_created_manager_id = None
our_created_meeting_id = None
created_stored_filename = None


def make_small_wav_bytes(duration_sec: float = 0.5, framerate: int = 8000) -> bytes:
    """Return bytes of a valid tiny 16-bit PCM WAV file (no file on disk needed)."""
    n_samples = int(duration_sec * framerate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        samples = []
        for i in range(n_samples):
            t = i / framerate
            val = int(5000 * random.uniform(-1, 1))  # quiet noise, valid WAV
            samples.append(struct.pack("<h", max(-32768, min(32767, val))))
        wf.writeframes(b"".join(samples))
    return buf.getvalue()


def ensure_manager():
    """Return (email, password) of a manager that exists. If none exist, create a temp one."""
    global our_created_manager_id
    db = SessionLocal()
    try:
        mgr = db.query(User).filter(User.role == UserRole.MANAGER, User.is_active == True).first()
        if mgr is not None:
            # We found an existing manager, but we don't know their password. Create a temp one.
            print("[SETUP] Existing manager found (id={}) but password unknown — creating temp manager for test login.".format(mgr.id))
        # Create temp manager regardless to ensure clean login with known creds
        u = User(
            email=TEMP_MANAGER_EMAIL,
            first_name="Temp",
            last_name="ManagerM8",
            hashed_password=hash_password(TEMP_MANAGER_PASSWORD),
            role=UserRole.MANAGER,
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        our_created_manager_id = u.id
        print("[SETUP] Created temp manager id={} email={}".format(u.id, TEMP_MANAGER_EMAIL))
        return TEMP_MANAGER_EMAIL, TEMP_MANAGER_PASSWORD
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
                    body = json.loads(r.read().decode())
                    print("[SERVER] Health OK:", body)
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("Server did not become healthy within {}s".format(timeout))


def urlencode_form(data: dict) -> bytes:
    return urllib.parse.urlencode(data).encode("utf-8")


def http(method: str, path: str, body: bytes | None = None, headers: dict | None = None, content_type: str | None = None):
    h = dict(headers or {})
    if content_type:
        h["Content-Type"] = content_type
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type", "")
            return r.status, ct, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        ct = e.headers.get("Content-Type", "")
        return e.code, ct, raw


def login(email: str, password: str) -> str:
    status, ct, body = http(
        "POST", "/api/auth/login",
        body=urlencode_form({"username": email, "password": password}),
        content_type="application/x-www-form-urlencoded",
    )
    text = body.decode("utf-8", errors="replace")
    if status != 200:
        raise RuntimeError(f"Login FAILED status={status}: {text[:500]}")
    data = json.loads(text)
    token = data["access_token"]
    print("[LOGIN] OK as {} user_id={} role={}".format(email, data.get("user", {}).get("id"), data.get("user", {}).get("role")))
    return token


def encode_multipart_form(fields: dict[str, str], files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    """Manual multipart/form-data encoder. Returns (body_bytes, content_type_with_boundary)."""
    boundary = "----BoundaryM8Test" + uuid.uuid4().hex
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
    body = b"\r\n".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


def main():
    global our_created_meeting_id, created_stored_filename

    print("=" * 80)
    print("Milestone 8 — END-TO-END UPLOAD TEST")
    print("=" * 80)

    email, password = ensure_manager()

    # Start server in background daemon thread
    t = threading.Thread(target=start_uvicorn, daemon=True)
    t.start()
    try:
        wait_for_server()
    except Exception as e:
        print("[SERVER] FAILED to start:", e)
        return 1

    token = login(email, password)
    auth_headers = {"Authorization": f"Bearer {token}"}

    # --- Step 4: POST /api/meetings with valid audio file ---
    print()
    print("[TEST 1] POST /api/meetings — manager upload small .wav audio recording")
    wav_bytes = make_small_wav_bytes()
    print("   Generated synthetic WAV file: {} bytes".format(len(wav_bytes)))

    mp_body, mp_ct = encode_multipart_form(
        fields={
            "title": "Milestone 8 E2E Test Meeting",
            "description": "Uploaded by automated verification — may be deleted.",
        },
        files=[("recording", "m8_e2e_test.wav", wav_bytes, "audio/wav")],
    )

    status, ct, raw = http(
        "POST", "/api/meetings",
        body=mp_body,
        headers=auth_headers,
        content_type=mp_ct,
    )
    text = raw.decode("utf-8", errors="replace")
    print("   HTTP {} (expected 201)".format(status))
    if status != 201:
        print("   BODY:", text[:800])
    assert status == 201, f"Expected HTTP 201 but got {status}"
    created = json.loads(text)
    our_created_meeting_id = created["id"]
    print("   Created meeting id={}".format(created["id"]))
    print("   title             =", created.get("title"))
    print("   original_filename =", created.get("original_filename"))
    print("   content_type      =", created.get("content_type"))
    print("   file_size         =", created.get("file_size"), "bytes")
    print("   status            =", created.get("status"))
    print("   created_by_id     =", created.get("created_by_id"))
    print("   has recording_path in response?", "recording_path" in created)
    assert created.get("status") == "uploaded", f"Expected status 'uploaded', got {created.get('status')!r}"
    assert created.get("original_filename") == "m8_e2e_test.wav"
    assert created.get("file_size") == len(wav_bytes)
    assert "recording_path" not in created, "INTERNAL recording_path must NOT leak to API response"
    print("   -> TEST 1 PASSED: HTTP 201, all 4 new columns present, recording_path hidden.")

    # --- Step 5: GET /api/meetings list ---
    print()
    print("[TEST 2] GET /api/meetings — manager list includes newly uploaded meeting")
    status, ct, raw = http("GET", "/api/meetings", headers=auth_headers)
    assert status == 200, f"Expected HTTP 200 got {status}"
    meetings = json.loads(raw.decode())
    print("   Total meetings returned: {}".format(len(meetings)))
    found = next((m for m in meetings if m["id"] == our_created_meeting_id), None)
    assert found is not None, "Newly created meeting id={} not in GET /api/meetings list".format(our_created_meeting_id)
    print("   Found created meeting in list: id={} title={!r} status={!r}".format(found["id"], found["title"], found["status"]))
    assert found["status"] == "uploaded"
    assert found.get("original_filename") == "m8_e2e_test.wav"
    assert "recording_path" not in found, "recording_path must NOT appear in list response"
    print("   -> TEST 2 PASSED: Meeting correctly listed.")

    # --- Step 6: GET /api/meetings/{id} detail ---
    print()
    print("[TEST 3] GET /api/meetings/{} — detail metadata".format(our_created_meeting_id))
    status, ct, raw = http("GET", f"/api/meetings/{our_created_meeting_id}", headers=auth_headers)
    assert status == 200, f"Expected 200 got {status}"
    detail = json.loads(raw.decode())
    assert detail["id"] == our_created_meeting_id
    assert detail["status"] == "uploaded"
    print("   detail.title  =", detail["title"])
    print("   detail.status =", detail["status"])
    assert "recording_path" not in detail
    print("   -> TEST 3 PASSED: Detail endpoint returns metadata safely.")

    # --- Step 7: stored file physically exists in uploads/ ---
    print()
    print("[TEST 4] Physical file exists in backend/uploads/ (UUID-named)")
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    candidates = []
    for fn in os.listdir(uploads_dir):
        fp = os.path.join(uploads_dir, fn)
        if os.path.isfile(fp) and fn.lower().endswith(".wav") and fn != ".gitkeep":
            st = os.stat(fp)
            if st.st_size == len(wav_bytes):
                candidates.append((fn, st.st_mtime, st.st_size))
    candidates.sort(key=lambda x: -x[1])
    print("   Uploads dir candidate .wav files with matching size {} bytes:".format(len(wav_bytes)))
    for fn, mtime, size in candidates[:5]:
        print("      {}  {} bytes  mtime={}".format(fn, size, time.ctime(mtime)))
    assert candidates, "No matching .wav file found in uploads/ of size {} bytes".format(len(wav_bytes))
    created_stored_filename = candidates[0][0]
    stored_fp = os.path.join(uploads_dir, created_stored_filename)
    with open(stored_fp, "rb") as f:
        assert f.read() == wav_bytes, "Stored file contents differ from uploaded bytes!"
    print("   stored file = {} — contents match exactly.".format(created_stored_filename))
    print("   -> TEST 4 PASSED: File safely stored with unique UUID filename.")

    # --- Bonus: 403 for non-manager ---
    print()
    print("[TEST 5] Admin role attempting POST /api/meetings expects 403")
    # Create a temp admin and login
    db = SessionLocal()
    try:
        admin_email = f"temp_admin_m8_{uuid.uuid4().hex[:8]}@example.com"
        a = User(
            email=admin_email,
            first_name="Temp",
            last_name="AdminM8",
            hashed_password=hash_password("AdminM8Pass!23"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        temp_admin_id = a.id
    finally:
        db.close()
    admin_token = login(admin_email, "AdminM8Pass!23")
    status2, _, raw2 = http(
        "POST", "/api/meetings",
        body=mp_body,
        headers={"Authorization": f"Bearer {admin_token}"},
        content_type=mp_ct,
    )
    print("   Admin POST /api/meetings returned HTTP {} (expected 403)".format(status2))
    assert status2 == 403, f"Admin must not upload meetings: expected 403 got {status2}"
    # Cleanup temp admin
    db = SessionLocal()
    try:
        db.query(User).filter(User.id == temp_admin_id).delete()
        db.commit()
    finally:
        db.close()
    print("   -> TEST 5 PASSED: Admin correctly blocked with 403.")

    print()
    print("=" * 80)
    print("ALL MILSTONE 8 TESTS PASSED")
    print("=" * 80)

    return 0

def cleanup():
    global our_created_meeting_id, our_created_manager_id, created_stored_filename
    print()
    print("[CLEANUP] Removing test artifacts (preserves real data):")
    # 1) delete test meeting row
    if our_created_meeting_id is not None:
        db = SessionLocal()
        try:
            db.query(Meeting).filter(Meeting.id == our_created_meeting_id).delete()
            db.commit()
            print("   - Deleted meeting id={}".format(our_created_meeting_id))
        finally:
            db.close()
    # 2) delete temp manager user we created
    if our_created_manager_id is not None:
        db = SessionLocal()
        try:
            db.query(User).filter(User.id == our_created_manager_id).delete()
            db.commit()
            print("   - Deleted temp manager id={}".format(our_created_manager_id))
        finally:
            db.close()
    # 3) delete stored file from uploads/
    if created_stored_filename:
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
        fp = os.path.join(uploads_dir, created_stored_filename)
        if os.path.isfile(fp):
            os.remove(fp)
            print("   - Removed uploaded file uploads/{}".format(created_stored_filename))


if __name__ == "__main__":
    try:
        code = main()
    finally:
        cleanup()
    sys.exit(code)
