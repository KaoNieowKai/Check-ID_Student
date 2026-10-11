"""FastAPI application entry point."""

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.templating import templates
from app.config import settings
from sqlalchemy.orm import Session
from app.database import init_db, SessionLocal
from app.models import User, AuditLog
from app.routers import auth, admin, teacher, student
from app.middleware.csrf import csrf_origin_check

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, docs_url=None, redoc_url=None)

# Register CSRF Origin/Referer validation middleware
app.middleware("http")(csrf_origin_check)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)


def ensure_super_admin_exists(db: Session = None):
    """One-time idempotent migration: ensure at least one super_admin exists.

    Rules:
    1. If ANY user with role='super_admin' AND is_active=True exists → do nothing.
    2. If no active super_admin exists → look for the bootstrap account
       (matching ADMIN_USERNAME from env) with role='admin'.
       - If found and is_active: promote to 'super_admin'. Log the promotion.
       - If found but is_active=False: skip (suspended account — do not promote).
       - If not found: skip (admin must run create_admin.py manually).
    3. Never promote multiple accounts. Never promote non-bootstrap accounts.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        # Check if any active super_admin already exists
        existing_sa = db.query(User).filter(
            User.role == "super_admin", User.is_active == True
        ).first()

        if existing_sa:
            logger.debug("Super Admin already exists. Skipping migration.")
            return

        # No active super_admin — look for the bootstrap account
        bootstrap_username = settings.ADMIN_USERNAME
        bootstrap_user = db.query(User).filter(
            User.username == bootstrap_username
        ).first()

        if not bootstrap_user:
            logger.warning(
                "No super_admin exists. Bootstrap account '%s' not found. "
                "Run create_admin.py.", bootstrap_username
            )
            return

        if not bootstrap_user.is_active:
            logger.warning(
                "Bootstrap account '%s' is suspended. Cannot auto-promote.",
                bootstrap_username
            )
            return

        if bootstrap_user.role != "admin":
            logger.warning(
                "Bootstrap account '%s' has role '%s', expected 'admin'. Skipping.",
                bootstrap_username, bootstrap_user.role
            )
            return

        # All conditions met — promote to super_admin
        previous_role = bootstrap_user.role
        bootstrap_user.role = "super_admin"

        # Create audit log entry for the promotion
        audit_entry = AuditLog(
            user_id=bootstrap_user.id,
            action="super_admin_migration",
            target_type="user",
            target_id=bootstrap_username,
            previous_value=previous_role,
            new_value="super_admin",
        )
        db.add(audit_entry)
        db.commit()

        logger.info(
            "Promoted user '%s' from admin to super_admin.", bootstrap_username
        )
    except Exception:
        db.rollback()
        logger.exception("Failed to run super_admin migration.")
    finally:
        if close_db:
            db.close()


@app.on_event("startup")
async def startup():
    """Initialize database tables on startup."""
    init_db()
    ensure_super_admin_exists()


@app.get("/")
async def root():
    """Redirect to login page."""
    return RedirectResponse(url="/login")


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request, "status_code": 403,
        "message": "คุณไม่มีสิทธิ์เข้าถึงหน้านี้"
    }, status_code=403)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request, "status_code": 404,
        "message": "ไม่พบหน้าที่คุณต้องการ"
    }, status_code=404)
