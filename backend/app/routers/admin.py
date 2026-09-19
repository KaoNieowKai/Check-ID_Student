"""Admin routes: dashboard, student management, teacher management, activities, sessions, attendance, reports, audit."""

import io
import json
import re
import secrets
from datetime import datetime, date, time, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, desc, cast, Integer
from openpyxl import Workbook, load_workbook
from app.database import get_db
from app.models import User, Student, Activity, ActivitySession, AttendanceRecord, AuditLog
from app.auth import require_admin, hash_password
from app.config import get_bkk_time
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_GRADES = ["M.1", "M.2", "M.3", "M.4", "M.5", "M.6"]


def create_audit_log(db: Session, user_id: int, action: str, target_type: str = None,
                     target_id: str = None, previous_value: str = None,
                     new_value: str = None, reason: str = None):
    """Create an audit log entry."""
    log = AuditLog(
        user_id=user_id, action=action, target_type=target_type,
        target_id=target_id, previous_value=previous_value,
        new_value=new_value, reason=reason
    )
    db.add(log)
    db.commit()


# ─── Dashboard ────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    total_students = db.query(func.count(Student.id)).filter(Student.is_active == True).scalar()
    total_teachers = db.query(func.count(User.id)).filter(User.role == "teacher").scalar()
    total_activities = db.query(func.count(Activity.id)).scalar()
    active_sessions = db.query(func.count(ActivitySession.id)).filter(
        ActivitySession.status == "active"
    ).scalar()
    recent_activities = db.query(Activity).order_by(desc(Activity.updated_at)).limit(5).all()
    recent_logs = db.query(AuditLog).options(joinedload(AuditLog.user)).order_by(
        desc(AuditLog.created_at)
    ).limit(10).all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": user,
        "total_students": total_students, "total_teachers": total_teachers,
        "total_activities": total_activities, "active_sessions": active_sessions,
        "recent_activities": recent_activities, "recent_logs": recent_logs,
    })


# ─── Student Management ──────────────────────────────────────────────

@router.get("/students", response_class=HTMLResponse)
async def students_list(
    request: Request,
    search: str = Query("", alias="search"),
    grade: str = Query("", alias="grade"),
    room: str = Query("", alias="room"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    per_page = 50
    query = db.query(Student).filter(Student.is_active == True)
    if search:
        query = query.filter(or_(
            Student.student_id.contains(search),
            Student.full_name.contains(search)
        ))
    if grade:
        query = query.filter(Student.grade == grade)
    if room:
        query = query.filter(Student.room == room)

    total = query.count()
    students = query.order_by(Student.grade, cast(Student.room, Integer), Student.student_id).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    # Get distinct rooms for filter sorted numerically
    raw_rooms = [r[0] for r in db.query(Student.room).filter(Student.room != None).distinct().all()]
    rooms = sorted(raw_rooms, key=lambda x: int(x) if str(x).isdigit() else 99999)

    return templates.TemplateResponse("admin/students.html", {
        "request": request, "user": user,
        "students": students, "total": total,
        "search": search, "grade": grade, "room_filter": room,
        "grades": VALID_GRADES, "rooms": rooms,
        "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@router.get("/students/add", response_class=HTMLResponse)
async def student_add_form(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/student_form.html", {
        "request": request, "user": user, "student": None,
        "grades": VALID_GRADES, "error": None,
    })


@router.post("/students/add", response_class=HTMLResponse)
async def student_add_submit(
    request: Request,
    student_id: str = Form(...),
    full_name: str = Form(...),
    grade: str = Form(...),
    room: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    # Check duplicate
    existing = db.query(Student).filter(Student.student_id == student_id).first()
    if existing:
        return templates.TemplateResponse("admin/student_form.html", {
            "request": request, "user": user, "student": None,
            "grades": VALID_GRADES,
            "error": f"Student ID {student_id} already exists.",
        })

    student = Student(student_id=student_id, full_name=full_name, grade=grade, room=room)
    db.add(student)
    db.commit()
    create_audit_log(db, user.id, "student_created", "student", student_id,
                     new_value=json.dumps({"name": full_name, "grade": grade, "room": room}))
    return RedirectResponse(url="/admin/students", status_code=303)


@router.get("/students/{id}/edit", response_class=HTMLResponse)
async def student_edit_form(
    id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return templates.TemplateResponse("admin/student_form.html", {
        "request": request, "user": user, "student": student,
        "grades": VALID_GRADES, "error": None,
    })


@router.post("/students/{id}/edit", response_class=HTMLResponse)
async def student_edit_submit(
    id: int, request: Request,
    student_id: str = Form(...),
    full_name: str = Form(...),
    grade: str = Form(...),
    room: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check for duplicate student_id if changed
    if student.student_id != student_id:
        existing = db.query(Student).filter(Student.student_id == student_id, Student.id != id).first()
        if existing:
            return templates.TemplateResponse("admin/student_form.html", {
                "request": request, "user": user, "student": student,
                "grades": VALID_GRADES,
                "error": f"Student ID {student_id} already exists.",
            })

    prev = json.dumps({"id": student.student_id, "name": student.full_name, "grade": student.grade, "room": student.room})
    student.student_id = student_id
    student.full_name = full_name
    student.grade = grade
    student.room = room
    db.commit()
    new = json.dumps({"id": student_id, "name": full_name, "grade": grade, "room": room})
    create_audit_log(db, user.id, "student_edited", "student", student_id,
                     previous_value=prev, new_value=new)
    return RedirectResponse(url="/admin/students", status_code=303)


@router.post("/students/{id}/delete")
async def student_delete(
    id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.is_active = False
    db.commit()
    create_audit_log(db, user.id, "student_deactivated", "student", student.student_id)
    return RedirectResponse(url="/admin/students", status_code=303)


@router.post("/students/delete-all")
async def students_delete_all(
    db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    # Find all students with attendance records
    students_with_attendance_subq = db.query(AttendanceRecord.student_id).distinct().subquery()
    
    # 1. Physically delete students with NO attendance records
    db.query(Student).filter(Student.id.notin_(students_with_attendance_subq)).delete(synchronize_session=False)
    
    # 2. Soft delete students WITH attendance records (is_active = False)
    db.query(Student).filter(Student.id.in_(students_with_attendance_subq)).update({"is_active": False}, synchronize_session=False)
    
    db.commit()
    
    create_audit_log(db, user.id, "students_deleted_all", "student", "all")
    
    return RedirectResponse(url="/admin/students?success=deleted_all", status_code=303)


# ─── Excel Import ────────────────────────────────────────────────────

@router.get("/students/import", response_class=HTMLResponse)
async def import_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/student_import.html", {
        "request": request, "user": user,
        "preview": None, "errors": None, "summary": None,
    })


@router.post("/students/import/preview", response_class=HTMLResponse)
async def import_preview(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Read uploaded Excel, validate, and show preview."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        return templates.TemplateResponse("admin/student_import.html", {
            "request": request, "user": user,
            "preview": None, "summary": None,
            "errors": [{"row": 0, "message": "Please upload an Excel file (.xlsx)"}],
        })

    try:
        content = await file.read()
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        return templates.TemplateResponse("admin/student_import.html", {
            "request": request, "user": user,
            "preview": None, "summary": None,
            "errors": [{"row": 0, "message": f"Unable to read this Excel file: {str(e)}"}],
        })

    records = []
    errors = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        # Detect headers
        headers = [str(h).strip().lower() if h else "" for h in rows[0]]

        has_student_id = "student_id" in headers or "studentid" in headers or "id" in headers or "รหัสนักเรียน" in headers
        has_name = "full_name" in headers or "fullname" in headers or "name" in headers or "ชื่อ-สกุล" in headers or "ชื่อ" in headers
        has_room = "room" in headers or "ห้อง" in headers or "class" in headers

        if not has_student_id or not has_name:
            # Try if first row is data, not header (for sheets with name like M.1)
            # Check if sheet name looks like a grade
            is_grade_sheet = sheet_name.strip() in VALID_GRADES or sheet_name.strip().replace(".", "").replace(" ", "").upper().startswith("M")
            if not is_grade_sheet:
                continue
            # Try treating first row as data with positional columns
            # Assume: student_id, full_name, room (if 3 cols) or student_id, full_name (if 2 cols)
            errors.append({
                "row": 0,
                "message": f"Sheet '{sheet_name}': Cannot identify required columns (student_id, full_name). Skipping."
            })
            continue

        # Map column indices
        def find_col(names):
            for n in names:
                if n in headers:
                    return headers.index(n)
            return None

        id_col = find_col(["student_id", "studentid", "id", "รหัสนักเรียน"])
        name_col = find_col(["full_name", "fullname", "name", "ชื่อ-สกุล", "ชื่อ"])
        grade_col = find_col(["grade", "ระดับชั้น", "ชั้น"])
        room_col = find_col(["room", "ห้อง", "class"])

        # Infer grade from sheet name if missing
        inferred_grade = None
        if grade_col is None:
            normalized = sheet_name.strip()
            if normalized in VALID_GRADES:
                inferred_grade = normalized
            else:
                # Try matching M1 -> M.1
                for g in VALID_GRADES:
                    if normalized.replace(".", "").replace(" ", "").upper() == g.replace(".", "").upper():
                        inferred_grade = g
                        break

        for row_idx, row in enumerate(rows[1:], start=2):
            if all(cell is None for cell in row):
                continue  # skip empty rows

            sid = str(row[id_col]).strip() if id_col is not None and row[id_col] is not None else None
            name = str(row[name_col]).strip() if name_col is not None and row[name_col] is not None else None
            grade = str(row[grade_col]).strip() if grade_col is not None and row[grade_col] is not None else inferred_grade
            room = str(row[room_col]).strip() if room_col is not None and row[room_col] is not None else ""

            # Validate
            if not sid:
                errors.append({"row": row_idx, "message": f"Sheet '{sheet_name}', row {row_idx}: Missing student_id"})
                continue
            if not name:
                errors.append({"row": row_idx, "message": f"Sheet '{sheet_name}', row {row_idx}: Missing full_name"})
                continue
            if not grade:
                errors.append({"row": row_idx, "message": f"Sheet '{sheet_name}', row {row_idx}: Missing grade"})
                continue

            # Clean student_id — remove .0 from numeric Excel values
            if sid.endswith(".0"):
                sid = sid[:-2]

            # Validate grade
            if grade not in VALID_GRADES:
                errors.append({"row": row_idx, "message": f"Sheet '{sheet_name}', row {row_idx}: Invalid grade '{grade}'"})
                continue

            # Clean room
            if room.endswith(".0"):
                room = room[:-2]
            if not room:
                room = "-"

            records.append({
                "student_id": sid,
                "full_name": name,
                "grade": grade,
                "room": room,
                "sheet": sheet_name,
                "row": row_idx,
            })

    wb.close()

    # Check duplicates within import
    seen_ids = {}
    deduped_records = []
    for rec in records:
        if rec["student_id"] in seen_ids:
            errors.append({
                "row": rec["row"],
                "message": f"Duplicate student_id '{rec['student_id']}' in sheet '{rec['sheet']}' row {rec['row']} "
                           f"(first seen at row {seen_ids[rec['student_id']]})"
            })
        else:
            seen_ids[rec["student_id"]] = rec["row"]
            deduped_records.append(rec)

    # Check existing in DB
    existing_ids = {s.student_id for s in db.query(Student.student_id).all()}
    new_records = [r for r in deduped_records if r["student_id"] not in existing_ids]
    update_records = [r for r in deduped_records if r["student_id"] in existing_ids]

    # Store preview in session via a temp mechanism — we'll use a hidden form approach
    import_data = json.dumps(deduped_records)

    return templates.TemplateResponse("admin/student_import.html", {
        "request": request, "user": user,
        "preview": deduped_records,
        "new_count": len(new_records),
        "update_count": len(update_records),
        "errors": errors if errors else None,
        "import_data": import_data,
        "summary": None,
    })


@router.post("/students/import/confirm", response_class=HTMLResponse)
async def import_confirm(
    request: Request,
    import_data: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Actually import the previewed records."""
    try:
        records = json.loads(import_data)
    except Exception:
        return RedirectResponse(url="/admin/students/import", status_code=303)

    imported = 0
    updated = 0
    skipped = 0

    for rec in records:
        existing = db.query(Student).filter(Student.student_id == rec["student_id"]).first()
        if existing:
            existing.full_name = rec["full_name"]
            existing.grade = rec["grade"]
            existing.room = rec["room"]
            existing.is_active = True
            updated += 1
        else:
            student = Student(
                student_id=rec["student_id"],
                full_name=rec["full_name"],
                grade=rec["grade"],
                room=rec["room"],
            )
            db.add(student)
            imported += 1

    db.commit()
    create_audit_log(db, user.id, "students_imported", "student", None,
                     new_value=json.dumps({"imported": imported, "updated": updated}))

    return templates.TemplateResponse("admin/student_import.html", {
        "request": request, "user": user,
        "preview": None, "errors": None, "import_data": None,
        "summary": {"imported": imported, "updated": updated, "skipped": skipped},
    })


@router.get("/students/template")
async def download_template(user: User = Depends(require_admin)):
    """Download the Excel template for student import."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    ws.append(["student_id", "full_name", "grade", "room"])
    ws.append(["64001", "Student One", "M.1", "1"])
    ws.append(["65001", "Student Two", "M.2", "1"])
    ws.append(["66001", "Student Three", "M.3", "5"])

    # Style the header
    from openpyxl.styles import Font, PatternFill
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    # Set column widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 10

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=students_template.xlsx"}
    )


# ─── Teacher Management ──────────────────────────────────────────────

@router.get("/teachers", response_class=HTMLResponse)
async def teachers_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    teachers = db.query(User).filter(User.role == "teacher").order_by(User.username).all()
    return templates.TemplateResponse("admin/teachers.html", {
        "request": request, "user": user, "teachers": teachers, "error": None, "success": None,
    })


@router.post("/teachers/add", response_class=HTMLResponse)
async def teacher_add(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        teachers = db.query(User).filter(User.role == "teacher").order_by(User.username).all()
        return templates.TemplateResponse("admin/teachers.html", {
            "request": request, "user": user, "teachers": teachers,
            "error": f"Username '{username}' already exists.", "success": None,
        })
    teacher = User(
        username=username, display_name=display_name,
        password_hash=hash_password(password), role="teacher"
    )
    db.add(teacher)
    db.commit()
    create_audit_log(db, user.id, "teacher_created", "user", username)
    return RedirectResponse(url="/admin/teachers", status_code=303)


@router.post("/teachers/{id}/toggle")
async def teacher_toggle(id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    teacher = db.query(User).filter(User.id == id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404)
    prev = teacher.is_active
    teacher.is_active = not teacher.is_active
    db.commit()
    create_audit_log(db, user.id, "teacher_toggled", "user", teacher.username,
                     previous_value=str(prev), new_value=str(teacher.is_active))
    return RedirectResponse(url="/admin/teachers", status_code=303)


@router.post("/teachers/{id}/reset-password")
async def teacher_reset_password(
    id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    teacher = db.query(User).filter(User.id == id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404)
    teacher.password_hash = hash_password(new_password)
    db.commit()
    create_audit_log(db, user.id, "teacher_password_reset", "user", teacher.username)
    return RedirectResponse(url="/admin/teachers", status_code=303)

@router.post("/teachers/{id}/edit")
async def teacher_edit(
    request: Request,
    id: int,
    username: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    teacher = db.query(User).filter(User.id == id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404)
        
    # Check if username is changed and already exists
    if teacher.username != username:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            # We can use the error query param or render the template
            # For simplicity, returning a redirect with an error query param
            return RedirectResponse(url=f"/admin/teachers?error=duplicate_username", status_code=303)
            
    teacher.username = username
    teacher.display_name = display_name
    db.commit()
    create_audit_log(db, user.id, "teacher_edited", "user", teacher.username)
    return RedirectResponse(url="/admin/teachers?success=edited", status_code=303)


@router.post("/teachers/{id}/delete")
async def teacher_delete(
    id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    teacher = db.query(User).filter(User.id == id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404)
        
    username = teacher.username
    db.delete(teacher)
    db.commit()
    create_audit_log(db, user.id, "teacher_deleted", "user", username)
    
    return RedirectResponse(url="/admin/teachers?success=deleted", status_code=303)


# ─── Activity Management ─────────────────────────────────────────────

@router.get("/activities", response_class=HTMLResponse)
async def activities_list(
    request: Request,
    status_filter: str = Query("", alias="status"),
    error: str = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    query = db.query(Activity).order_by(desc(Activity.updated_at))
    if status_filter:
        query = query.filter(Activity.status == status_filter)
    activities = query.all()
    error_msg = None
    if error == "cannot_delete_active":
        error_msg = "ไม่สามารถลบกิจกรรมที่มีรอบกำลังเปิดใช้งานอยู่ได้"
    elif error:
        error_msg = error

    return templates.TemplateResponse("admin/activities.html", {
        "request": request, "user": user, "activities": activities,
        "status_filter": status_filter, "error": error_msg,
    })


@router.get("/activities/add", response_class=HTMLResponse)
async def activity_add_form(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/activity_form.html", {
        "request": request, "user": user, "activity": None,
        "grades": VALID_GRADES, "error": None,
    })


@router.post("/activities/add")
async def activity_add_submit(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    status: str = Form("draft"),
    eligible_grades: list = Form(None, alias="eligible_grades"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    activity = Activity(
        name=name, description=description,
        start_date=date.fromisoformat(start_date) if start_date else None,
        end_date=date.fromisoformat(end_date) if end_date else None,
        status=status,
        eligible_grades=",".join(eligible_grades) if eligible_grades else None,
    )
    db.add(activity)
    db.commit()
    create_audit_log(db, user.id, "activity_created", "activity", str(activity.id),
                     new_value=json.dumps({"name": name}))
    return RedirectResponse(url="/admin/activities", status_code=303)


@router.get("/activities/{id}/edit", response_class=HTMLResponse)
async def activity_edit_form(
    id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/activity_form.html", {
        "request": request, "user": user, "activity": activity,
        "grades": VALID_GRADES, "error": None,
    })


@router.post("/activities/{id}/edit")
async def activity_edit_submit(
    id: int, request: Request,
    name: str = Form(...),
    description: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    status: str = Form("draft"),
    eligible_grades: list = Form(None, alias="eligible_grades"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(status_code=404)

    prev = json.dumps({"name": activity.name, "status": activity.status})
    activity.name = name
    activity.description = description
    activity.start_date = date.fromisoformat(start_date) if start_date else None
    activity.end_date = date.fromisoformat(end_date) if end_date else None
    activity.status = status
    activity.eligible_grades = ",".join(eligible_grades) if eligible_grades else None
    db.commit()
    create_audit_log(db, user.id, "activity_edited", "activity", str(id),
                     previous_value=prev, new_value=json.dumps({"name": name, "status": status}))
    return RedirectResponse(url="/admin/activities", status_code=303)


@router.post("/activities/{id}/delete")
async def activity_delete(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check for active sessions
    active = db.query(ActivitySession).filter(
        ActivitySession.activity_id == id,
        ActivitySession.status == "active"
    ).first()
    if active:
        return RedirectResponse(url="/admin/activities?error=cannot_delete_active", status_code=303)

    act_name = activity.name
    db.delete(activity)
    db.commit()
    create_audit_log(db, user.id, "activity_deleted", "activity", str(id),
                     previous_value=json.dumps({"name": act_name}))
    return RedirectResponse(url="/admin/activities", status_code=303)


# ─── Session Management ──────────────────────────────────────────────

@router.get("/activities/{activity_id}/sessions", response_class=HTMLResponse)
async def sessions_list(
    activity_id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404)
    sessions = db.query(ActivitySession).filter(
        ActivitySession.activity_id == activity_id
    ).order_by(ActivitySession.date, ActivitySession.start_time).all()

    # Get attendance counts per session
    session_stats = {}
    for sess in sessions:
        count = db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.session_id == sess.id
        ).scalar()
        session_stats[sess.id] = count

    return templates.TemplateResponse("admin/sessions.html", {
        "request": request, "user": user,
        "activity": activity, "sessions": sessions,
        "session_stats": session_stats,
    })


@router.post("/activities/{activity_id}/sessions/add")
async def session_add(
    activity_id: int,
    name: str = Form(...),
    session_date: str = Form(...),
    start_time: str = Form(""),
    end_time: str = Form(""),
    status: str = Form("draft"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    session = ActivitySession(
        activity_id=activity_id, name=name,
        date=date.fromisoformat(session_date),
        start_time=time.fromisoformat(start_time) if start_time else None,
        end_time=time.fromisoformat(end_time) if end_time else None,
        status=status,
    )
    db.add(session)
    db.commit()
    create_audit_log(db, user.id, "session_created", "session", str(session.id),
                     new_value=json.dumps({"name": name, "activity_id": activity_id}))
    return RedirectResponse(url=f"/admin/activities/{activity_id}/sessions", status_code=303)


@router.post("/sessions/{id}/edit")
async def session_edit(
    id: int,
    name: str = Form(...),
    session_date: str = Form(...),
    start_time: str = Form(""),
    end_time: str = Form(""),
    status: str = Form("draft"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    session = db.query(ActivitySession).filter(ActivitySession.id == id).first()
    if not session:
        raise HTTPException(status_code=404)

    session.name = name
    session.date = date.fromisoformat(session_date)
    session.start_time = time.fromisoformat(start_time) if start_time else None
    session.end_time = time.fromisoformat(end_time) if end_time else None
    session.status = status
    db.commit()
    return RedirectResponse(url=f"/admin/activities/{session.activity_id}/sessions", status_code=303)


@router.post("/sessions/{id}/delete")
async def session_delete(
    id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    session = db.query(ActivitySession).filter(ActivitySession.id == id).first()
    if not session:
        raise HTTPException(status_code=404)
    activity_id = session.activity_id
    db.delete(session)
    db.commit()
    return RedirectResponse(url=f"/admin/activities/{activity_id}/sessions", status_code=303)


# ─── Attendance Management ───────────────────────────────────────────

@router.get("/attendance", response_class=HTMLResponse)
async def attendance_list(
    request: Request,
    activity_id: int = Query(0),
    session_id: int = Query(0),
    grade: str = Query(""),
    room: str = Query(""),
    search: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    activities = db.query(Activity).order_by(desc(Activity.updated_at)).all()
    sessions = []
    records = []
    selected_session = None

    if activity_id:
        sessions = db.query(ActivitySession).filter(
            ActivitySession.activity_id == activity_id
        ).order_by(ActivitySession.date).all()

    if session_id:
        selected_session = db.query(ActivitySession).filter(ActivitySession.id == session_id).first()
        query = db.query(AttendanceRecord).options(
            joinedload(AttendanceRecord.student)
        ).filter(AttendanceRecord.session_id == session_id)

        if grade:
            query = query.join(Student).filter(Student.grade == grade)
        if room:
            query = query.join(Student, isouter=True).filter(Student.room == room)
        if search:
            query = query.join(Student, isouter=True).filter(
                or_(Student.student_id.contains(search), Student.full_name.contains(search))
            )

        records = query.order_by(AttendanceRecord.checked_in_at).all()

    return templates.TemplateResponse("admin/attendance.html", {
        "request": request, "user": user,
        "activities": activities, "sessions": sessions,
        "records": records, "selected_session": selected_session,
        "activity_id": activity_id, "session_id": session_id,
        "grade": grade, "room_filter": room, "search": search,
        "grades": VALID_GRADES,
    })


@router.post("/attendance/{id}/correct")
async def attendance_correct(
    id: int,
    status: str = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == id).first()
    if not record:
        raise HTTPException(status_code=404)
    prev_status = record.status
    record.status = status
    record.checked_in_method = "manual"
    db.commit()
    create_audit_log(db, user.id, "attendance_corrected", "attendance", str(id),
                     previous_value=prev_status, new_value=status, reason=reason)
    return RedirectResponse(url=f"/admin/attendance?session_id={record.session_id}", status_code=303)


@router.post("/attendance/manual-add")
async def attendance_manual_add(
    session_id: int = Form(...),
    student_db_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Manually add attendance for a student who couldn't check in via QR.
    
    NOTE: This operation is intentionally NOT logged to the audit log /
    system usage history. It is a data-management operation only.
    """
    from fastapi.responses import JSONResponse

    # Check if already exists
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student_db_id,
        AttendanceRecord.session_id == session_id
    ).first()
    if existing:
        student = db.query(Student).filter(Student.id == student_db_id).first()
        return JSONResponse(status_code=409, content={
            "success": False,
            "message": "นักเรียนคนนี้เช็คชื่อกิจกรรมนี้แล้ว",
            "already_exists": True,
        })

    record = AttendanceRecord(
        student_id=student_db_id,
        session_id=session_id,
        status="present",
        checked_in_method="admin_manual",
        checked_in_at=get_bkk_time(),
    )
    db.add(record)
    db.commit()

    student = db.query(Student).filter(Student.id == student_db_id).first()
    return JSONResponse(status_code=200, content={
        "success": True,
        "message": "เพิ่มรายชื่อนักเรียนเรียบร้อยแล้ว",
        "student": {
            "student_id": student.student_id if student else "",
            "full_name": student.full_name if student else "",
        }
    })


@router.get("/attendance/students-search")
async def attendance_students_search(
    session_id: int = Query(...),
    q: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Search for students to manually add to attendance.
    Returns students who are eligible for the session and NOT yet checked in.
    """
    from fastapi.responses import JSONResponse

    # Load session to find eligible grades
    session = db.query(ActivitySession).options(
        joinedload(ActivitySession.activity)
    ).filter(ActivitySession.id == session_id).first()
    if not session:
        return JSONResponse(status_code=404, content={"students": []})

    # Get already checked-in student IDs
    checked_in_ids = [
        r.student_id for r in
        db.query(AttendanceRecord.student_id).filter(
            AttendanceRecord.session_id == session_id
        ).all()
    ]

    query = db.query(Student).filter(Student.is_active == True)

    # Filter by eligible grades
    if session.activity.eligible_grades:
        grades = [g.strip() for g in session.activity.eligible_grades.split(",")]
        query = query.filter(Student.grade.in_(grades))

    # Search filter
    if q and len(q.strip()) >= 1:
        query = query.filter(
            or_(Student.student_id.contains(q.strip()),
                Student.full_name.contains(q.strip()))
        )

    students = query.order_by(Student.grade, Student.room, Student.student_id).limit(30).all()

    result = []
    for s in students:
        result.append({
            "db_id": s.id,
            "student_id": s.student_id,
            "full_name": s.full_name,
            "grade": s.grade,
            "room": s.room,
            "already_checked_in": s.id in checked_in_ids,
        })

    return {"students": result, "session_name": session.name, "activity_name": session.activity.name}


# ─── Student Attendance History ───────────────────────────────────────

@router.get("/students/{id}/history", response_class=HTMLResponse)
async def student_history(
    id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404)
    records = db.query(AttendanceRecord).options(
        joinedload(AttendanceRecord.session).joinedload(ActivitySession.activity)
    ).filter(
        AttendanceRecord.student_id == id
    ).order_by(desc(AttendanceRecord.checked_in_at)).all()

    return templates.TemplateResponse("admin/student_history.html", {
        "request": request, "user": user,
        "student": student, "records": records,
    })


# ─── Reports & Excel Export ──────────────────────────────────────────

@router.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    activities = db.query(Activity).order_by(desc(Activity.updated_at)).all()
    return templates.TemplateResponse("admin/reports.html", {
        "request": request, "user": user, "activities": activities,
        "grades": VALID_GRADES,
    })


@router.get("/reports/export")
async def export_attendance(
    request: Request,
    session_id: int = Query(0),
    activity_id: int = Query(0),
    grade: str = Query(""),
    room: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Export attendance to Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    from openpyxl.styles import Font, PatternFill, Alignment

    # Header style
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")

    # Build query
    if session_id:
        session = db.query(ActivitySession).options(
            joinedload(ActivitySession.activity)
        ).filter(ActivitySession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404)

        safe_session_title = re.sub(r'[\\/*?:\[\]]', '_', session.name).strip()[:31] or "Session"
        ws.title = safe_session_title

        # Get all eligible students
        student_query = db.query(Student).filter(Student.is_active == True)
        if session.activity.eligible_grades:
            grades_list = [g.strip() for g in session.activity.eligible_grades.split(",")]
            student_query = student_query.filter(Student.grade.in_(grades_list))
        if grade:
            student_query = student_query.filter(Student.grade == grade)
        if room:
            student_query = student_query.filter(Student.room == room)

        students = student_query.order_by(Student.grade, Student.room, Student.student_id).all()

        # Get attendance records
        attendance_map = {}
        for rec in db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id).all():
            attendance_map[rec.student_id] = rec

        # Summary row
        ws.append([f"Activity: {session.activity.name}"])
        ws.append([f"Session: {session.name} — {session.date}"])
        ws.append([])

        # Headers
        headers = ["Student ID", "Full Name", "Grade", "Room", "Status", "Check-in Time", "Method"]
        ws.append(headers)
        for col, cell in enumerate(ws[4], 1):
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        present_count = 0
        for student in students:
            rec = attendance_map.get(student.id)
            if rec:
                status_text = "Present"
                checkin_time = rec.checked_in_at.strftime("%H:%M:%S") if rec.checked_in_at else "-"
                method = rec.checked_in_method
                if method in ("admin_manual", "qr"):
                    method = "QR Scan" if request.cookies.get("app_language", "th") == "en" else "สแกน QR"
                present_count += 1
            else:
                status_text = "Not Checked In"
                checkin_time = "-"
                method = "-"
            ws.append([student.student_id, student.full_name, student.grade, student.room,
                       status_text, checkin_time, method])

        # Summary
        ws.append([])
        ws.append(["Summary"])
        ws.append(["Total Students", len(students)])
        ws.append(["Present", present_count])
        ws.append(["Not Checked In", len(students) - present_count])
        pct = (present_count / len(students) * 100) if students else 0
        ws.append(["Attendance %", f"{pct:.1f}%"])

    elif activity_id:
        activity = db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404)
        sessions = db.query(ActivitySession).filter(
            ActivitySession.activity_id == activity_id
        ).order_by(ActivitySession.date).all()

        safe_activity_title = re.sub(r'[\\/*?:\[\]]', '_', activity.name).strip()[:31] or "Activity"
        ws.title = safe_activity_title
        ws.append([f"Activity: {activity.name}"])
        ws.append([])

        headers = ["Student ID", "Full Name", "Grade", "Room"] + [s.name for s in sessions]
        ws.append(headers)
        for col, cell in enumerate(ws[3], 1):
            cell.font = header_font
            cell.fill = header_fill

        student_query = db.query(Student).filter(Student.is_active == True)
        if activity.eligible_grades:
            grades_list = [g.strip() for g in activity.eligible_grades.split(",")]
            student_query = student_query.filter(Student.grade.in_(grades_list))
        if grade:
            student_query = student_query.filter(Student.grade == grade)
        students = student_query.order_by(Student.grade, Student.room, Student.student_id).all()

        # Build attendance map: {student_id: {session_id: record}}
        all_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.session_id.in_([s.id for s in sessions])
        ).all()
        att_map = {}
        for rec in all_records:
            att_map.setdefault(rec.student_id, {})[rec.session_id] = rec

        for student in students:
            row = [student.student_id, student.full_name, student.grade, student.room]
            for sess in sessions:
                rec = att_map.get(student.id, {}).get(sess.id)
                row.append("✓" if rec else "✗")
            ws.append(row)

    # Set column widths
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 4, 40)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"attendance_report_{get_bkk_time().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─── Audit Logs ──────────────────────────────────────────────────────

@router.get("/audit-logs", response_class=HTMLResponse)
async def audit_logs_page(
    request: Request,
    action: str = Query(""),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    per_page = 50
    query = db.query(AuditLog).options(joinedload(AuditLog.user))
    if action:
        query = query.filter(AuditLog.action.contains(action))
    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    return templates.TemplateResponse("admin/audit_logs.html", {
        "request": request, "user": user,
        "logs": logs, "total": total,
        "action_filter": action, "page": page,
        "per_page": per_page, "total_pages": (total + per_page - 1) // per_page,
    })


# ─── API endpoints for AJAX ──────────────────────────────────────────

@router.get("/api/sessions/{activity_id}")
async def api_get_sessions(activity_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Return sessions for an activity as JSON (for dynamic dropdowns)."""
    sessions = db.query(ActivitySession).filter(
        ActivitySession.activity_id == activity_id
    ).order_by(ActivitySession.date).all()
    return [{"id": s.id, "name": s.name, "date": str(s.date), "status": s.status} for s in sessions]
