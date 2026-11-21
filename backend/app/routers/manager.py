import json
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, UserRole, Meeting, Task, TaskStatus, Priority
from app.schemas.schemas import (
    EmployeeUserResponse,
    ManagerStatistics,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.dependencies import require_manager

router = APIRouter(prefix="/api/manager", tags=["Manager"])


def _manager_task_query(db: Session, current_user: User):
    return db.query(Task).join(
        Meeting, Task.meeting_id == Meeting.id, isouter=True
    ).filter(
        (Task.created_by == current_user.id)
        | (Meeting.created_by_id == current_user.id)
    )


def _get_manager_task_or_404(db: Session, current_user: User, task_id: int) -> Task:
    task = _manager_task_query(db, current_user).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not authorized.",
        )
    return task


def _validate_employee_assignee(db: Session, user_id: int) -> User:
    employee = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == UserRole.EMPLOYEE,
            User.is_active == True,
        )
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid employee. Please select an active Employee (role=employee, is_active=true).",
        )
    return employee


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


@router.get("/statistics", response_model=ManagerStatistics)
def get_manager_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    _auto_sync_overdue(db)

    stats = ManagerStatistics()

    manager_scoped_tasks = _manager_task_query(db, current_user)

    stats.total_meetings = (
        db.query(func.count(Meeting.id))
        .filter(Meeting.created_by_id == current_user.id)
        .scalar() or 0
    )

    stats.total_tasks = manager_scoped_tasks.count() or 0
    stats.completed_tasks = manager_scoped_tasks.filter(
        Task.status == TaskStatus.COMPLETED
    ).count() or 0

    pending_count = manager_scoped_tasks.filter(Task.status == TaskStatus.PENDING).count() or 0
    in_progress_count = manager_scoped_tasks.filter(Task.status == TaskStatus.IN_PROGRESS).count() or 0
    overdue_count = manager_scoped_tasks.filter(Task.status == TaskStatus.OVERDUE).count() or 0

    stats.overdue_tasks = overdue_count
    stats.pending_tasks = pending_count
    stats.in_progress_tasks = in_progress_count

    stats.team_members = (
        db.query(func.count(User.id))
        .filter(User.role == UserRole.EMPLOYEE, User.is_active == True)
        .scalar() or 0
    )

    return stats


@router.get("/employees", response_model=List[EmployeeUserResponse])
def list_manager_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    employees = (
        db.query(User)
        .filter(User.role == UserRole.EMPLOYEE, User.is_active == True)
        .order_by(User.first_name.asc(), User.last_name.asc())
        .all()
    )
    return employees


@router.get("/tasks", response_model=List[TaskResponse])
def list_manager_tasks(
    meeting_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    assigned_to: Optional[int] = None,
    priority: Optional[Priority] = None,
    search: Optional[str] = Query(default=None, min_length=1),
    deadline_from: Optional[date] = None,
    deadline_to: Optional[date] = None,
    sort_by: str = Query(default="created_at", pattern="^(created_at|deadline|priority|status|title)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    skip: int = Query(default=0, ge=0),
    limit: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    _auto_sync_overdue(db)

    query = _manager_task_query(db, current_user)
    if meeting_id is not None:
        query = query.filter(Task.meeting_id == meeting_id)
    if status is not None:
        query = query.filter(Task.status == status)
    if assigned_to is not None:
        query = query.filter(Task.assigned_to == assigned_to)
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


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_manager_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    if data.meeting_id is not None:
        meeting = (
            db.query(Meeting)
            .filter(
                Meeting.id == data.meeting_id,
                Meeting.created_by_id == current_user.id,
            )
            .first()
        )
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found or not authorized.",
            )

    _validate_employee_assignee(db, data.assigned_to)

    title = (data.title or "").strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task title is required.",
        )

    # Idempotency: prevent duplicate task creation from rapid repeated clicks
    # Same (created_by, meeting_id, assigned_to, title) within last 60 seconds → reuse existing
    recent_cutoff = datetime.utcnow().timestamp() - 60
    recent_dt = datetime.utcfromtimestamp(recent_cutoff)
    dup_q = db.query(Task).filter(
        Task.created_by == current_user.id,
        Task.assigned_to == data.assigned_to,
        Task.title == title,
        Task.created_at >= recent_dt,
    )
    if data.meeting_id is not None:
        dup_q = dup_q.filter(Task.meeting_id == data.meeting_id)
    else:
        dup_q = dup_q.filter(Task.meeting_id.is_(None))
    existing = dup_q.first()
    if existing:
        return existing

    priority = data.priority
    if priority is None:
        priority = Priority.MEDIUM

    task = Task(
        title=title,
        description=(data.description or "").strip() or None,
        status=TaskStatus.PENDING,
        priority=priority,
        deadline=data.deadline,
        meeting_id=data.meeting_id,
        assigned_to=data.assigned_to,
        created_by=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_manager_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    _auto_sync_overdue(db)
    return _get_manager_task_or_404(db, current_user, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_manager_task(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    task = _get_manager_task_or_404(db, current_user, task_id)
    update_data = data.model_dump(exclude_unset=True)

    immutable_keys = {"created_by", "created_at", "id", "meeting_id"}
    for key in immutable_keys:
        update_data.pop(key, None)

    if "assigned_to" in update_data:
        new_assignee = update_data["assigned_to"]
        if new_assignee is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user cannot be null.",
            )
        _validate_employee_assignee(db, new_assignee)
        task.assigned_to = new_assignee

    if "title" in update_data:
        title = (update_data["title"] or "").strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task title is required.",
            )
        task.title = title

    if "description" in update_data:
        desc_val = update_data["description"]
        task.description = (desc_val.strip() or None) if isinstance(desc_val, str) else desc_val

    if "priority" in update_data:
        task.priority = update_data["priority"]

    if "deadline" in update_data:
        task.deadline = update_data["deadline"]

    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == TaskStatus.COMPLETED and task.status != TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        if new_status != TaskStatus.COMPLETED and task.status == TaskStatus.COMPLETED:
            task.completed_at = None
        task.status = new_status
        task.updated_at = datetime.utcnow()

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manager_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    task = _get_manager_task_or_404(db, current_user, task_id)
    db.delete(task)
    db.commit()
    return None

