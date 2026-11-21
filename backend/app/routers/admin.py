from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User, UserRole, Meeting, Task, TaskStatus
from app.schemas.schemas import AdminStatistics
from app.dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/statistics", response_model=AdminStatistics)
def get_admin_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    stats = AdminStatistics()

    stats.total_users = db.query(func.count(User.id)).scalar() or 0
    stats.total_admins = db.query(func.count(User.id)).filter(User.role == UserRole.ADMIN).scalar() or 0
    stats.total_managers = db.query(func.count(User.id)).filter(User.role == UserRole.MANAGER).scalar() or 0
    stats.total_employees = db.query(func.count(User.id)).filter(User.role == UserRole.EMPLOYEE).scalar() or 0

    stats.total_meetings = db.query(func.count(Meeting.id)).scalar() or 0

    stats.total_tasks = db.query(func.count(Task.id)).scalar() or 0
    stats.completed_tasks = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.COMPLETED).scalar() or 0

    pending_count = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.PENDING).scalar() or 0
    in_progress_count = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.IN_PROGRESS).scalar() or 0
    overdue_count = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.OVERDUE).scalar() or 0

    today = date.today()
    auto_overdue = db.query(func.count(Task.id)).filter(
        Task.status != TaskStatus.COMPLETED,
        Task.deadline.isnot(None),
        Task.deadline < today
    ).scalar() or 0

    stats.overdue_tasks = max(overdue_count, auto_overdue)
    stats.pending_tasks = pending_count + in_progress_count

    return stats
