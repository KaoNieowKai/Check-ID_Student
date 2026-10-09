import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.templating import templates
from app.config import settings
from app.database import init_db, SessionLocal
from app.routers import auth, admin, teacher, student

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, docs_url=None, redoc_url=None)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)


def ensure_super_admin_exists(db: Session = None):
    """One-time, idempotent migration: promote the bootstrap admin to super_admin
    if no super_admin account exists yet.

    Safety guarantees:
    - If any super_admin already exists → does nothing (permanent no-op).
    - Only promotes the specific account matching ADMIN_USERNAME with role='admin'.
    - Never promotes all admins or arbitrary accounts.
    - Safe to run on every startup.
    """
    from app.models import User
    from sqlalchemy import func

    session = db or SessionLocal()
    close_session = db is None
    
    try:
        # Check if any super_admin already exists
        sa_count = session.query(func.count(User.id)).filter(
            User.role == "super_admin"
        ).scalar()
        if sa_count > 0:
            return  # Already initialized — nothing to do

        # Find the specific bootstrap admin account
        bootstrap_user = session.query(User).filter(
            User.username == settings.ADMIN_USERNAME,
            User.role == "admin"
        ).first()

        if bootstrap_user is None:
            logger.info(
                "No super_admin exists and bootstrap account '%s' not found with role='admin'. "
                "Run create_admin.py to create the initial super_admin.",
                settings.ADMIN_USERNAME
            )
            return

        # Promote only this specific account
        bootstrap_user.role = "super_admin"
        session.commit()
        logger.info(
            "Promoted bootstrap account '%s' (id=%d) to super_admin.",
            bootstrap_user.username, bootstrap_user.id
        )
    except Exception:
        session.rollback()
        logger.exception("Error during super_admin initialization.")
    finally:
        if close_session:
            session.close()


@app.on_event("startup")
async def startup():
    """Initialize database tables and ensure super_admin exists."""
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

