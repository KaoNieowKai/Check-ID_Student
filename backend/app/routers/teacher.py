"""Teacher routes: dashboard, attendance screen, QR generation, WebSocket."""

import io
import base64
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, cast, Integer
from app.database import get_db, SessionLocal
from app.models import User, Student, Activity, ActivitySession, AttendanceRecord, QRToken
from app.auth import require_teacher
from app.config import settings
from app.websocket import manager
from app.templating import templates
import qrcode

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Teacher's main page: select activity and session."""
    activities = db.query(Activity).filter(
        Activity.status.in_(["active", "scheduled"])
    ).order_by(Activity.name).all()

    return templates.TemplateResponse("teacher/dashboard.html", {
        "request": request, "user": user, "activities": activities,
    })


@router.get("/api/sessions/{activity_id}")
async def get_sessions(activity_id: int, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    """Get sessions for an activity (AJAX)."""
    sessions = db.query(ActivitySession).filter(
        ActivitySession.activity_id == activity_id,
        ActivitySession.status.in_(["active", "scheduled"])
    ).order_by(ActivitySession.date, ActivitySession.start_time).all()
    return [{"id": s.id, "name": s.name, "date": str(s.date),
             "start_time": str(s.start_time) if s.start_time else None,
             "end_time": str(s.end_time) if s.end_time else None} for s in sessions]


@router.get("/attendance/{session_id}", response_class=HTMLResponse)
async def attendance_screen(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Main attendance screen with QR code display."""
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Count eligible students
    student_query = db.query(func.count(Student.id)).filter(Student.is_active == True)
    if session.activity.eligible_grades:
        grades = [g.strip() for g in session.activity.eligible_grades.split(",")]
        student_query = student_query.filter(Student.grade.in_(grades))
    total_students = student_query.scalar()

    present_count = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.session_id == session_id
    ).scalar()

    return templates.TemplateResponse("teacher/attendance.html", {
        "request": request, "user": user,
        "session": session, "activity": session.activity,
        "total_students": total_students,
        "present_count": present_count,
        "not_checked_in": total_students - present_count,
        "qr_expire_seconds": settings.QR_TOKEN_EXPIRE_SECONDS,
    })


@router.get("/api/qr/{session_id}")
async def generate_qr(session_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    """Generate a new QR token and return QR code as base64 image."""
    session = db.query(ActivitySession).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    # Generate cryptographically random token
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires = now + timedelta(seconds=settings.QR_TOKEN_EXPIRE_SECONDS)

    qr_token = QRToken(
        session_id=session_id,
        token=token,
        created_at=now,
        expires_at=expires,
    )
    db.add(qr_token)
    db.commit()

    # Build an absolute check-in URL so QR scanners open the browser directly
    base = str(request.base_url).rstrip("/")
    checkin_url = f"{base}/checkin?token={token}"

    # Generate QR code image
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(checkin_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "qr_image": f"data:image/png;base64,{img_base64}",
        "token": token,
        "expires_at": expires.isoformat(),
        "created_at": now.isoformat(),
        "expire_seconds": settings.QR_TOKEN_EXPIRE_SECONDS,
    }


@router.get("/api/stats/{session_id}")
async def attendance_stats(session_id: int, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    """Get current attendance statistics for a session."""
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    student_query = db.query(func.count(Student.id)).filter(Student.is_active == True)
    if session.activity.eligible_grades:
        grades = [g.strip() for g in session.activity.eligible_grades.split(",")]
        student_query = student_query.filter(Student.grade.in_(grades))
    total = student_query.scalar()

    present = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.session_id == session_id
    ).scalar()

    return {
        "total": total,
        "present": present,
        "not_checked_in": total - present,
        "percentage": round(present / total * 100, 1) if total > 0 else 0,
    }


@router.get("/not-checked-in/{session_id}", response_class=HTMLResponse)
async def not_checked_in(
    session_id: int,
    request: Request,
    grade: str = Query(""),
    room: str = Query(""),
    search: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Show students who haven't checked in."""
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    # Get all checked-in student IDs for this session
    checked_in_ids = db.query(AttendanceRecord.student_id).filter(
        AttendanceRecord.session_id == session_id
    ).subquery()

    # Get students NOT in checked_in_ids
    query = db.query(Student).filter(
        Student.is_active == True,
        ~Student.id.in_(checked_in_ids)
    )

    if session.activity.eligible_grades:
        grades_list = [g.strip() for g in session.activity.eligible_grades.split(",")]
        query = query.filter(Student.grade.in_(grades_list))

    if grade:
        query = query.filter(Student.grade == grade)
    if room:
        query = query.filter(Student.room == room)
    if search:
        query = query.filter(or_(
            Student.student_id.contains(search),
            Student.full_name.contains(search)
        ))

    students = query.order_by(Student.grade, cast(Student.room, Integer), Student.student_id).all()

    grades = ["M.1", "M.2", "M.3", "M.4", "M.5", "M.6"]
    raw_rooms = [r[0] for r in db.query(Student.room).filter(Student.room != None).distinct().all()]
    rooms = sorted(raw_rooms, key=lambda x: int(x) if str(x).isdigit() else 99999)

    return templates.TemplateResponse("teacher/not_checked_in.html", {
        "request": request, "user": user,
        "session": session, "activity": session.activity,
        "students": students, "total": len(students),
        "grade": grade, "room_filter": room, "search": search,
        "grades": grades, "rooms": rooms,
    })


# ─── WebSocket for real-time updates ─────────────────────────────────

@router.websocket("/ws/attendance/{session_id}")
async def websocket_attendance(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time attendance updates on teacher screen."""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception:
        manager.disconnect(websocket, session_id)
