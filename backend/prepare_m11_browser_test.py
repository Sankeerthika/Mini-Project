import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text
from app.models.models import User, UserRole
from app.utils.security import hash_password

def ensure_user(email, fname, lname, role, pw):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email, first_name=fname, last_name=lname,
                role=role, is_active=True,
                hashed_password=hash_password(pw),
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            print(f"[CREATED] {email} / {pw} | role={role.value} | id={u.id}")
        else:
            print(f"[EXISTS] {email} | role={u.role.value} | id={u.id} | active={u.is_active}")
            if not u.is_active:
                u.is_active = True
                db.commit()
                print("  -> reactivated")
        return u
    finally:
        db.close()

print("=== Ensuring test users ===")
m1 = ensure_user("manager_a@example.com", "TestA", "Manager", UserRole.MANAGER, "Test1234!")
m2 = ensure_user("manager_b@example.com", "TestB", "Manager", UserRole.MANAGER, "Test1234!")
e1 = ensure_user("emp_c@example.com", "EmpC", "Worker", UserRole.EMPLOYEE, "Test1234!")
e2 = ensure_user("emp_d@example.com", "EmpD", "Worker", UserRole.EMPLOYEE, "Test1234!")
ad = ensure_user("admin_x@example.com", "Super", "Admin", UserRole.ADMIN, "Test1234!")

# Inject an analyzed meeting for manager_a
db = SessionLocal()
try:
    from app.models.models import Meeting, MeetingStatus
    existing = db.query(Meeting).filter(Meeting.created_by_id == m1.id, Meeting.title == "M11 Browser E2E Test Meeting").first()
    if existing:
        mid = existing.id
        print(f"\n[EXISTS] Meeting 'M11 Browser E2E Test Meeting' id={mid}")
    else:
        import uuid
        fname = f"{uuid.uuid4().hex}.wav"
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        fpath = os.path.join(uploads_dir, fname)
        with open(fpath, "wb") as f:
            f.write(b"RIFF" + b"\x00" * 44)
        m = Meeting(
            title="M11 Browser E2E Test Meeting",
            description="Pre-injected for browser M11 testing",
            recording_path=f"uploads/{fname}",
            original_filename="e2e-meeting.wav",
            file_size=48,
            content_type="audio/wav",
            created_by_id=m1.id,
            status=MeetingStatus.COMPLETED,
            transcript=(
                "Welcome everyone. Today we reviewed Q3 progress and set Q4 targets. "
                "Key decisions: approved the new marketing budget. "
                "Action items: 1) EmpC will prepare weekly status report by Friday. "
                "2) EmpD to draft Q4 financial plan by 2026-10-30. "
                "3) Send customer satisfaction survey to clients."
            ),
            summary="Reviewed Q3 progress, approved marketing budget, set Q4 targets.",
            key_decisions="1) Approve revised marketing budget of $500k.\n2) Move Q4 launch date to 2026-10-30.",
            action_items_json=__import__('json').dumps([
                {"task": "Prepare weekly project status report", "person": "EmpC", "deadline": "Friday"},
                {"task": "Draft Q4 financial plan", "person": "EmpD", "deadline": "2026-10-30"},
                {"task": "Send customer satisfaction survey to all clients", "person": "", "deadline": None},
            ]),
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        mid = m.id
        print(f"\n[CREATED] Meeting 'M11 Browser E2E Test Meeting' id={mid} for manager id={m1.id}")

    # Check for existing tasks associated
    from app.models.models import Task
    tcount = db.query(Task).filter(Task.created_by == m1.id).count()
    print(f"[INFO] Manager_A task count before test: {tcount}")
    e1count = db.query(Task).filter(Task.assigned_to == e1.id).count()
    print(f"[INFO] EmpC (id={e1.id}) assigned task count before test: {e1count}")
finally:
    db.close()

print("\n=== Done. Browser E2E test data ready. ===")
