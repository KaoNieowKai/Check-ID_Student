"""Authentication routes: login, logout."""

import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import verify_password, create_access_token, get_current_user_from_cookie
from app.config import settings
from app.templating import templates

router = APIRouter(tags=["auth"])


def _is_secure_cookie(request: Request) -> bool:
    """Determine whether access_token cookie should have Secure flag.

    In local HTTP development (localhost, 127.0.0.1, LAN IP, etc.),
    browsers drop Secure cookies, preventing authentication.
    In production (HTTPS or non-local host), Secure is enabled.
    Can also be explicitly overridden via COOKIE_SECURE env var.
    """
    env_override = os.getenv("COOKIE_SECURE")
    if env_override is not None:
        return env_override.strip().lower() in ("true", "1")

    if settings.DATABASE_URL.startswith("sqlite"):
        return False

    host = request.headers.get("host", "").split(":")[0].lower()
    is_local_host = host in ("localhost", "127.0.0.1", "0.0.0.0") or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172.")
    if is_local_host and request.url.scheme == "http":
        return False

    return True


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Show login page. Redirect if already logged in."""
    user = get_current_user_from_cookie(request, db)
    if user:
        if user.role in ("admin", "super_admin"):
            return RedirectResponse(url="/admin/dashboard", status_code=303)
        return RedirectResponse(url="/teacher/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process login form."""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
        })
    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "บัญชีนี้ถูกปิดใช้งาน กรุณาติดต่อผู้ดูแลระบบ"
        })

    token = create_access_token(data={"sub": user.username, "role": user.role})
    if user.role in ("admin", "super_admin"):
        redirect_url = "/admin/dashboard"
    else:
        redirect_url = "/teacher/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=_is_secure_cookie(request),
        max_age=60 * 480,  # 8 hours
    )
    return response


@router.get("/logout")
async def logout():
    """Clear auth cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
