"""Student check-in routes: QR scan → verify → confirm attendance."""

import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import Student, ActivitySession, AttendanceRecord, QRToken, CheckinSession, Activity
from app.config import settings, get_bkk_time
from app.websocket import manager
from app.templating import templates

router = APIRouter(tags=["student"])

VALID_GRADES = ["M.1", "M.2", "M.3", "M.4", "M.5", "M.6"]


# ─── Helpers ──────────────────────────────────────────────────────────

def _validate_checkin_session(checkin_token: str, db: Session):
    """Look up a CheckinSession by its token and verify it hasn't expired.

    Returns (checkin_session, error_message).
    """
    if not checkin_token:
        return None, "การเช็คชื่อหมดเวลา กรุณาสแกน QR Code ใหม่"

    cs = db.query(CheckinSession).filter(
        CheckinSession.checkin_token == checkin_token
    ).first()

    if not cs:
        return None, "การเช็คชื่อหมดเวลา กรุณาสแกน QR Code ใหม่"

    if get_bkk_time() > cs.expires_at:
        return None, "การเช็คชื่อหมดเวลา กรุณาสแกน QR Code ใหม่"

    return cs, None


# ─── GET /checkin ─────────────────────────────────────────────────────

@router.get("/checkin", response_class=HTMLResponse)
async def checkin_page(
    request: Request,
    token: str = Query(""),
    db: Session = Depends(get_db)
):
    """Student check-in page — shown after scanning QR code.

    Flow:
    1. Validate the QR token (must exist + not expired).
    2. If valid → create a temporary CheckinSession (3 min).
    3. Pass the checkin_token (NOT the QR token) to the template.
    """
    error = None
    session_info = None

    if token:
        # Validate QR token
        qr_token = db.query(QRToken).filter(QRToken.token == token).first()
        if not qr_token:
            error = "QR Code ไม่ถูกต้อง"
        elif get_bkk_time() > qr_token.expires_at:
            error = "QR Code หมดอายุ กรุณาสแกน QR Code ปัจจุบัน"
        else:
            # QR is valid — load the activity session
            activity_session = db.query(ActivitySession).options(
                joinedload(ActivitySession.activity)
            ).filter(ActivitySession.id == qr_token.session_id).first()

            if activity_session:
                # Create a temporary CheckinSession
                now = get_bkk_time()
                checkin_token = secrets.token_urlsafe(32)
                checkin_session = CheckinSession(
                    session_id=activity_session.id,
                    checkin_token=checkin_token,
                    created_at=now,
                    expires_at=now + timedelta(seconds=settings.CHECKIN_SESSION_EXPIRE_SECONDS),
                )
                db.add(checkin_session)
                db.commit()

                session_info = {
                    "session_id": activity_session.id,
                    "session_name": activity_session.name,
                    "activity_name": activity_session.activity.name,
                    "checkin_token": checkin_token,
                    "expires_in": settings.CHECKIN_SESSION_EXPIRE_SECONDS,
                }

    return templates.TemplateResponse("student/checkin.html", {
        "request": request,
        "error": error,
        "session_info": session_info,
        "grades": VALID_GRADES,
    })


# ─── POST /api/checkin/verify ────────────────────────────────────────

@router.post("/api/checkin/verify")
async def verify_student(
    checkin_token: str = Form(...),
    grade: str = Form(...),
    student_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Step 1: Verify student identity before confirming attendance.

    Validates the CheckinSession (not the QR token).
    """
    cs, err = _validate_checkin_session(checkin_token, db)
    if err:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": err,
            "session_expired": True,
        })

    # Find student
    student = db.query(Student).filter(
        Student.student_id == student_id,
        Student.is_active == True
    ).first()

    if not student or student.grade != grade:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "ไม่พบข้อมูลนักเรียน กรุณาตรวจสอบระดับชั้นและรหัสนักเรียน"
        })

    # Check if already checked in
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student.id,
        AttendanceRecord.session_id == cs.session_id
    ).first()

    if existing:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "บันทึกการเข้าร่วมแล้ว",
            "already_checked_in": True,
            "checked_in_at": existing.checked_in_at.strftime("%H:%M:%S") if existing.checked_in_at else None,
        })

    # Check eligibility
    activity_session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == cs.session_id).first()

    if activity_session and activity_session.activity.eligible_grades:
        eligible = [g.strip() for g in activity_session.activity.eligible_grades.split(",")]
        if student.grade not in eligible:
            return JSONResponse(status_code=400, content={
                "success": False,
                "message": "คุณไม่มีสิทธิ์เข้าร่วมกิจกรรมนี้"
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
            "session_id": cs.session_id,
            "checkin_token": checkin_token,
        }
    }


# ─── POST /api/checkin/confirm ───────────────────────────────────────

@router.post("/api/checkin/confirm")
async def confirm_attendance(
    checkin_token: str = Form(...),
    student_db_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Step 2: Actually record attendance after student confirms.

    Validates the CheckinSession (not the QR token).
    No grace period hack — the CheckinSession has its own 3-minute lifetime.
    """
    cs, err = _validate_checkin_session(checkin_token, db)
    if err:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": err,
            "session_expired": True,
        })

    # Verify student exists
    student = db.query(Student).filter(Student.id == student_db_id, Student.is_active == True).first()
    if not student:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": "ไม่พบข้อมูลนักเรียน"
        })

    # Record attendance (with duplicate protection)
    now = get_bkk_time()
    record = AttendanceRecord(
        student_id=student.id,
        session_id=cs.session_id,
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
            "message": "บันทึกการเข้าร่วมแล้ว",
        })

    # Broadcast update to teacher's WebSocket
    from sqlalchemy import func
    activity_session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == cs.session_id).first()

    total_query = db.query(func.count(Student.id)).filter(Student.is_active == True)
    if activity_session.activity.eligible_grades:
        grades = [g.strip() for g in activity_session.activity.eligible_grades.split(",")]
        total_query = total_query.filter(Student.grade.in_(grades))
    total = total_query.scalar()

    present = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.session_id == cs.session_id
    ).scalar()

    await manager.broadcast_to_session(cs.session_id, {
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
        "message": "บันทึกการเข้าร่วมเรียบร้อยแล้ว!",
        "checked_in_at": now.strftime("%H:%M:%S"),
        "checked_in_date": now.strftime("%d/%m/%Y"),
        "student": {
            "student_id": student.student_id,
            "full_name": student.full_name,
            "grade": student.grade,
            "room": student.room,
        }
    }
