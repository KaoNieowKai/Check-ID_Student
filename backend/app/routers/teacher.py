"""Teacher routes: dashboard, attendance screen, QR generation, WebSocket."""

import io
import base64
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, Query, HTTPException, Body
from pydantic import BaseModel
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

class StatusUpdateRequest(BaseModel):
    student_id: str
    status: str

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

    student_records = {rec.student_id: rec for rec in records}
    
    students_list = []
    stats = {"total": total_count, "present": 0, "leave": 0, "sick_leave": 0, "absent": 0}
    
    for st in eligible_students:
        rec = student_records.get(st.id)
        if rec:
            status = rec.status
            method = rec.checked_in_method
            time_str = rec.checked_in_at.strftime("%H:%M:%S")
        else:
            status = "absent"
            method = "-"
            time_str = "-"
            
        if status not in stats:
            status = "absent"
            
        stats[status] += 1
        
        students_list.append({
            "student_id": st.student_id,
            "full_name": st.full_name,
            "grade": st.grade,
            "room": st.room,
            "status": status,
            "method": method,
            "time": time_str
        })
        
    students_list.sort(key=lambda x: (x["grade"], int(x["room"]) if str(x["room"]).isdigit() else 999, x["student_id"]))

    return {
        "stats": stats,
        "students": students_list
    }


@router.post("/api/attendance/{session_id}/status")
async def update_attendance_status(
    session_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Update attendance status for a student."""
    session = db.query(ActivitySession).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    student = db.query(Student).filter(Student.student_id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    valid_statuses = ["present", "leave", "sick_leave", "absent"]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.session_id == session_id,
        AttendanceRecord.student_id == student.id
    ).first()
    
    if record:
        record.status = request.status
        record.checked_in_method = "manual"
        record.checked_in_at = get_bkk_time()
    else:
        record = AttendanceRecord(
            student_id=student.id,
            session_id=session_id,
            status=request.status,
            checked_in_method="manual",
            checked_in_at=get_bkk_time()
        )
        db.add(record)
        
    db.commit()
    
    # Notify websockets
    await manager.broadcast_to_session(session_id, {"type": "update"})
    
    return {"success": True, "status": request.status}

@router.get("/reports", response_class=HTMLResponse)
async def teacher_reports(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """PDF attendance report download page for teachers."""
    return templates.TemplateResponse("teacher/reports.html", {
        "request": request, "user": user,
    })


@router.get("/api/classrooms")
async def get_classrooms(
    grade: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Return sorted list of distinct classrooms for a given grade."""
    rooms = (
        db.query(Student.room)
        .filter(Student.grade == grade, Student.is_active == True)
        .distinct()
        .all()
    )
    room_list = sorted(
        [r[0] for r in rooms],
        key=lambda x: int(x) if str(x).isdigit() else 0
    )
    return {"grade": grade, "rooms": room_list}


def _build_attendance_pdf(students_data: list, lang: str, report_title: str, report_subtitle: str, base_dir: str) -> bytes:
    """Build a single combined attendance PDF from a list of student dicts.

    Each dict must have: student_id, full_name, grade, room, status.
    Returns raw PDF bytes.
    """
    status_map_th = {"present": "มา", "leave": "ลา", "sick_leave": "ลาป่วย", "absent": "ไม่มา"}
    status_map_en = {"present": "Present", "leave": "Leave", "sick_leave": "Sick Leave", "absent": "Absent"}
    status_map = status_map_th if lang == "th" else status_map_en

    class PDF(FPDF):
        def __init__(self, title, subtitle):
            super().__init__()
            self._report_title = title
            self._report_subtitle = subtitle

        def header(self):
            self.set_font("Prompt", "B", 16)
            self.cell(0, 10, self._report_title, align="C", new_x="LMARGIN", new_y="NEXT")
            if self._report_subtitle:
                self.set_font("Prompt", "", 11)
                self.cell(0, 8, self._report_subtitle, align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(4)

        def footer(self):
            self.set_y(-15)
            self.set_font("Prompt", "", 8)
            page_label = f"หน้า {self.page_no()}/{{nb}}" if lang == "th" else f"Page {self.page_no()}/{{nb}}"
            self.cell(0, 10, page_label, align="C")

    pdf = PDF(report_title, report_subtitle)

    font_path_reg = os.path.join(base_dir, "static", "fonts", "Prompt-Regular.ttf")
    font_path_med = os.path.join(base_dir, "static", "fonts", "Prompt-Medium.ttf")
    pdf.add_font("Prompt", "", font_path_reg)
    pdf.add_font("Prompt", "B", font_path_med)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Summary stats ───────────────────────────────────────────────
    stats = {"present": 0, "leave": 0, "sick_leave": 0, "absent": 0}
    for s in students_data:
        st = s.get("status", "absent")
        if st not in stats:
            st = "absent"
        stats[st] += 1
    total_count = len(students_data)

    lbl_total   = "นักเรียนทั้งหมด:"  if lang == "th" else "Total Students:"
    lbl_present = "มา:"               if lang == "th" else "Present:"
    lbl_leave   = "ลา:"               if lang == "th" else "Leave:"
    lbl_sick    = "ลาป่วย:"           if lang == "th" else "Sick Leave:"
    lbl_absent  = "ไม่มา:"            if lang == "th" else "Absent:"
    summary_title = "ข้อมูลสรุป"      if lang == "th" else "Summary"

    pdf.set_font("Prompt", "B", 13)
    pdf.cell(0, 9, summary_title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Prompt", "", 11)
    for lbl, val in [
        (lbl_total, total_count),
        (lbl_present, stats["present"]),
        (lbl_leave, stats["leave"]),
        (lbl_sick, stats["sick_leave"]),
        (lbl_absent, stats["absent"]),
    ]:
        pdf.cell(55, 8, lbl)
        pdf.cell(0, 8, str(val), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Student table grouped by status ────────────────────────────
    headers_th = ["ที่", "รหัสนักเรียน", "ชื่อ-นามสกุล", "ชั้น", "ห้อง", "สถานะ"]
    headers_en = ["No.", "Student ID", "Name", "Grade", "Room", "Status"]
    headers = headers_th if lang == "th" else headers_en
    col_widths = [10, 28, 68, 22, 18, 34]

    for st_val in ["present", "leave", "sick_leave", "absent"]:
        group = [s for s in students_data if s.get("status") == st_val]
        if not group:
            continue
        pdf.set_font("Prompt", "B", 13)
        pdf.cell(0, 9, f"{status_map[st_val]} ({len(group)})", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Prompt", "B", 10)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, align="C")
        pdf.ln(8)
        pdf.set_font("Prompt", "", 10)
        for idx, row in enumerate(group, 1):
            pdf.cell(col_widths[0], 8, str(idx), border=1, align="C")
            pdf.cell(col_widths[1], 8, str(row.get("student_id", "")), border=1, align="C")
            pdf.cell(col_widths[2], 8, str(row.get("full_name", "")), border=1)
            pdf.cell(col_widths[3], 8, str(row.get("grade", "")), border=1, align="C")
            pdf.cell(col_widths[4], 8, str(row.get("room", "")), border=1, align="C")
            pdf.cell(col_widths[5], 8, status_map.get(str(row.get("status", "absent")), str(row.get("status", ""))), border=1, align="C")
            pdf.ln(8)
        pdf.ln(4)

    return bytes(pdf.output())


@router.get("/api/attendance_pdf")
async def attendance_pdf_by_grade_room(
    session_id: int,
    grade: str = Query(...),
    room: str = Query("all"),
    lang: str = Query("th"),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Generate PDF for a specific grade (and optionally a specific classroom)."""
    from fastapi.responses import StreamingResponse
    import urllib.parse

    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build student query filtered server-side by grade (and optionally room)
    student_query = db.query(Student).filter(
        Student.is_active == True,
        Student.grade == grade
    )
    if room != "all":
        student_query = student_query.filter(Student.room == room)
    eligible_students = student_query.all()

    records = db.query(AttendanceRecord).options(
        joinedload(AttendanceRecord.student)
    ).filter(AttendanceRecord.session_id == session_id).all()
    student_records = {rec.student_id: rec for rec in records}

    students_data = []
    for st in eligible_students:
        rec = student_records.get(st.id)
        status = rec.status if rec else "absent"
        if status not in ("present", "leave", "sick_leave", "absent"):
            status = "absent"
        students_data.append({
            "student_id": st.student_id,
            "full_name": st.full_name,
            "grade": st.grade,
            "room": st.room,
            "status": status,
        })
    students_data.sort(key=lambda x: (
        int(x["room"]) if str(x["room"]).isdigit() else 999,
        x["student_id"]
    ))

    # Grade label for the report
    grade_num = grade.replace("M.", "").replace("ม.", "")
    if lang == "th":
        grade_label = f"ม.{grade_num}"
        if room == "all":
            subtitle = f"รายงานนักเรียนชั้น {grade_label} ทุกห้อง"
            filename = f"attendance_M{grade_num}_all_classrooms.pdf"
        else:
            subtitle = f"รายงานเฉพาะนักเรียนชั้น {grade_label} ห้อง {room}"
            filename = f"attendance_M{grade_num}_room_{room}.pdf"
        title = "สรุปการเข้าร่วมกิจกรรม"
    else:
        if room == "all":
            subtitle = f"Report for all classrooms in Grade {grade_num}"
            filename = f"attendance_M{grade_num}_all_classrooms.pdf"
        else:
            subtitle = f"Report for Grade {grade_num}, Classroom {room}"
            filename = f"attendance_M{grade_num}_room_{room}.pdf"
        title = "Attendance Summary"

    subtitle += f" — {session.activity.name} ({session.date})"

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    pdf_bytes = _build_attendance_pdf(students_data, lang, title, subtitle, base_dir)

    encoded = urllib.parse.quote(filename)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded}"}
    )


@router.get("/api/attendance_pdf_all")
async def attendance_pdf_all_students(
    session_id: int,
    lang: str = Query("th"),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Generate PDF containing all active students across every grade and classroom."""
    from fastapi.responses import StreamingResponse
    import urllib.parse

    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    eligible_students = db.query(Student).filter(Student.is_active == True).all()

    records = db.query(AttendanceRecord).options(
        joinedload(AttendanceRecord.student)
    ).filter(AttendanceRecord.session_id == session_id).all()
    student_records = {rec.student_id: rec for rec in records}

    students_data = []
    for st in eligible_students:
        rec = student_records.get(st.id)
        status = rec.status if rec else "absent"
        if status not in ("present", "leave", "sick_leave", "absent"):
            status = "absent"
        students_data.append({
            "student_id": st.student_id,
            "full_name": st.full_name,
            "grade": st.grade,
            "room": st.room,
            "status": status,
        })
    # Sort by grade number → room number → student_id
    students_data.sort(key=lambda x: (
        int(str(x["grade"]).replace("M.", "").replace("ม.", "")) if str(x["grade"]).replace("M.", "").replace("ม.", "").isdigit() else 999,
        int(x["room"]) if str(x["room"]).isdigit() else 999,
        x["student_id"]
    ))

    if lang == "th":
        title = "สรุปการเข้าร่วมกิจกรรม"
        subtitle = f"รายงานนักเรียนทุกชั้นและทุกห้อง — {session.activity.name} ({session.date})"
        filename = "attendance_all_students.pdf"
    else:
        title = "Attendance Summary"
        subtitle = f"All grades and classrooms — {session.activity.name} ({session.date})"
        filename = "attendance_all_students.pdf"

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    pdf_bytes = _build_attendance_pdf(students_data, lang, title, subtitle, base_dir)

    encoded = urllib.parse.quote(filename)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded}"}
    )


@router.get("/api/summary_pdf/{session_id}")
async def summary_pdf(
    session_id: int,
    lang: str = Query("th"),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher)
):
    """Generate and download a PDF summary of the attendance."""
    from fastapi.responses import StreamingResponse
    import urllib.parse

    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    student_query = db.query(Student).filter(Student.is_active == True)
    if session.activity.eligible_grades:
        grades = [g.strip() for g in session.activity.eligible_grades.split(",")]
        student_query = student_query.filter(Student.grade.in_(grades))
    
    eligible_students = student_query.all()
    total_count = len(eligible_students)

    records = db.query(AttendanceRecord).options(
        joinedload(AttendanceRecord.student)
    ).filter(AttendanceRecord.session_id == session_id).order_by(
        AttendanceRecord.checked_in_at.asc()
    ).all()

    student_records = {rec.student_id: rec for rec in records}
    
    students_list = []
    stats = {"present": 0, "leave": 0, "sick_leave": 0, "absent": 0}
    
    for st in eligible_students:
        rec = student_records.get(st.id)
        if rec:
            status = rec.status
            method = rec.checked_in_method
            time_str = rec.checked_in_at.strftime("%H:%M:%S")
        else:
            status = "absent"
            method = "-"
            time_str = "-"
            
        if status not in stats:
            status = "absent"
            
        stats[status] += 1
        
        students_list.append({
            "student_id": st.student_id,
            "full_name": st.full_name,
            "grade": st.grade,
            "room": st.room,
            "status": status,
            "method": method,
            "time": time_str
        })
        
    students_list.sort(key=lambda x: (x["grade"], int(x["room"]) if str(x["room"]).isdigit() else 999, x["student_id"]))

    class PDF(FPDF):
        def header(self):
            self.set_font('Prompt', 'B', 16)
            title = "สรุปการเช็กชื่อ" if lang == "th" else "Attendance Summary"
            self.cell(0, 10, title, align='C', new_x="LMARGIN", new_y="NEXT")
            self.set_font('Prompt', '', 12)
            self.cell(0, 10, f"{session.activity.name} - {session.name} ({session.date})", align='C', new_x="LMARGIN", new_y="NEXT")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Prompt', '', 8)
            self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    pdf = PDF()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    font_path_reg = os.path.join(base_dir, "static", "fonts", "Prompt-Regular.ttf")
    font_path_med = os.path.join(base_dir, "static", "fonts", "Prompt-Medium.ttf")
    
    pdf.add_font("Prompt", "", font_path_reg)
    pdf.add_font("Prompt", "B", font_path_med)
    
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font('Prompt', 'B', 14)
    summary_title = "ข้อมูลสรุป" if lang == "th" else "Summary"
    pdf.cell(0, 10, summary_title, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Prompt', '', 12)
    
    lbl_total = "นักเรียนทั้งหมด:" if lang == "th" else "Total Students:"
    lbl_present = "มา:" if lang == "th" else "Present:"
    lbl_leave = "ลา:" if lang == "th" else "Leave:"
    lbl_sick = "ลาป่วย:" if lang == "th" else "Sick Leave:"
    lbl_absent = "ไม่มา:" if lang == "th" else "Absent:"
    
    pdf.cell(50, 8, lbl_total)
    pdf.cell(0, 8, str(total_count), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(50, 8, lbl_present)
    pdf.cell(0, 8, str(stats['present']), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(50, 8, lbl_leave)
    pdf.cell(0, 8, str(stats['leave']), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(50, 8, lbl_sick)
    pdf.cell(0, 8, str(stats['sick_leave']), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(50, 8, lbl_absent)
    pdf.cell(0, 8, str(stats['absent']), new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    status_map_th = {"present": "มา", "leave": "ลา", "sick_leave": "ลาป่วย", "absent": "ไม่มา"}
    status_map_en = {"present": "Present", "leave": "Leave", "sick_leave": "Sick Leave", "absent": "Absent"}
    status_map = status_map_th if lang == "th" else status_map_en
    
    col_widths = [10, 25, 60, 20, 20, 30, 25]
    headers_th = ["ที่", "รหัสนักเรียน", "ชื่อ-นามสกุล", "ชั้น", "ห้อง", "สถานะ", "เวลา"]
    headers_en = ["No.", "Student ID", "Name", "Grade", "Room", "Status", "Time"]
    headers = headers_th if lang == "th" else headers_en
    
    for st_val in ["present", "leave", "sick_leave", "absent"]:
        group_students = [s for s in students_list if s["status"] == st_val]
        if group_students:
            pdf.set_font('Prompt', 'B', 14)
            group_title = f"{status_map[st_val]} ({len(group_students)})"
            pdf.cell(0, 10, group_title, new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font('Prompt', 'B', 10)
            for i in range(len(headers)):
                pdf.cell(col_widths[i], 8, headers[i], border=1, align='C')
            pdf.ln(8)
            
            pdf.set_font('Prompt', '', 10)
            for idx, row in enumerate(group_students, 1):
                pdf.cell(col_widths[0], 8, str(idx), border=1, align='C')
                pdf.cell(col_widths[1], 8, row["student_id"], border=1, align='C')
                pdf.cell(col_widths[2], 8, row["full_name"], border=1)
                pdf.cell(col_widths[3], 8, row["grade"], border=1, align='C')
                pdf.cell(col_widths[4], 8, str(row["room"]), border=1, align='C')
                pdf.cell(col_widths[5], 8, status_map.get(row["status"], row["status"]), border=1, align='C')
                pdf.cell(col_widths[6], 8, row["time"], border=1, align='C')
                pdf.ln(8)
            pdf.ln(5)
    

    pdf_bytes = bytes(pdf.output())
    
    base_name = f"สรุปการเช็กชื่อ" if lang == "th" else f"Attendance_Summary"
    filename = f"{base_name}_{session.activity.name}_{session.date}.pdf"
    encoded_filename = urllib.parse.quote(filename)
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"}
    )
