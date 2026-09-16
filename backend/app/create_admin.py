"""Bootstrap script to create the first admin user."""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.models import User
from app.auth import hash_password
from app.config import settings


def create_admin():
    """Create the initial admin user if it doesn't exist."""
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if existing:
            print(f"Admin user '{settings.ADMIN_USERNAME}' already exists.")
            return

        admin = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            display_name="Administrator",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Admin user '{settings.ADMIN_USERNAME}' created successfully.")
        print(f"Username: {settings.ADMIN_USERNAME}")
        print(f"Password: {settings.ADMIN_PASSWORD}")
        print("\nIMPORTANT: Change the default password after first login!")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
