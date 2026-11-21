import sys
import os
import uuid
import tempfile
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.database import SessionLocal
from app.models.models import User, UserRole, Meeting, Task, MeetingStatus
from app.utils.security import hash_password

client = TestClient(app)

TMP_DIR = tempfile.mkdtemp()


def _make_dummy_audio(path):
    with open(path, "wb") as f:
        f.write(b"RIFF" + b"\x00" * 44)


def ensure_users(db):
    users = {
        "m1": {"email": "manager_m11_a@example.com", "fname": "M11A", "lname": "Manager", "role": UserRole.MANAGER, "pw": "Test1234!"},
        "m2": {"email": "manager_m11_b@example.com", "fname": "M11B", "lname": "Manager", "role": UserRole.MANAGER, "pw": "Test1234!"},
        "e1": {"email": "employee_m11@example.com", "fname": "M11E", "lname": "Employee", "role": UserRole.EMPLOYEE, "pw": "Test1234!"},
        "e2": {"email": "employee_m11_2@example.com", "fname": "M11F", "lname": "Employee", "role": UserRole.EMPLOYEE, "pw": "Test1234!"},
        "ad": {"email": "admin_m11@example.com", "fname": "M11G", "lname": "Admin", "role": UserRole.ADMIN, "pw": "Test1234!"},
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
        created[key] = {"id": u.id, "email": u.email, "role": u.role}
    return created


def login(email, pw):
    r = client.post("/api/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def upload_meeting(token, title, transcript_to_inject=None, analysis_to_inject=None):
    path = os.path.join(TMP_DIR, f"dummy_{uuid.uuid4().hex}.wav")
    _make_dummy_audio(path)
    with open(path, "rb") as f:
        files = {"recording": ("dummy.wav", f, "audio/wav")}
        data = {"title": title}
        r = client.post("/api/meetings", headers=auth_header(token), data=data, files=files)
    assert r.status_code == 201, f"Upload meeting failed: {r.status_code} {r.text}"
    meeting_id = r.json()["id"]
    if transcript_to_inject is not None or analysis_to_inject is not None:
        db = SessionLocal()
        try:
            m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if transcript_to_inject is not None:
                m.transcript = transcript_to_inject
            if analysis_to_inject:
                m.summary = analysis_to_inject.get("summary", m.summary)
                m.key_decisions = analysis_to_inject.get("key_decisions", m.key_decisions)
                m.action_items_json = analysis_to_inject.get("action_items_json", m.action_items_json)
            if transcript_to_inject is not None:
                m.status = MeetingStatus.COMPLETED
            db.commit()
        finally:
            db.close()
    return meeting_id


def cleanup_db():
    db = SessionLocal()
    try:
        emails = [
            "manager_m11_a@example.com", "manager_m11_b@example.com",
            "employee_m11@example.com", "employee_m11_2@example.com",
            "admin_m11@example.com",
        ]
        users = db.query(User).filter(User.email.in_(emails)).all()
        uids = [u.id for u in users]
        if uids:
            db.query(Task).filter(
                (Task.created_by.in_(uids)) | (Task.assigned_to.in_(uids))
            ).delete(synchronize_session=False)
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
    created_tasks = []

    def record(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append((name, status, detail))
        print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

    try:
        cleanup_db()

        db = SessionLocal()
        users = ensure_users(db)
        db.close()

        m1_token = login("manager_m11_a@example.com", "Test1234!")
        m2_token = login("manager_m11_b@example.com", "Test1234!")
        e1_token = login("employee_m11@example.com", "Test1234!")
        e2_token = login("employee_m11_2@example.com", "Test1234!")
        ad_token = login("admin_m11@example.com", "Test1234!")

        sample_analysis = {
            "summary": "Reviewed Q3 progress and set Q4 targets.",
            "key_decisions": "Approved the new marketing budget.",
            "action_items_json": json.dumps([
                {"task": "Prepare weekly project status report", "person": "Charlie", "deadline": "Friday"},
                {"task": "Draft Q4 financial plan", "person": "Dana", "deadline": "2026-10-30"},
                {"task": "Send customer satisfaction survey", "person": "", "deadline": None},
            ]),
        }

        mid = upload_meeting(
            m1_token,
            "M11 Test Meeting",
            transcript_to_inject="Reviewed Q3 progress and set Q4 targets.",
            analysis_to_inject=sample_analysis,
        )

        # ========== MANAGER / EMPLOYEES ROUTES ==========

        # T1: GET /api/manager/employees returns active employees
        r = client.get("/api/manager/employees", headers=auth_header(m1_token))
        record("T1. Manager list employees (200)", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            employees = r.json()
            record("T1b. Employee list is array of users", isinstance(employees, list) and len(employees) >= 2,
                   f"len={len(employees) if isinstance(employees, list) else 'n/a'}")
            only_employees = all(u.get("role") in {None, "employee"} or (isinstance(u, dict) and "role" not in u and "email" in u) for u in employees)
            record("T1c. Only employees returned (no admins)", only_employees,
                   f"sample={[{k: v for k, v in list(u.items())[:3] if k in ('id','email','role')} for u in employees[:2]]}")

        # T2: Admin cannot be picked from the employee list
        r2_emp = client.get("/api/manager/employees", headers=auth_header(m1_token))
        if r2_emp.status_code == 200:
            admin_in_list = any(u.get("email") == "admin_m11@example.com" for u in r2_emp.json())
            record("T2. Admin NOT in employee list", not admin_in_list,
                   f"admin_in_list={admin_in_list}")
        else:
            record("T2. Admin NOT in employee list", False, f"employees api failed: {r2_emp.status_code}")

        # T3: Employee cannot call /manager/employees
        r_e = client.get("/api/manager/employees", headers=auth_header(e1_token))
        record("T3. Employee cannot list manager employees", r_e.status_code in {401, 403, 404},
               f"status={r_e.status_code}")

        # ========== POST /api/manager/tasks ==========

        e1_id = users["e1"]["id"]
        e2_id = users["e2"]["id"]
        ad_id = users["ad"]["id"]

        # T4: Manager successfully creates task from meeting action item (with employee)
        payload = {
            "title": "Prepare weekly project status report",
            "description": "Weekly status for M11 test meeting",
            "priority": "medium",
            "deadline": "2026-10-10",
            "assigned_to": str(e1_id),
            "meeting_id": mid,
        }
        r = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=payload)
        record("T4. Manager creates task assigned to employee (201)", r.status_code == 201,
               f"status={r.status_code}, text={r.text[:200]}")
        task = None
        if r.status_code == 201:
            task = r.json()
            created_tasks.append(task["id"])
            record("T4b. Task response has assigned_to matching e1_id",
                   str(task.get("assigned_to")) == str(e1_id),
                   f"got {task.get('assigned_to')}, expected {e1_id}")
            record("T4c. Task response has meeting_id matching mid",
                   int(task.get("meeting_id") or 0) == int(mid),
                   f"got {task.get('meeting_id')}, expected {mid}")
            record("T4d. Task response has title, priority, deadline",
                   bool(task.get("title")) and bool(task.get("priority")) and bool(task.get("deadline")),
                   f"title={bool(task.get('title'))}, priority={bool(task.get('priority'))}, deadline={bool(task.get('deadline'))}")
            record("T4e. Task has status = pending by default",
                   task.get("status") == "pending",
                   f"status={task.get('status')}")
            record("T4f. Task created_by set",
                   bool(task.get("created_by")) or ("created_by_id" in task),
                   f"created_by={task.get('created_by')}, created_by_id={task.get('created_by_id')}")

        # T5: Missing assigned_to returns validation error
        payload_miss = {"title": "Task missing assignee", "assigned_to": "", "meeting_id": mid}
        r5 = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=payload_miss)
        record("T5. Missing assigned_to rejected (4xx)", 400 <= r5.status_code < 500,
               f"status={r5.status_code}")

        # T6: Empty title rejected
        payload_empty_title = {"title": "", "assigned_to": str(e1_id), "meeting_id": mid}
        r6 = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=payload_empty_title)
        record("T6. Empty title rejected (4xx)", 400 <= r6.status_code < 500,
               f"status={r6.status_code}")

        # T7: Assigning admin as assignee rejected
        payload_admin_ass = {
            "title": "Task assigned to admin",
            "assigned_to": str(ad_id),
            "meeting_id": mid,
        }
        r7 = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=payload_admin_ass)
        record("T7. Cannot assign admin as assignee (4xx)", 400 <= r7.status_code < 500,
               f"status={r7.status_code}, text={r7.text[:200]}")

        # T8: Cannot create task for another manager's meeting
        mid_m2 = upload_meeting(m2_token, "M11 M2 Meeting",
                                transcript_to_inject="M2's transcript",
                                analysis_to_inject=sample_analysis)
        payload_cross = {
            "title": "Wrong owner task",
            "assigned_to": str(e1_id),
            "meeting_id": mid_m2,
        }
        r8 = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=payload_cross)
        record("T8. Manager cannot create task for another manager's meeting",
               400 <= r8.status_code < 500,
               f"status={r8.status_code}")

        # T9: Employee cannot create manager tasks
        r9 = client.post("/api/manager/tasks", headers=auth_header(e1_token), json={
            "title": "Employee attempt",
            "assigned_to": str(e1_id),
            "meeting_id": mid,
        })
        record("T9. Employee cannot create manager tasks",
               r9.status_code in {401, 403, 404},
               f"status={r9.status_code}")

        # T10: Create second task for same meeting / employee
        payload_t10 = {
            "title": "Draft Q4 financial plan",
            "priority": "high",
            "deadline": "2026-10-30",
            "assigned_to": str(e2_id),
            "meeting_id": mid,
        }
        r10 = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=payload_t10)
        record("T10. Manager creates second task (201)", r10.status_code == 201,
               f"status={r10.status_code}")
        if r10.status_code == 201:
            created_tasks.append(r10.json()["id"])

        # T10b: Task without meeting_id (standalone) accepted
        payload_nomeeting = {
            "title": "Standalone task no meeting",
            "assigned_to": str(e1_id),
            "priority": "low",
        }
        r10b = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=payload_nomeeting)
        record("T10b. Manager creates standalone task without meeting (201)",
               r10b.status_code == 201,
               f"status={r10b.status_code}")
        if r10b.status_code == 201:
            created_tasks.append(r10b.json()["id"])

        # ========== GET /api/manager/tasks ==========

        # T11: Manager tasks list shows the tasks we created
        r11 = client.get("/api/manager/tasks", headers=auth_header(m1_token))
        record("T11. GET /api/manager/tasks returns 200", r11.status_code == 200,
               f"status={r11.status_code}")
        if r11.status_code == 200:
            tasks = r11.json()
            record("T11b. Manager tasks count >= 3",
                   isinstance(tasks, list) and len(tasks) >= len(created_tasks),
                   f"len={len(tasks) if isinstance(tasks, list) else 'n/a'}; created_ids={created_tasks}")
            all_my = all(int(t.get("created_by") or t.get("created_by_id") or 0) == int(users["m1"]["id"]) for t in tasks)
            record("T11c. All listed tasks are created_by current manager", all_my,
                   f"sample creators={[t.get('created_by_id') or t.get('created_by') for t in tasks[:5]]}")

        # T12: GET /api/manager/tasks?meeting_id=mid filter works
        r12 = client.get(f"/api/manager/tasks?meeting_id={mid}", headers=auth_header(m1_token))
        record("T12. Manager tasks filter by meeting_id works",
               r12.status_code == 200 and (isinstance(r12.json(), list) and len(r12.json()) >= 2),
               f"status={r12.status_code}, len={len(r12.json()) if r12.status_code == 200 else 'n/a'}")

        # T13: GET /api/manager/tasks?assigned_to=e1_id filter works
        r13 = client.get(f"/api/manager/tasks?assigned_to={e1_id}", headers=auth_header(m1_token))
        record("T13. Manager tasks filter by assigned_to works",
               r13.status_code == 200 and isinstance(r13.json(), list) and len(r13.json()) >= 2,
               f"status={r13.status_code}, len={len(r13.json()) if r13.status_code == 200 else 'n/a'}")

        # T14: Second manager cannot see first manager's tasks
        r14 = client.get("/api/manager/tasks", headers=auth_header(m2_token))
        record("T14. Second manager cannot see first manager's tasks",
               r14.status_code == 200 and (not any(int(t.get("id") or 0) in created_tasks for t in r14.json())),
               f"status={r14.status_code}; first_task_ids_in_m2_list={[t.get('id') for t in r14.json() if int(t.get('id') or 0) in created_tasks]}")

        # T15: Employee cannot list manager tasks
        r15 = client.get("/api/manager/tasks", headers=auth_header(e1_token))
        record("T15. Employee cannot list /manager/tasks",
               r15.status_code in {401, 403, 404}, f"status={r15.status_code}")

        # ========== MANAGER STATISTICS ==========

        r16 = client.get("/api/manager/statistics", headers=auth_header(m1_token))
        record("T16. Manager statistics (200) includes task counts",
               r16.status_code == 200,
               f"status={r16.status_code}")
        if r16.status_code == 200:
            st = r16.json()
            record("T16b. Manager stats total_tasks >= 3",
                   int(st.get("total_tasks") or 0) >= 3,
                   f"total_tasks={st.get('total_tasks')}")
            record("T16c. Manager stats pending_tasks present",
                   "pending_tasks" in st, f"keys={list(st.keys())}")

        # ========== EMPLOYEE TASK APIS ==========

        # T17: Employee list own tasks shows assigned tasks
        r17 = client.get("/api/employee/tasks", headers=auth_header(e1_token))
        record("T17. Employee list own tasks (200)",
               r17.status_code == 200, f"status={r17.status_code}")
        if r17.status_code == 200:
            emp_tasks = r17.json()
            record("T17b. Employee's list contains tasks assigned to them",
                   isinstance(emp_tasks, list) and len(emp_tasks) >= 2,
                   f"len={len(emp_tasks)}; assigned_to_ids={[t.get('assigned_to') for t in emp_tasks[:5]]}")

        # T18: Employee cannot see tasks assigned to other employees
        r18 = client.get("/api/employee/tasks", headers=auth_header(e2_token))
        record("T18. Second employee sees only their own tasks",
               r18.status_code == 200 and isinstance(r18.json(), list) and all(int(t.get("assigned_to") or 0) == int(e2_id) for t in r18.json()),
               f"status={r18.status_code}, len={len(r18.json()) if r18.status_code == 200 else 'n/a'}")

        # T19: Employee updates task status to in_progress
        first_emp_task_id = None
        if r17.status_code == 200 and isinstance(r17.json(), list) and len(r17.json()) > 0:
            first_emp_task_id = r17.json()[0]["id"]
        r19 = client.patch(f"/api/employee/tasks/{first_emp_task_id}", headers=auth_header(e1_token),
                           json={"status": "in_progress"})
        record("T19. Employee updates task status to in_progress (200)",
               r19.status_code == 200 and r19.json().get("status") == "in_progress",
               f"status={r19.status_code}, result_status={r19.json().get('status') if r19.status_code == 200 else 'n/a'}")

        # T20: Employee sets task to completed
        r20 = client.patch(f"/api/employee/tasks/{first_emp_task_id}", headers=auth_header(e1_token),
                           json={"status": "completed"})
        record("T20. Employee updates task status to completed (200)",
               r20.status_code == 200 and r20.json().get("status") == "completed",
               f"status={r20.status_code}")
        if r20.status_code == 200:
            record("T20b. completed_at field set after COMPLETED status",
                   bool(r20.json().get("completed_at")),
                   f"completed_at={r20.json().get('completed_at')}")

        # T21: Employee cannot update another employee's task
        r21 = client.patch(f"/api/employee/tasks/{first_emp_task_id}", headers=auth_header(e2_token),
                           json={"status": "pending"})
        record("T21. Second employee cannot update first's task (4xx)",
               400 <= r21.status_code < 500,
               f"status={r21.status_code}")

        # T22: Employee cannot change assigned_to
        r22 = client.patch(f"/api/employee/tasks/{first_emp_task_id}", headers=auth_header(e1_token),
                           json={"assigned_to": str(e2_id)})
        record("T22. Employee cannot reassign task (whitelist enforced)",
               r22.status_code in {200, 400, 422} and (
                   (r22.status_code == 200 and int(r22.json().get("assigned_to") or 0) == int(e1_id))
                   or 400 <= r22.status_code
               ),
               f"status={r22.status_code}")

        # ========== EMPLOYEE STATISTICS ==========

        r23 = client.get("/api/employee/statistics", headers=auth_header(e1_token))
        record("T23. Employee statistics (200)",
               r23.status_code == 200, f"status={r23.status_code}")
        if r23.status_code == 200:
            st = r23.json()
            record("T23b. Employee stats includes total_tasks",
                   "total_tasks" in st, f"keys={list(st.keys())}")
            record("T23c. Employee stats total_tasks >= 2",
                   int(st.get("total_tasks") or 0) >= 2,
                   f"total_tasks={st.get('total_tasks')}")

        # ========== ADMIN STATISTICS ==========

        r24 = client.get("/api/admin/statistics", headers=auth_header(ad_token))
        record("T24. Admin statistics (200)",
               r24.status_code == 200, f"status={r24.status_code}")
        if r24.status_code == 200:
            st = r24.json()
            record("T24b. Admin stats includes total_tasks",
                   "total_tasks" in st, f"keys={list(st.keys())}")

        # ========== DEADLINE / OVERDUE ==========

        past_payload = {
            "title": "Overdue task test",
            "assigned_to": str(e1_id),
            "deadline": "2000-01-01",
            "priority": "high",
        }
        r25 = client.post("/api/manager/tasks", headers=auth_header(m1_token), json=past_payload)
        record("T25. Create task with past deadline (201)",
               r25.status_code == 201, f"status={r25.status_code}")

        # ========== UNAUTHENTICATED ==========

        r26 = client.post("/api/manager/tasks", json={"title": "x", "assigned_to": str(e1_id)})
        record("T26. Unauthenticated request to /manager/tasks returns 401",
               r26.status_code == 401, f"status={r26.status_code}")

        r27 = client.get("/api/manager/employees")
        record("T27. Unauthenticated /manager/employees = 401",
               r27.status_code == 401, f"status={r27.status_code}")

        # ========== DB INTEGRITY CHECK ==========

        db = SessionLocal()
        try:
            tcount = db.query(Task).filter(Task.id.in_(created_tasks)).count()
            record("T28. Tasks actually exist in DB", tcount == len(created_tasks),
                   f"expected={len(created_tasks)}, got={tcount}")

            m1_owned_by = db.query(Meeting.created_by_id).filter(Meeting.id == mid).scalar()
            record("T29. Meeting ownership preserved (no tampering by task creation)",
                   int(m1_owned_by or 0) == int(users["m1"]["id"]),
                   f"meeting.created_by_id={m1_owned_by}, expected={users['m1']['id']}")
        finally:
            db.close()

    except Exception as exc:
        record("TEST EXCEPTION", False, str(exc))
        import traceback
        traceback.print_exc()

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
