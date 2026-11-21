import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal, Base, engine
from app.models.models import User, UserRole
from app.utils.security import hash_password


def create_first_admin():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing_admins = db.query(User).filter(User.role == UserRole.ADMIN).count()
        if existing_admins > 0:
            print(f"[SKIP] There are already {existing_admins} Admin user(s) in the system.")
            print("       Use the Admin dashboard or API to create additional users.")
            return

        email = os.getenv("ADMIN_EMAIL") or "admin@example.com"
        password = os.getenv("ADMIN_PASSWORD") or "Admin123!"
        first_name = os.getenv("ADMIN_FIRST_NAME") or "System"
        last_name = os.getenv("ADMIN_LAST_NAME") or "Administrator"

        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            print(f"[WARN] A user with email {email} already exists but is not an Admin.")
            print(f"       Existing user role: {existing.role}")
            print(f"       Setting existing user role to ADMIN and activating.")
            existing.role = UserRole.ADMIN
            existing.is_active = True
            existing.hashed_password = hash_password(password)
            db.commit()
            db.refresh(existing)
            print(f"[OK] User {email} promoted to Admin. Password updated.")
            return

        admin = User(
            first_name=first_name,
            last_name=last_name,
            email=email.lower(),
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("=" * 60)
        print("[SUCCESS] First Admin account created successfully!")
        print("=" * 60)
        print(f"  Email:     {email}")
        print(f"  Password:  {password}")
        print(f"  Name:      {first_name} {last_name}")
        print(f"  Role:      ADMIN")
        print("=" * 60)
        print("IMPORTANT: Log in and change the default password immediately!")
        print("You can customize credentials via backend/.env:")
        print("  ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_FIRST_NAME, ADMIN_LAST_NAME")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    create_first_admin()
