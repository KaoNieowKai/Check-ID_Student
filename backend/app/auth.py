"""Authentication utilities: password hashing, JWT, and FastAPI dependencies."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Extract and validate JWT from httpOnly cookie. Returns None if not authenticated."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    return user


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: require authenticated user or redirect to login."""
    user = get_current_user_from_cookie(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    return user


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: require admin role."""
    user = get_current_user_from_cookie(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def require_teacher(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: require teacher or admin role."""
    user = get_current_user_from_cookie(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required"
        )
    return user
