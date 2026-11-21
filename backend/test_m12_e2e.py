import sys
import os
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.models import User, UserRole, Meeting, Task, TaskStatus, Priority, MeetingStatus
from app.utils.security import hash_password

client = TestClient(app)

MANAGER_A = {"email": "mgr_m12_a@example.com", "pw": "Test1234!", "fname": "M12A", "lname": "Mgr"}
MANAGER_B = {"email": "mgr_m12_b@example.com", "pw": "Test1234!", "fname": "M12B", "lname": "Mgr"}
EMPLOYEE_A = {"email": "emp_m12_a@example.com", "pw": "Test1234!", "fname": "M12A", "lname": "Emp"}
EMPLOYEE_B = {"email": "emp_m12_b@example.com", "pw": "Test1234!", "fname": "M12B", "lname": "Emp"}

ALL_EMAILS = [v["email"] for v in (MANAGER_A, MANAGER_B, EMPLOYEE_A, EMPLOYEE_B)]


def ensure_users(db):
    created = {}
    for key, spec in (
        ("ma", MANAGER_A),
        ("mb", MANAGER_B),
        ("ea", EMPLOYEE_A),
        ("eb", EMPLOYEE_B),
    ):
        u = db.query(User).filter(User.email == spec["email"]).first()
        if not u:
            u = User(
                email=spec["email"],
                first_name=spec["fname"],
                last_name=spec["lname"],
                role={"ma": UserRole.MANAGER, "mb": UserRole.MANAGER, "ea": UserRole.EMPLOYEE, "eb": UserRole.EMPLOYEE}[key],
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
    assert r.status_code == 200, f"Login fail {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def cleanup():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.email.in_(ALL_EMAILS)).all()
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
        print(f"[CLEANUP WARN] {e}")
        db.rollback()
    finally:
        db.close()


def _check(name, condition, detail=""):
    mark = "PASS" if condition else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{mark}] {name}{extra}")
    return bool(condition)


def main():
    cleanup()
    db = SessionLocal()
    try:
        users = ensure_users(db)
        ma_id = users["ma"]["id"]
        mb_id = users["mb"]["id"]
        ea_id = users["ea"]["id"]
        eb_id = users["eb"]["id"]

        ma_tok = login(MANAGER_A["email"], MANAGER_A["pw"])
        mb_tok = login(MANAGER_B["email"], MANAGER_B["pw"])
        ea_tok = login(EMPLOYEE_A["email"], EMPLOYEE_A["pw"])
        eb_tok = login(EMPLOYEE_B["email"], EMPLOYEE_B["pw"])

        today = datetime.date.today()
        yest = today - datetime.timedelta(days=1)
        last_week = today - datetime.timedelta(days=7)
        tmrw = today + datetime.timedelta(days=1)
        next_week = today + datetime.timedelta(days=7)

        passed = 0
        total = 0

        def t(name, ok, detail=""):
            nonlocal passed, total
            total += 1
            if _check(name, ok, detail):
                passed += 1

        print("\n=== M12 Backend Tests ===")

        # --------- Manager creates a couple of tasks ---------
        r = client.post(
            "/api/manager/tasks",
            headers=auth(ma_tok),
            json={
                "title": "Prepare quarterly board deck",
                "description": "Assemble the slides for Q3 board meeting",
                "priority": "high",
                "deadline": tmrw.isoformat(),
                "assigned_to": ea_id,
            },
        )
        ok = r.status_code == 201
        t("T1. Create task A (201)", ok, f"status={r.status_code}")
        task_a = r.json() if ok else None

        r = client.post(
            "/api/manager/tasks",
            headers=auth(ma_tok),
            json={
                "title": "Draft release notes v2.1",
                "description": "Describe new task tracking features",
                "priority": "medium",
                "deadline": next_week.isoformat(),
                "assigned_to": eb_id,
            },
        )
        ok = r.status_code == 201
        t("T2. Create task B (201)", ok, f"status={r.status_code}")
        task_b = r.json() if ok else None

        # --------- Detail endpoint ---------
        r = client.get(f"/api/manager/tasks/{task_a['id']}", headers=auth(ma_tok))
        t("T3. Manager GET detail 200", r.status_code == 200, f"status={r.status_code}")
        t("T3b. Detail body has title", r.json().get("title") == task_a["title"])

        r = client.get(f"/api/manager/tasks/{task_a['id']}", headers=auth(mb_tok))
        t("T4. Cross-manager detail returns 404", r.status_code == 404, f"status={r.status_code}")

        # --------- Manager PATCH ---------
        r = client.patch(
            f"/api/manager/tasks/{task_a['id']}",
            headers=auth(ma_tok),
            json={"title": "Prepare quarterly board deck — Q3 FINAL", "priority": "high"},
        )
        ok = r.status_code == 200
        t("T5. Manager PATCH title/priority 200", ok, f"status={r.status_code}")
        if ok:
            t("T5b. Title updated", r.json().get("title") == "Prepare quarterly board deck — Q3 FINAL")
            t("T5c. Priority unchanged high", r.json().get("priority") == "high")

        r = client.patch(
            f"/api/manager/tasks/{task_a['id']}",
            headers=auth(ma_tok),
            json={"assigned_to": eb_id},
        )
        ok = r.status_code == 200
        t("T6. Manager reassign task A → B employee", ok, f"status={r.status_code}")
        if ok:
            t("T6b. assigned_to updated", r.json().get("assigned_to") == eb_id)

        r = client.patch(
            f"/api/manager/tasks/{task_a['id']}",
            headers=auth(ma_tok),
            json={"assigned_to": ma_id},
        )
        t("T7. PATCH invalid assignee (manager) → 400", r.status_code == 400, f"status={r.status_code}, text={r.text[:200]}")

        r = client.patch(
            f"/api/manager/tasks/{task_a['id']}",
            headers=auth(mb_tok),
            json={"priority": "low"},
        )
        t("T8. Cross-manager PATCH → 404", r.status_code == 404, f"status={r.status_code}")

        r = client.patch(
            f"/api/manager/tasks/{task_a['id']}",
            headers=auth(ma_tok),
            json={"title": ""},
        )
        t("T9. PATCH empty title → 400", r.status_code == 400, f"status={r.status_code}")

        # --------- Status transitions via Manager PATCH ---------
        r = client.patch(
            f"/api/manager/tasks/{task_b['id']}",
            headers=auth(ma_tok),
            json={"status": "completed"},
        )
        ok = r.status_code == 200
        t("T10. Manager mark task B COMPLETED", ok, f"status={r.status_code}")
        if ok:
            t("T10b. completed_at set", bool(r.json().get("completed_at")))

        r = client.patch(
            f"/api/manager/tasks/{task_b['id']}",
            headers=auth(ma_tok),
            json={"status": "in_progress"},
        )
        ok = r.status_code == 200
        t("T11. Manager revert task B to IN_PROGRESS", ok, f"status={r.status_code}")
        if ok:
            t("T11b. completed_at cleared", r.json().get("completed_at") is None)

        # --------- Manager DELETE ---------
        tmp = client.post(
            "/api/manager/tasks",
            headers=auth(ma_tok),
            json={"title": "Temporary task to delete", "priority": "low", "assigned_to": ea_id},
        ).json()
        r = client.delete(f"/api/manager/tasks/{tmp['id']}", headers=auth(ma_tok))
        t("T12. Manager DELETE own task 204", r.status_code == 204, f"status={r.status_code}")

        r = client.get(f"/api/manager/tasks/{tmp['id']}", headers=auth(ma_tok))
        t("T12b. Deleted task is gone (404)", r.status_code == 404)

        r = client.delete(f"/api/manager/tasks/{task_a['id']}", headers=auth(mb_tok))
        t("T13. Cross-manager DELETE → 404", r.status_code == 404, f"status={r.status_code}")

        # --------- List backward compat (no new params) ---------
        r = client.get("/api/manager/tasks", headers=auth(ma_tok))
        ok = r.status_code == 200
        t("T14. List tasks (no new params) → 200", ok, f"status={r.status_code}")
        if ok:
            t("T14b. Response is JSON array", isinstance(r.json(), list))
            t("T14c. At least 2 tasks remain", len(r.json()) >= 2, f"len={len(r.json())}")

        # --------- priority filter ---------
        r = client.get("/api/manager/tasks", params={"priority": "medium"}, headers=auth(ma_tok))
        t("T15. priority=medium filter", r.status_code == 200 and all(t.get("priority") == "medium" for t in r.json()), f"status={r.status_code}")

        # --------- search filter ---------
        r = client.get("/api/manager/tasks", params={"search": "release notes"}, headers=auth(ma_tok))
        t("T16. search='release notes'", all("release" in (t.get("title","") + " " + (t.get("description") or "")).lower() for t in r.json()), f"titles={[t['title'] for t in r.json()]}")

        # --------- deadline_from/to ---------
        r = client.get("/api/manager/tasks", params={"deadline_from": today.isoformat(), "deadline_to": tmrw.isoformat()}, headers=auth(ma_tok))
        t("T17. deadline_from/to date window", all(today.isoformat() <= (t.get("deadline") or "") <= tmrw.isoformat() for t in r.json()), f"rows={len(r.json())}")

        # --------- sort by deadline asc ---------
        r = client.get("/api/manager/tasks", params={"sort_by": "deadline", "sort_order": "asc"}, headers=auth(ma_tok))
        rows = r.json()
        deadlines = [t.get("deadline") or "9999-12-31" for t in rows]
        ok = deadlines == sorted(deadlines)
        t("T18. sort_by=deadline asc", ok, f"deadlines={deadlines}")

        # --------- sort_by=title desc ---------
        r = client.get("/api/manager/tasks", params={"sort_by": "title", "sort_order": "desc"}, headers=auth(ma_tok))
        titles = [t["title"] for t in r.json()]
        ok = titles == sorted(titles, reverse=True)
        t("T19. sort_by=title desc", ok, f"titles={titles}")

        # --------- limit/skip pagination ---------
        full = client.get("/api/manager/tasks", headers=auth(ma_tok)).json()
        r = client.get("/api/manager/tasks", params={"limit": 1, "skip": 0}, headers=auth(ma_tok))
        t("T20. limit=1 returns 1", len(r.json()) == 1, f"len={len(r.json())}")
        if len(full) >= 2:
            r2 = client.get("/api/manager/tasks", params={"limit": 1, "skip": 1}, headers=auth(ma_tok))
            t("T20b. skip=1 returns second row", r2.json() and r2.json()[0]["id"] == full[1]["id"])

        # --------- Overdue sync ---------
        overdue_task = client.post(
            "/api/manager/tasks",
            headers=auth(ma_tok),
            json={
                "title": "TASK with past deadline",
                "priority": "low",
                "deadline": last_week.isoformat(),
                "assigned_to": ea_id,
            },
        ).json()
        db.expire_all()
        row = db.query(Task).filter(Task.id == overdue_task["id"]).first()
        t("T21. After create, status=PENDING", row.status == TaskStatus.PENDING, f"status={row.status}")

        r = client.get("/api/manager/tasks", headers=auth(ma_tok))
        db.expire_all()
        row = db.query(Task).filter(Task.id == overdue_task["id"]).first()
        t("T22. After list call, auto-synced to OVERDUE", row.status == TaskStatus.OVERDUE, f"status={row.status}")

        # Completed past deadline — NEVER auto-sync to overdue
        done_task = client.post(
            "/api/manager/tasks",
            headers=auth(ma_tok),
            json={"title": "Already completed late", "deadline": yest.isoformat(), "assigned_to": ea_id},
        ).json()
        db.expire_all()
        client.patch(f"/api/manager/tasks/{done_task['id']}", headers=auth(ma_tok), json={"status": "completed"})
        db.expire_all()
        pre = db.query(Task).filter(Task.id == done_task["id"]).first()
        t("T23. Status is COMPLETED before list call", pre.status == TaskStatus.COMPLETED)
        client.get("/api/manager/tasks", headers=auth(ma_tok))
        db.expire_all()
        post = db.query(Task).filter(Task.id == done_task["id"]).first()
        t("T24. Completed task NOT auto-synced to OVERDUE", post.status == TaskStatus.COMPLETED, f"status={post.status}")

        # --------- Manager statistics split ---------
        r = client.get("/api/manager/statistics", headers=auth(ma_tok))
        ok = r.status_code == 200
        t("T25. Manager statistics 200", ok, f"status={r.status_code}")
        if ok:
            body = r.json()
            keys_ok = "in_progress_tasks" in body
            t("T25b. Has in_progress_tasks field", keys_ok, f"keys={sorted(body.keys())}")
            t("T25c. Numeric counts", all(isinstance(body.get(k), int) for k in ["pending_tasks", "in_progress_tasks", "completed_tasks", "overdue_tasks"]))

        # --------- Employee filters + sort + limit ---------
        r = client.get("/api/employee/tasks", params={"priority": "high"}, headers=auth(ea_tok))
        t("T26. Employee priority=high filter 200", r.status_code == 200, f"status={r.status_code}")
        t("T26b. Only EA assigned tasks (or empty)", all(t.get("assigned_to") == ea_id for t in r.json()) or len(r.json()) == 0)

        r = client.get("/api/employee/tasks", params={"search": "deck", "sort_by": "deadline", "sort_order": "asc", "limit": 5}, headers=auth(ea_tok))
        t("T27. Employee multi-param (search/sort/limit) 200", r.status_code == 200, f"status={r.status_code}")

        # --------- Employee edit PATCH title/priority/deadline/description ---------
        # First find a task assigned to ea_id
        my_task = client.post(
            "/api/manager/tasks",
            headers=auth(ma_tok),
            json={"title": "Employee editable sample", "description": "Init description", "priority": "medium", "deadline": next_week.isoformat(), "assigned_to": ea_id},
        ).json()
        patch_payload = {
            "title": "Employee editable sample — edited",
            "description": "Edited by employee",
            "priority": "high",
            "deadline": tmrw.isoformat(),
        }
        r = client.patch(f"/api/employee/tasks/{my_task['id']}", headers=auth(ea_tok), json=patch_payload)
        ok = r.status_code == 200
        t("T28. Employee PATCH title/desc/priority/deadline", ok, f"status={r.status_code}, text={r.text[:200]}")
        if ok:
            body = r.json()
            t("T28a. Title updated", body.get("title") == patch_payload["title"])
            t("T28b. Description updated", (body.get("description") or "") == patch_payload["description"])
            t("T28c. Priority updated", body.get("priority") == patch_payload["priority"])
            t("T28d. Deadline updated", body.get("deadline") == patch_payload["deadline"])

        r = client.patch(f"/api/employee/tasks/{my_task['id']}", headers=auth(eb_tok), json={"title": "should fail"})
        t("T29. Other employee patch → 404", r.status_code == 404, f"status={r.status_code}")

        # Ensure employee cannot alter assigned_to / created_by / meeting_id even if manually sent
        r = client.patch(
            f"/api/employee/tasks/{my_task['id']}",
            headers=auth(ea_tok),
            json={"title": "still allowed", "assigned_to": eb_id, "meeting_id": 9999, "created_by": eb_id},
        )
        ok = r.status_code == 200
        t("T30. Employee patch payload w/ forbidden keys — title accepted + others ignored", ok, f"status={r.status_code}")
        if ok:
            t("T30a. assigned_to unchanged", r.json().get("assigned_to") == ea_id)
            t("T30b. meeting_id unchanged", r.json().get("meeting_id") is None)
            t("T30c. created_by unchanged (manager ma_id)", r.json().get("created_by") == ma_id)

        # Employee task edit empty title rejected
        r = client.patch(f"/api/employee/tasks/{my_task['id']}", headers=auth(ea_tok), json={"title": "   "})
        t("T31. Employee PATCH empty title → 400", r.status_code == 400, f"status={r.status_code}, text={r.text[:200]}")

        # Employee stats now uses auto-overdue sync
        r = client.get("/api/employee/statistics", headers=auth(ea_tok))
        t("T32. Employee statistics 200", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            t("T32b. Stats keys", all(k in r.json() for k in ["total_tasks", "pending_tasks", "in_progress_tasks", "completed_tasks", "overdue_tasks"]))

        print(f"\n=== RESULTS: {passed}/{total} PASSED ===")
        return 0 if passed == total else 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FATAL EXCEPTION] {e}")
        return 2
    finally:
        db.close()
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
