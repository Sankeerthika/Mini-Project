from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Date, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, PyEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class Priority(str, PyEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MeetingStatus(str, PyEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meetings_created = relationship("Meeting", back_populates="created_by", foreign_keys="Meeting.created_by_id")
    tasks_assigned = relationship("Task", back_populates="assigned_user", foreign_keys="Task.assigned_to")
    tasks_created = relationship("Task", back_populates="created_by_user", foreign_keys="Task.created_by")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    original_filename = Column(String, nullable=False)
    recording_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.UPLOADED, nullable=False)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    key_decisions = Column(Text, nullable=True)
    action_items_json = Column(Text, nullable=True)
    meeting_date = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = relationship("User", back_populates="meetings_created", foreign_keys=[created_by_id])
    tasks = relationship("Task", back_populates="meeting")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM, nullable=False)
    deadline = Column(Date, nullable=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_user = relationship("User", back_populates="tasks_assigned", foreign_keys=[assigned_to])
    created_by_user = relationship("User", back_populates="tasks_created", foreign_keys=[created_by])
    meeting = relationship("Meeting", back_populates="tasks")
