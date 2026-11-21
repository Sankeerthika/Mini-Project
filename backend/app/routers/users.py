from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserStatusUpdate,
)
from app.utils.security import hash_password
from app.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
def list_users(
    search: Optional[str] = Query(None, description="Search by first name, last name, or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(User)

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            or_(
                User.email.ilike(search_lower),
                User.first_name.ilike(search_lower),
                User.last_name.ilike(search_lower),
            )
        )

    if role is not None:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing_user = db.query(User).filter(User.email == user.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )

    new_user = User(
        first_name=user.first_name.strip(),
        last_name=user.last_name.strip(),
        email=user.email.lower().strip(),
        hashed_password=hash_password(user.password),
        role=user.role,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    if "email" in update_data and update_data["email"]:
        new_email = update_data["email"].lower().strip()
        existing = db.query(User).filter(and_(User.email == new_email, User.id != user_id)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )
        update_data["email"] = new_email

    if "is_active" in update_data and update_data["is_active"] is False:
        if user.role == UserRole.ADMIN:
            active_admins = (
                db.query(User)
                .filter(User.role == UserRole.ADMIN, User.is_active == True, User.id != user_id)
                .count()
            )
            if active_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the only active Admin account."
                )

    if "role" in update_data and update_data["role"] != user.role:
        if user.role == UserRole.ADMIN:
            active_admins = (
                db.query(User)
                .filter(User.role == UserRole.ADMIN, User.is_active == True, User.id != user_id)
                .count()
            )
            if active_admins == 0 and update_data["role"] != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove Admin role from the only active Admin account."
                )

    for key, value in update_data.items():
        if value is not None:
            setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if status_update.is_active is False:
        if user.role == UserRole.ADMIN:
            active_admins = (
                db.query(User)
                .filter(User.role == UserRole.ADMIN, User.is_active == True, User.id != user_id)
                .count()
            )
            if active_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the only active Admin account."
                )

    user.is_active = status_update.is_active
    db.commit()
    db.refresh(user)
    return user
