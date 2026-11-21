"""
Milestone 9 CROWN JEWEL direct verification.

Uses real Whisper transcription on a real copied ~4.8 MB sample mp4 from uploads/.
Overrides WHISPER_MODEL=tiny before loading the service so test completes quickly
and guarantees non-empty output (sample mp4 transcribed as len>=3 text "You" on tiny).

Run:
  cd backend
  ..\.venv\Scripts\python.exe verify_m9_direct.py
"""
import os, sys, time, json, uuid, shutil, threading, urllib.request, urllib.parse, urllib.error

os.environ["WHISPER_MODEL"] = "tiny"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()

from app.utils.security import hash_password
from app.database import SessionLocal
from app.models.models import User, Meeting, UserRole, MeetingStatus

TEST_PORT = 8769
BASE = f"http://127.0.0.1:{TEST_PORT}"

UPLOADS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
MANAGER_EMAIL = f"v9mgr_{uuid.uuid4().hex[:6]}@example.com"
MANAGER_PW    = "V9mgrPASS!23"
_created = {"manager_id": None, "meeting_id": None, "copied_file": None, "stored_path": None}


def start_uvicorn():
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=TEST_PORT, log_level="error")


def wait_server(to=30):
    dl = time.time()+to
    while time.time() < dl:
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=2) as r:
                if r.status == 200: return
        except Exception: time.sleep(0.3)
    raise RuntimeError("server not ready")


def http(method,path,body=None,headers=None,content_type=None):
    h = dict(headers or {})
    if content_type: h["Content-Type"] = content_type
    req = urllib.request.Request(BASE+path,data=body,method=method,headers=h)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, r.headers.get("Content-Type",""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type",""), e.read()


def login(email,pw):
    s,_,b = http("POST","/api/auth/login",
                 body=urllib.parse.urlencode({"username":email,"password":pw}).encode(),
                 content_type="application/x-www-form-urlencoded")
    assert s == 200, f"login {s}: {b.decode()[:600]}"
    return json.loads(b.decode())["access_token"]


def multipart(fields, files):
    boundary = "---V9" + uuid.uuid4().hex
    lines = []
    for k,v in fields.items():
        lines += [f"--{boundary}".encode(),
                  f'Content-Disposition: form-data; name="{k}"'.encode(), b"", v.encode()]
    for k,fn,ct,data in files:
        lines += [f"--{boundary}".encode(),
                  f'Content-Disposition: form-data; name="{k}"; filename="{fn}"'.encode(),
                  f"Content-Type: {ct}".encode(), b"", data]
    lines += [f"--{boundary}--".encode(), b""]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"


def find_sample_mp4():
    for fn in sorted(os.listdir(UPLOADS)):
        if fn.lower().endswith(".mp4") and os.path.getsize(os.path.join(UPLOADS,fn)) > 1_000_000:
            return os.path.join(UPLOADS, fn)
    return None


def main():
    # 0) Prep: find existing large mp4, copy to temp (name unique) to upload
    sample = find_sample_mp4()
    if not sample:
        print("FAIL: no existing ~5MB mp4 in uploads/ to copy as test input.")
        return 1
    tmp_src = os.path.join(UPLOADS, f"_v9src_{uuid.uuid4().hex}.mp4")
    shutil.copy2(sample, tmp_src)
    _created["copied_file"] = tmp_src
    with open(tmp_src, "rb") as f: mp4_bytes = f.read()
    print(f"[prep] copied sample mp4 -> {os.path.basename(tmp_src)} ({len(mp4_bytes)} bytes)")

    # 1) Create temp manager
    db = SessionLocal()
    try:
        u = User(email=MANAGER_EMAIL, first_name="V9", last_name="Mgr",
                 hashed_password=hash_password(MANAGER_PW),
                 role=UserRole.MANAGER, is_active=True)
        db.add(u); db.commit(); db.refresh(u)
        _created["manager_id"] = u.id
        print(f"[db] temp manager id={u.id} email={MANAGER_EMAIL}")
    finally: db.close()

    # 2) Start server
    threading.Thread(target=start_uvicorn, daemon=True).start()
    wait_server()

    tok = login(MANAGER_EMAIL, MANAGER_PW)
    auth = {"Authorization": f"Bearer {tok}"}

    # 3) Upload via HTTP (Rule-AC-10: regression test for M8 upload)
    print("\n=== VERIFY 0: Upload regression ===")
    body, ct = multipart({"title":"M9 Crown Jewel Meeting","description":"Direct verify real Whisper transcription end to end."},
                         [("recording", "m9_crownjewel.mp4", "video/mp4", mp4_bytes)])
    s,_,rb = http("POST","/api/meetings", body=body, headers=auth, content_type=ct)
    print(f"POST /meetings -> HTTP {s}")
    assert s == 201, f"upload {s}: {rb.decode()[:600]}"
    up = json.loads(rb.decode())
    _created["meeting_id"] = up["id"]
    print(f"   uploaded id={up['id']} status={up['status']!r} file_size={up['file_size']} recording_path_in_body? {'recording_path' in up}")
    assert up["status"] == "uploaded"
    assert "recording_path" not in up

    # Grab stored recording_path DIRECTLY from DB for file tests later
    db = SessionLocal()
    try:
        row = db.query(Meeting).filter(Meeting.id == up["id"]).first()
        assert row, "uploaded row missing in DB"
        _created["stored_path"] = row.recording_path
        print(f"   stored_path basename = {os.path.basename(row.recording_path)}  exists? {os.path.isfile(row.recording_path)}")
    finally: db.close()

    # 4) Transcribe! Rule-TR-6.1
    print("\n=== VERIFY 1: POST transcribe (REAL WHISPER) ===")
    t0 = time.time()
    s,_,rb = http("POST",f"/api/meetings/{up['id']}/transcribe", headers=auth)
    dt = time.time() - t0
    print(f"POST /meetings/{up['id']}/transcribe -> HTTP {s}  (wall {dt:.1f}s)")
    assert s == 200, f"transcribe {s}: {rb.decode()[:800]}"
    r1 = json.loads(rb.decode())
    transcript1 = r1.get("transcript") or ""
    print(f"   status        = {r1.get('status')!r}")
    print(f"   transcript len = {len(transcript1)}")
    print(f"   transcript[:300] = {transcript1[:300]!r}")
    print(f"   recording_path in body? {'recording_path' in r1}")
    assert r1.get("status") == "completed", f"expected completed got {r1.get('status')!r}"
    assert len(transcript1) > 0, "FAIL: transcript is empty — Whisper did not transcribe real audio, or wrong audio."
    assert "recording_path" not in r1
    print("   -> VERIFY 1 PASS: HTTP 200, non-empty transcript, no path leak.")

    # 5) TR-6.2 PostgreSQL direct query: same transcript, status COMPLETED
    print("\n=== VERIFY 2: PostgreSQL direct query ===")
    db = SessionLocal()
    try:
        row = db.query(Meeting).filter(Meeting.id == up["id"]).first()
        assert row.transcript is not None
        assert len(row.transcript) > 0
        print(f"   DB transcript len={len(row.transcript)}  status={row.status}")
        print(f"   DB transcript[:200]={row.transcript[:200]!r}")
        assert row.status == MeetingStatus.COMPLETED, f"DB status expected COMPLETED got {row.status}"
        assert row.transcript == transcript1, "DB transcript != HTTP response transcript"
    finally: db.close()
    print("   -> VERIFY 2 PASS: DB row correct, byte-identical to HTTP transcript.")

    # 6) TR-6.3 GET /{id}
    print("\n=== VERIFY 3: GET /api/meetings/{id} detail ===")
    s,_,rb = http("GET", f"/api/meetings/{up['id']}", headers=auth)
    assert s == 200, f"GET detail {s}: {rb.decode()[:400]}"
    gd = json.loads(rb.decode())
    got_t = gd.get("transcript") or ""
    body_str = rb.decode()
    stored_abs = _created["stored_path"]
    # Even a substring of the stored path shouldn't accidentally appear
    leak_path = stored_abs in body_str
    print(f"   GET transcript len={len(got_t)}  matches HTTP transcribe transcript? {got_t == transcript1}")
    print(f"   Absolute stored path ({stored_abs!r}) anywhere in GET response body? {leak_path}")
    assert got_t == transcript1, "GET transcript mismatch"
    assert not leak_path, "recording_path absolute path LEAKED in response!"
    print("   -> VERIFY 3 PASS: GET correct; recording_path NOT leaked.")

    # 7) TR-6.5 Idempotency: second transcribe call -> identical
    print("\n=== VERIFY 4: Idempotency (second transcribe call) ===")
    # Count actual service transcribe calls via singleton
    from app.services.transcription_service import get_transcription_service
    svc_before = get_transcription_service()
    calls_before = svc_before.transcribe_call_count
    s,_,rb2 = http("POST",f"/api/meetings/{up['id']}/transcribe", headers=auth)
    print(f"   second call HTTP {s}")
    assert s == 200, f"2nd transcribe {s}: {rb2.decode()[:400]}"
    r2 = json.loads(rb2.decode())
    transcript2 = r2.get("transcript") or ""
    svc_after = get_transcription_service()
    calls_after = svc_after.transcribe_call_count
    print(f"   1st transcript len={len(transcript1)} 2nd len={len(transcript2)} equal? {transcript1 == transcript2}")
    print(f"   service transcribe() call count before= {calls_before}  after={calls_after}")
    assert transcript1 == transcript2, "Transcript changed on 2nd call (not byte identical)!"
    assert calls_after == calls_before, f"Idempotency violated: service re-ran Whisper ({calls_before} -> {calls_after}) on COMPLETED meeting."
    print("   -> VERIFY 4 PASS: byte-identical transcript; Whisper NOT re-run.")

    # 8) TR-6.4 Missing recording file -> HTTP 400, status becomes FAILED, safe message
    print("\n=== VERIFY 5: Missing on-disk recording file -> HTTP 400 ===")
    # First create a NEW uploaded meeting (status=uploaded) then rename its file
    body2, ct2 = multipart({"title":"M9 missing file test"},
                           [("recording","m9_shouldvanish.mp4","video/mp4", mp4_bytes)])
    s,_,rb = http("POST","/api/meetings", body=body2, headers=auth, content_type=ct2)
    assert s == 201, f"2nd upload {s}: {rb.decode()[:400]}"
    m2 = json.loads(rb.decode())
    db = SessionLocal()
    try:
        row2 = db.query(Meeting).filter(Meeting.id == m2["id"]).first()
        vanish_path = row2.recording_path
    finally: db.close()
    bak = vanish_path + ".m9bak"
    try:
        shutil.move(vanish_path, bak)
        print(f"   moved stored file to bak ({os.path.basename(bak)})")
        s,_,rb = http("POST", f"/api/meetings/{m2['id']}/transcribe", headers=auth)
        print(f"   POST transcribe with missing file -> HTTP {s}")
        assert s == 400, f"Expected 400 got {s}: {rb.decode()[:400]}"
        body_msg = rb.decode()
        has_path_in_msg = os.path.basename(vanish_path) in body_msg or vanish_path in body_msg or os.path.dirname(vanish_path) in body_msg
        print(f"   body: {body_msg[:400]!r}")
        print(f"   contains filesystem path? {has_path_in_msg}")
        assert "Recording file not found on server." in body_msg, "Wrong public error message"
        # Status in DB FAILED?
        db = SessionLocal()
        try:
            row2 = db.query(Meeting).filter(Meeting.id == m2["id"]).first()
            print(f"   DB status after missing-file call: {row2.status}")
            assert row2.status == MeetingStatus.FAILED, f"Expected FAILED status after file-missing transcribe, got {row2.status}"
        finally: db.close()
        print("   -> VERIFY 5 PASS: HTTP 400 with safe message; DB status=FAILED.")
    finally:
        # Cleanup the temp meeting + restore so cleanup step can remove file
        if os.path.isfile(bak):
            if os.path.isfile(vanish_path): os.remove(vanish_path)
            shutil.move(bak, vanish_path)
        db = SessionLocal()
        try:
            row2 = db.query(Meeting).filter(Meeting.id == m2["id"]).first()
            if row2 and os.path.isfile(row2.recording_path):
                try: os.remove(row2.recording_path)
                except OSError: pass
            db.query(Meeting).filter(Meeting.id == m2["id"]).delete()
            db.commit()
        finally: db.close()

    print("\n" + "="*80)
    print("MILESTONE 9 — ALL 5 CROWN JEWEL VERIFICATIONS PASSED")
    print("="*80)
    return 0


def cleanup():
    print("\n[cleanup]:")
    if _created["meeting_id"]:
        db = SessionLocal()
        try:
            row = db.query(Meeting).filter(Meeting.id == _created["meeting_id"]).first()
            if row and row.recording_path and os.path.isfile(row.recording_path):
                try: os.remove(row.recording_path); print(f"  - removed stored file {os.path.basename(row.recording_path)}")
                except OSError: pass
            db.query(Meeting).filter(Meeting.id == _created["meeting_id"]).delete()
            db.commit()
            print(f"  - deleted meeting id={_created['meeting_id']}")
        finally: db.close()
    if _created["manager_id"]:
        db = SessionLocal()
        try:
            db.query(User).filter(User.id == _created["manager_id"]).delete()
            db.commit()
            print(f"  - deleted temp manager id={_created['manager_id']}")
        finally: db.close()
    if _created["copied_file"] and os.path.isfile(_created["copied_file"]):
        try: os.remove(_created["copied_file"]); print(f"  - removed copied sample {os.path.basename(_created['copied_file'])}")
        except OSError: pass


if __name__ == "__main__":
    try: code = main()
    finally: cleanup()
    sys.exit(code)
