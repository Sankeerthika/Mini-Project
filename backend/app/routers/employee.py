from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User, Task, TaskStatus, Priority
from app.schemas.schemas import EmployeeStatistics, TaskResponse, TaskUpdate
from app.dependencies import require_employee

router = APIRouter(prefix="/api/employee", tags=["Employee"])


def _auto_sync_overdue(db: Session) -> None:
    today = date.today()
    try:
        db.query(Task).filter(
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            Task.deadline.isnot(None),
            Task.deadline < today,
        ).update(
            {Task.status: TaskStatus.OVERDUE, Task.updated_at: datetime.utcnow()},
            synchronize_session=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.get("/statistics", response_model=EmployeeStatistics)
def get_employee_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee),
):
    _auto_sync_overdue(db)

    stats = EmployeeStatistics()

    base_query = db.query(Task).filter(Task.assigned_to == current_user.id)

    stats.total_tasks = base_query.count() or 0
    stats.pending_tasks = base_query.filter(Task.status == TaskStatus.PENDING).count() or 0
    stats.in_progress_tasks = base_query.filter(Task.status == TaskStatus.IN_PROGRESS).count() or 0
    stats.completed_tasks = base_query.filter(Task.status == TaskStatus.COMPLETED).count() or 0
    stats.overdue_tasks = base_query.filter(Task.status == TaskStatus.OVERDUE).count() or 0

    return stats


@router.get("/tasks", response_model=List[TaskResponse])
def get_employee_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[Priority] = None,
    search: Optional[str] = Query(default=None, min_length=1),
    deadline_from: Optional[date] = None,
    deadline_to: Optional[date] = None,
    sort_by: str = Query(default="created_at", pattern="^(created_at|deadline|priority|status|title)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    skip: int = Query(default=0, ge=0),
    limit: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee),
):
    _auto_sync_overdue(db)

    query = db.query(Task).filter(Task.assigned_to == current_user.id)

    if status:
        query = query.filter(Task.status == status)
    if priority is not None:
        query = query.filter(Task.priority == priority)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
    if deadline_from is not None:
        query = query.filter(Task.deadline >= deadline_from)
    if deadline_to is not None:
        query = query.filter(Task.deadline <= deadline_to)

    priority_order = case(
        (Task.priority == Priority.HIGH, 1),
        (Task.priority == Priority.MEDIUM, 2),
        (Task.priority == Priority.LOW, 3),
        else_=4,
    )

    status_order = case(
        (Task.status == TaskStatus.OVERDUE, 0),
        (Task.status == TaskStatus.IN_PROGRESS, 1),
        (Task.status == TaskStatus.PENDING, 2),
        (Task.status == TaskStatus.COMPLETED, 3),
        else_=4,
    )

    primary_expr = Task.created_at
    if sort_by == "created_at":
        primary_expr = Task.created_at
    elif sort_by == "deadline":
        primary_expr = Task.deadline
    elif sort_by == "priority":
        primary_expr = priority_order
    elif sort_by == "status":
        primary_expr = status_order
    elif sort_by == "title":
        primary_expr = func.lower(Task.title)

    if sort_order == "asc":
        primary_expr = primary_expr.asc() if hasattr(primary_expr, "asc") else primary_expr
    else:
        primary_expr = primary_expr.desc() if hasattr(primary_expr, "desc") else primary_expr

    query = query.order_by(primary_expr, Task.created_at.desc())
    if skip:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)

    tasks = query.all()
    return tasks


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_employee_task_status(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee),
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.assigned_to == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not assigned to you"
        )

    update_data = task_update.model_dump(exclude_unset=True)

    allowed_fields = {"status", "title", "description", "priority", "deadline"}
    for key in list(update_data.keys()):
        if key not in allowed_fields:
            del update_data[key]

    if "title" in update_data:
        title = (update_data["title"] or "").strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task title is required.",
            )
        update_data["title"] = title

    if "description" in update_data:
        desc_val = update_data["description"]
        update_data["description"] = (desc_val.strip() or None) if isinstance(desc_val, str) else desc_val

    status_changed_to_completed = (
        "status" in update_data
        and update_data["status"] == TaskStatus.COMPLETED
        and task.status != TaskStatus.COMPLETED
    )
    status_changed_from_completed = (
        "status" in update_data
        and update_data["status"] != TaskStatus.COMPLETED
        and task.status == TaskStatus.COMPLETED
    )

    for key, value in update_data.items():
        if value is not None or key == "description":
            setattr(task, key, value)

    if status_changed_to_completed:
        task.completed_at = datetime.utcnow()
    if status_changed_from_completed:
        task.completed_at = None

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task
