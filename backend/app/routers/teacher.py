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
from app.config import settings, get_bkk_time
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
    now = get_bkk_time()
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


@router.get("/attendance-list/{session_id}", response_class=HTMLResponse)
async def attendance_list(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Show comprehensive attendance overview for the session."""
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse("teacher/attendance_list.html", {
        "request": request, "user": user,
        "session": session, "activity": session.activity,
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


# ─── Monitoring & History ──────────────────────────────────────────────

@router.get("/api/monitoring/{session_id}")
async def monitoring_data(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """API endpoint to get monitoring data for a session."""
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    # 1. Stats & Eligible Students
    student_query = db.query(Student).filter(Student.is_active == True)
    if session.activity.eligible_grades:
        grades = [g.strip() for g in session.activity.eligible_grades.split(",")]
        student_query = student_query.filter(Student.grade.in_(grades))
    
    eligible_students = student_query.all()
    total_count = len(eligible_students)

    # 2. Checked In Records
    records = db.query(AttendanceRecord).options(
        joinedload(AttendanceRecord.student)
    ).filter(AttendanceRecord.session_id == session_id).order_by(
        AttendanceRecord.checked_in_at.asc()
    ).all()

    checked_in = []
    checked_in_ids = set()
    for rec in records:
        checked_in_ids.add(rec.student_id)
        checked_in.append({
            "student_id": rec.student.student_id,
            "full_name": rec.student.full_name,
            "grade": rec.student.grade,
            "room": rec.student.room,
            "method": rec.checked_in_method,
            "date": rec.checked_in_at.strftime("%Y-%m-%d"),
            "time": rec.checked_in_at.strftime("%H:%M:%S")
        })

    # 3. Not Checked In
    not_checked_in = []
    for st in eligible_students:
        if st.id not in checked_in_ids:
            not_checked_in.append({
                "student_id": st.student_id,
                "full_name": st.full_name,
                "grade": st.grade,
                "room": st.room,
                "status": "not_checked_in"
            })
    
    # Sort not_checked_in by grade, room, student_id
    not_checked_in.sort(key=lambda x: (x["grade"], int(x["room"]) if str(x["room"]).isdigit() else 999, x["student_id"]))

    return {
        "stats": {
            "total": total_count,
            "present": len(checked_in),
            "absent": len(not_checked_in)
        },
        "checked_in": checked_in,
        "not_checked_in": not_checked_in,
        "history": checked_in
    }
