"""Authentication routes: login, logout."""

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import verify_password, create_access_token, get_current_user_from_cookie

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Show login page. Redirect if already logged in."""
    user = get_current_user_from_cookie(request, db)
    if user:
        if user.role == "admin":
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
            "error": "Invalid username or password."
        })
    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "This account has been disabled. Please contact admin."
        })

    token = create_access_token(data={"sub": user.username, "role": user.role})
    if user.role == "admin":
        redirect_url = "/admin/dashboard"
    else:
        redirect_url = "/teacher/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 480,  # 8 hours
    )
    return response


@router.get("/logout")
async def logout():
    """Clear auth cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
