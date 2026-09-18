"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.templating import templates
from app.config import settings
from app.database import init_db
from app.routers import auth, admin, teacher, student

app = FastAPI(title=settings.APP_NAME, docs_url=None, redoc_url=None)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)


@app.on_event("startup")
async def startup():
    """Initialize database tables on startup."""
    init_db()


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

