from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.models.models import UserRole, TaskStatus, Priority, MeetingStatus


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.EMPLOYEE


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[int] = None


class MeetingBase(BaseModel):
    title: str
    description: Optional[str] = None
    meeting_date: Optional[datetime] = None


class MeetingCreate(MeetingBase):
    pass


class ActionItem(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_person: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[Priority] = Priority.MEDIUM


class MeetingAnalysisResponse(BaseModel):
    meeting_summary: str
    key_decisions: List[str] = []
    action_items: List[ActionItem] = []


class MeetingListItem(MeetingBase):
    id: int
    created_by_id: int
    original_filename: str
    content_type: str
    file_size: Optional[int] = None
    status: MeetingStatus
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingResponse(MeetingBase):
    id: int
    created_by_id: int
    original_filename: str
    content_type: str
    file_size: Optional[int] = None
    status: MeetingStatus
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_decisions: Optional[str] = None
    action_items_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    deadline: Optional[date] = None
    assigned_to: int


class TaskCreate(TaskBase):
    meeting_id: Optional[int] = None


class EmployeeUserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool

    class Config:
        from_attributes = True


class ActionItemDraft(BaseModel):
    task: str
    person: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[Priority] = Priority.MEDIUM
    description: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    deadline: Optional[date] = None
    assigned_to: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    status: TaskStatus
    meeting_id: Optional[int] = None
    created_by: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    assigned_user: Optional[UserResponse] = None
    created_by_user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class TaskStats(BaseModel):
    total: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    overdue: int = 0


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class AdminUserCreate(UserCreate):
    role: UserRole = UserRole.EMPLOYEE


class AdminStatistics(BaseModel):
    total_users: int = 0
    total_admins: int = 0
    total_managers: int = 0
    total_employees: int = 0
    total_meetings: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0


class ManagerStatistics(BaseModel):
    total_meetings: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    team_members: int = 0


class EmployeeStatistics(BaseModel):
    total_tasks: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
