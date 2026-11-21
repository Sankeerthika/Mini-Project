"""Test: verify SQLAlchemy can insert a Meeting row with the enum and
all 4 new columns. Uses a DB transaction that ROLLBACKS at end so no
data is actually persisted; only validates type compatibility."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.models import Meeting, MeetingStatus, User
from app.utils.security import hash_password
from datetime import datetime

print("=" * 80)
print("ENROLL / MEETING INSERT TEST")
print("MeetingStatus.UPLOADED = {!r}  (Python value)".format(MeetingStatus.UPLOADED.value))
print("=" * 80)

db = SessionLocal()
try:
    # Ensure at least one user exists for FK constraint (rollback-safe)
    u = db.query(User).first()
    if u is None:
        u = User(
            email="migration_test_mgr_invalid@example.invalid",
            first_name="MigTest",
            last_name="MigTest",
            hashed_password=hash_password("Testpass1!"),
            role="manager",
            is_active=True,
        )
        db.add(u)
        db.flush()
        print("\nCreated throwaway manager user (will be rolled back): id={}".format(u.id))
    else:
        print("\nReusing existing user id={} role={} for FK".format(u.id, u.role))

    mid = u.id

    # Try to build + flush a Meeting with new columns, using UPLOADED enum
    m = Meeting(
        title="Migration test meeting — ROLLBACK",
        description="test via migration script",
        original_filename="test_upload.mp3",
        recording_path="/tmp/nonexistent_test.mp3",
        content_type="audio/mpeg",
        file_size=12345,
        status=MeetingStatus.UPLOADED,
        meeting_date=datetime.utcnow(),
        created_by_id=mid,
    )
    db.add(m)
    db.flush()
    print("\nMeeting flushed successfully! id={} status={!r}".format(m.id, m.status.value))
    print("All 15 columns mapped without error:")
    cols = ["id","title","description","original_filename","recording_path",
            "content_type","file_size","status","transcript","summary",
            "key_decisions","meeting_date","created_by_id","created_at","updated_at"]
    for c in cols:
        v = getattr(m, c)
        if c in ("recording_path",):
            print("   {:<20}= <hidden internal path>".format(c))
        else:
            preview = str(v)[:80] if v is not None else "NULL"
            print("   {:<20}= {}".format(c, preview))

    print("\nDB insert accepted with current enum mapping. ROLLBACK.")
    db.rollback()
    print("Rollback OK — no test data persisted. Safe to run upload tests.")
    sys.exit(0)
except Exception as e:
    db.rollback()
    print("\nDB FLUSH FAILED!")
    print("{}: {}".format(type(e).__name__, e))
    print("\nROLLBACK.")
    sys.exit(1)
finally:
    db.close()
