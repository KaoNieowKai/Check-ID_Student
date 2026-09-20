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
import os
from fpdf import FPDF

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

@router.get("/api/summary_pdf/{session_id}")
async def summary_pdf(
    session_id: int,
    lang: str = Query("th"),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Generate and download a PDF summary of the attendance."""
    from fastapi.responses import StreamingResponse
    import re

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
        checked_in.append(rec)

    # 3. Not Checked In
    not_checked_in = []
    for st in eligible_students:
        if st.id not in checked_in_ids:
            not_checked_in.append(st)
    
    # Sort not_checked_in by grade, room, student_id
    not_checked_in.sort(key=lambda x: (x.grade, int(x.room) if str(x.room).isdigit() else 999, x.student_id))

    class PDF(FPDF):
        def header(self):
            self.set_font('Prompt', 'B', 16)
            title = "สรุปการเช็คชื่อ" if lang == "th" else "Attendance Summary"
            self.cell(0, 10, title, align='C', new_x="LMARGIN", new_y="NEXT")
            self.set_font('Prompt', '', 12)
            self.cell(0, 10, f"{session.activity.name} - {session.name} ({session.date})", align='C', new_x="LMARGIN", new_y="NEXT")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Prompt', '', 8)
            self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    pdf = PDF()
    
    # Register fonts
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    font_path_reg = os.path.join(base_dir, "static", "fonts", "Prompt-Regular.ttf")
    font_path_med = os.path.join(base_dir, "static", "fonts", "Prompt-Medium.ttf")
    
    pdf.add_font("Prompt", "", font_path_reg)
    pdf.add_font("Prompt", "B", font_path_med)
    
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Summary Section
    pdf.set_font('Prompt', 'B', 14)
    summary_title = "ข้อมูลสรุป" if lang == "th" else "Summary"
    pdf.cell(0, 10, summary_title, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Prompt', '', 12)
    present_count = len(checked_in)
    absent_count = len(not_checked_in)
    rate = (present_count / total_count * 100) if total_count > 0 else 0
    
    lbl_total = "นักเรียนทั้งหมด:" if lang == "th" else "Total Students:"
    lbl_present = "มาเช็คชื่อแล้ว:" if lang == "th" else "Present:"
    lbl_absent = "ยังไม่เช็คชื่อ:" if lang == "th" else "Not Checked In:"
    lbl_rate = "อัตราการเข้าร่วม:" if lang == "th" else "Attendance Rate:"
    
    pdf.cell(50, 8, lbl_total)
    pdf.cell(0, 8, str(total_count), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(50, 8, lbl_present)
    pdf.cell(0, 8, str(present_count), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(50, 8, lbl_absent)
    pdf.cell(0, 8, str(absent_count), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(50, 8, lbl_rate)
    pdf.cell(0, 8, f"{rate:.1f}%", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # Present Students Table
    pdf.set_font('Prompt', 'B', 14)
    present_title = "รายชื่อนักเรียนที่มา" if lang == "th" else "Present Students"
    pdf.cell(0, 10, present_title, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Prompt', 'B', 10)
    col_widths = [10, 25, 60, 20, 20, 25, 30]
    headers_th = ["ที่", "รหัสนักเรียน", "ชื่อ-นามสกุล", "ชั้น", "ห้อง", "เวลาเช็คชื่อ", "วิธีการ"]
    headers_en = ["No.", "Student ID", "Name", "Grade", "Room", "Time", "Method"]
    headers = headers_th if lang == "th" else headers_en
    
    for i in range(len(headers)):
        pdf.cell(col_widths[i], 8, headers[i], border=1, align='C')
    pdf.ln(8)
    
    pdf.set_font('Prompt', '', 10)
    for idx, rec in enumerate(checked_in, 1):
        pdf.cell(col_widths[0], 8, str(idx), border=1, align='C')
        pdf.cell(col_widths[1], 8, rec.student.student_id, border=1, align='C')
        pdf.cell(col_widths[2], 8, rec.student.full_name, border=1)
        pdf.cell(col_widths[3], 8, rec.student.grade, border=1, align='C')
        pdf.cell(col_widths[4], 8, rec.student.room, border=1, align='C')
        pdf.cell(col_widths[5], 8, rec.checked_in_at.strftime("%H:%M:%S"), border=1, align='C')
        method = rec.checked_in_method
        if method in ("admin_manual", "qr"):
            method = "สแกน QR" if lang == "th" else "QR Scan"
        pdf.cell(col_widths[6], 8, method, border=1, align='C')
        pdf.ln(8)
    
    pdf.ln(10)
    
    # Not Checked In Table
    pdf.set_font('Prompt', 'B', 14)
    absent_title = "รายชื่อนักเรียนที่ไม่มา" if lang == "th" else "Not Checked In Students"
    pdf.cell(0, 10, absent_title, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Prompt', 'B', 10)
    col_widths_absent = [10, 25, 70, 25, 25, 35]
    headers_absent_th = ["ที่", "รหัสนักเรียน", "ชื่อ-นามสกุล", "ระดับชั้น", "ห้อง", "สถานะ"]
    headers_absent_en = ["No.", "Student ID", "Name", "Grade", "Room", "Status"]
    headers_absent = headers_absent_th if lang == "th" else headers_absent_en
    
    for i in range(len(headers_absent)):
        pdf.cell(col_widths_absent[i], 8, headers_absent[i], border=1, align='C')
    pdf.ln(8)
    
    pdf.set_font('Prompt', '', 10)
    status_text = "ยังไม่เช็คชื่อ" if lang == "th" else "Not Checked In"
    for idx, st in enumerate(not_checked_in, 1):
        pdf.cell(col_widths_absent[0], 8, str(idx), border=1, align='C')
        pdf.cell(col_widths_absent[1], 8, st.student_id, border=1, align='C')
        pdf.cell(col_widths_absent[2], 8, st.full_name, border=1)
        pdf.cell(col_widths_absent[3], 8, st.grade, border=1, align='C')
        pdf.cell(col_widths_absent[4], 8, st.room, border=1, align='C')
        pdf.cell(col_widths_absent[5], 8, status_text, border=1, align='C')
        pdf.ln(8)
        
    pdf_bytes = bytes(pdf.output())
    
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', session.activity.name)
    filename = f"Attendance_Summary_{safe_name}_{session.date}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
