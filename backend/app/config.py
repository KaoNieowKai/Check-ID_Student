"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Student Activity Attendance")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./attendance.db")
    QR_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("QR_TOKEN_EXPIRE_SECONDS", "30"))
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")


settings = Settings()
