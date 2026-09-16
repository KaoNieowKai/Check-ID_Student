"""Student check-in routes: QR scan → verify → confirm attendance."""

from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import Student, ActivitySession, AttendanceRecord, QRToken, Activity
from app.websocket import manager

router = APIRouter(tags=["student"])
templates = Jinja2Templates(directory="templates")

VALID_GRADES = ["M.1", "M.2", "M.3", "M.4", "M.5", "M.6"]


@router.get("/checkin", response_class=HTMLResponse)
async def checkin_page(
    request: Request,
    token: str = Query(""),
    db: Session = Depends(get_db)
):
    """Student check-in page — shown after scanning QR code."""
    error = None
    session_info = None

    if token:
        # Validate token
        qr_token = db.query(QRToken).filter(QRToken.token == token).first()
        if not qr_token:
            error = "Invalid QR Code. Please scan the current QR Code."
        elif datetime.utcnow() > qr_token.expires_at:
            error = "This QR Code has expired. Please scan the current QR Code."
        else:
            session = db.query(ActivitySession).options(
                joinedload(ActivitySession.activity)
            ).filter(ActivitySession.id == qr_token.session_id).first()
            if session:
                session_info = {
                    "session_id": session.id,
                    "session_name": session.name,
                    "activity_name": session.activity.name,
                    "token": token,
                }

    return templates.TemplateResponse("student/checkin.html", {
        "request": request,
        "token": token,
        "error": error,
        "session_info": session_info,
        "grades": VALID_GRADES,
    })


@router.post("/api/checkin/verify")
async def verify_student(
    token: str = Form(...),
    grade: str = Form(...),
    student_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Step 1: Verify student identity before confirming attendance."""
    # Validate token again
    qr_token = db.query(QRToken).filter(QRToken.token == token).first()
    if not qr_token:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Invalid QR Code. Please scan the current QR Code."
        })
    if datetime.utcnow() > qr_token.expires_at:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "This QR Code has expired. Please scan the current QR Code."
        })

    # Find student
    student = db.query(Student).filter(
        Student.student_id == student_id,
        Student.is_active == True
    ).first()

    if not student or student.grade != grade:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Student information not found. Please check your grade and student ID."
        })

    # Check if already checked in
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student.id,
        AttendanceRecord.session_id == qr_token.session_id
    ).first()

    if existing:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Attendance already recorded.",
            "already_checked_in": True,
            "checked_in_at": existing.checked_in_at.strftime("%H:%M:%S") if existing.checked_in_at else None,
        })

    # Check eligibility
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == qr_token.session_id).first()

    if session and session.activity.eligible_grades:
        eligible = [g.strip() for g in session.activity.eligible_grades.split(",")]
        if student.grade not in eligible:
            return JSONResponse(status_code=400, content={
                "success": False,
                "message": "You are not eligible for this activity."
            })

    return {
        "success": True,
        "student": {
            "db_id": student.id,
            "student_id": student.student_id,
            "full_name": student.full_name,
            "grade": student.grade,
            "room": student.room,
        },
        "session": {
            "session_id": qr_token.session_id,
            "token": token,
        }
    }


@router.post("/api/checkin/confirm")
async def confirm_attendance(
    token: str = Form(...),
    student_db_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Step 2: Actually record attendance after student confirms."""
    # Validate token (we accept even an expired token at this point
    # if verification happened within the validity window)
    qr_token = db.query(QRToken).filter(QRToken.token == token).first()
    if not qr_token:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Invalid QR Code."
        })

    # Allow a small grace period (60 seconds) after token expiry for the confirmation step
    from datetime import timedelta
    grace_expiry = qr_token.expires_at + timedelta(seconds=60)
    if datetime.utcnow() > grace_expiry:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Session has expired. Please scan the QR Code again."
        })

    # Verify student exists
    student = db.query(Student).filter(Student.id == student_db_id, Student.is_active == True).first()
    if not student:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Student not found."
        })

    # Record attendance (with duplicate protection)
    now = datetime.utcnow()
    record = AttendanceRecord(
        student_id=student.id,
        session_id=qr_token.session_id,
        status="present",
        checked_in_at=now,
        checked_in_method="qr",
    )

    try:
        db.add(record)
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "Attendance already recorded.",
        })

    # Broadcast update to teacher's WebSocket
    from sqlalchemy import func
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == qr_token.session_id).first()

    total_query = db.query(func.count(Student.id)).filter(Student.is_active == True)
    if session.activity.eligible_grades:
        grades = [g.strip() for g in session.activity.eligible_grades.split(",")]
        total_query = total_query.filter(Student.grade.in_(grades))
    total = total_query.scalar()

    present = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.session_id == qr_token.session_id
    ).scalar()

    await manager.broadcast_to_session(qr_token.session_id, {
        "type": "attendance_update",
        "total": total,
        "present": present,
        "not_checked_in": total - present,
        "percentage": round(present / total * 100, 1) if total > 0 else 0,
        "last_checkin": {
            "student_id": student.student_id,
            "full_name": student.full_name,
            "grade": student.grade,
            "room": student.room,
            "time": now.strftime("%H:%M:%S"),
        }
    })

    return {
        "success": True,
        "message": "Attendance recorded successfully!",
        "checked_in_at": now.strftime("%H:%M:%S"),
        "student": {
            "student_id": student.student_id,
            "full_name": student.full_name,
            "grade": student.grade,
            "room": student.room,
        }
    }
