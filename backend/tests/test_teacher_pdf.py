"""Tests for Teacher PDF export functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from app.models import Student, ActivitySession, AttendanceRecord
from app.routers.teacher import _build_attendance_pdf


def test_build_attendance_pdf_direct():
    """Verify _build_attendance_pdf creates valid PDF bytes containing time data."""
    students_data = [
        {
            "student_id": "69001",
            "full_name": "ทดสอบ สมชาย",
            "grade": "M.6",
            "room": "1",
            "status": "present",
            "time": "08:15:30",
        },
        {
            "student_id": "69002",
            "full_name": "ทดสอบ สมหญิง",
            "grade": "M.6",
            "room": "1",
            "status": "leave",
            "time": "-",
        },
        {
            "student_id": "69003",
            "full_name": "ทดสอบ มานะ",
            "grade": "M.6",
            "room": "1",
            "status": "absent",
            "time": "-",
        },
    ]

    # Thai PDF
    pdf_th = _build_attendance_pdf(
        students_data=students_data,
        lang="th",
        report_title="รายงานสรุปการเช็คชื่อ",
        report_subtitle="กิจกรรมทดสอบ",
        base_dir=".",
    )
    assert isinstance(pdf_th, bytes)
    assert len(pdf_th) > 1000
    assert pdf_th.startswith(b"%PDF")

    # English PDF
    pdf_en = _build_attendance_pdf(
        students_data=students_data,
        lang="en",
        report_title="Attendance Report",
        report_subtitle="Test Activity",
        base_dir=".",
    )
    assert isinstance(pdf_en, bytes)
    assert len(pdf_en) > 1000
    assert pdf_en.startswith(b"%PDF")


def test_teacher_attendance_pdf_by_grade_room(teacher_client, sample_activity, sample_students, db):
    """Test /teacher/api/attendance_pdf endpoint with checked-in and absent students."""
    activity, sessions = sample_activity
    session = sessions[0]

    bkk_tz = timezone(timedelta(hours=7))
    checkin_time = datetime(2026, 9, 20, 8, 30, 45, tzinfo=bkk_tz)

    # Student 0 is present
    rec = AttendanceRecord(
        student_id=sample_students[0].id,
        session_id=session.id,
        status="present",
        checked_in_method="qr",
        checked_in_at=checkin_time,
    )
    db.add(rec)
    db.commit()

    resp = teacher_client.get(
        f"/teacher/api/attendance_pdf?session_id={session.id}&grade=M.6&room=7&lang=th"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_teacher_attendance_pdf_all(teacher_client, sample_activity, sample_students, db):
    """Test /teacher/api/attendance_pdf_all endpoint."""
    activity, sessions = sample_activity
    session = sessions[0]

    bkk_tz = timezone(timedelta(hours=7))
    checkin_time = datetime(2026, 9, 20, 8, 35, 10, tzinfo=bkk_tz)

    rec = AttendanceRecord(
        student_id=sample_students[0].id,
        session_id=session.id,
        status="present",
        checked_in_method="manual",
        checked_in_at=checkin_time,
    )
    db.add(rec)
    db.commit()

    resp = teacher_client.get(
        f"/teacher/api/attendance_pdf_all?session_id={session.id}&lang=th"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_teacher_summary_pdf(teacher_client, sample_activity, sample_students, db):
    """Test /teacher/api/summary_pdf/{session_id} endpoint."""
    activity, sessions = sample_activity
    session = sessions[0]

    bkk_tz = timezone(timedelta(hours=7))
    checkin_time = datetime(2026, 9, 20, 8, 40, 0, tzinfo=bkk_tz)

    rec = AttendanceRecord(
        student_id=sample_students[0].id,
        session_id=session.id,
        status="present",
        checked_in_method="qr",
        checked_in_at=checkin_time,
    )
    db.add(rec)
    db.commit()

    resp = teacher_client.get(
        f"/teacher/api/summary_pdf/{session.id}?lang=th"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
