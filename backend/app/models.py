"""SQLAlchemy ORM models for the attendance system."""

from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, Time,
    DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """Admin and Teacher accounts."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="teacher")  # admin | teacher
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")


class Student(Base):
    """Student records imported from Excel or created manually."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    grade = Column(String(10), nullable=False, index=True)
    room = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    attendance_records = relationship("AttendanceRecord", back_populates="student")

    __table_args__ = (
        Index("ix_students_grade_room", "grade", "room"),
    )


class Activity(Base):
    """Activities such as Sports Day, Workshops, etc."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    # draft | scheduled | active | completed | cancelled
    eligible_grades = Column(String(100), nullable=True)  # comma-separated: "M.1,M.2,M.3"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sessions = relationship("ActivitySession", back_populates="activity", cascade="all, delete-orphan")


class ActivitySession(Base):
    """Individual sessions within an activity."""
    __tablename__ = "activity_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    # draft | scheduled | active | completed | cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    activity = relationship("Activity", back_populates="sessions")
    attendance_records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")
    qr_tokens = relationship("QRToken", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_activity_sessions_activity_id", "activity_id"),
    )


class AttendanceRecord(Base):
    """Individual attendance records — one per student per session."""
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("activity_sessions.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="present")  # present | manual
    checked_in_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    checked_in_method = Column(String(20), nullable=False, default="qr")  # qr | manual
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    session = relationship("ActivitySession", back_populates="attendance_records")

    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="uq_attendance_student_session"),
        Index("ix_attendance_session_id", "session_id"),
        Index("ix_attendance_student_id", "student_id"),
    )


class QRToken(Base):
    """Temporary QR tokens for attendance sessions."""
    __tablename__ = "qr_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("activity_sessions.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    session = relationship("ActivitySession", back_populates="qr_tokens")


class CheckinSession(Base):
    """Temporary check-in session created after a student scans a valid QR code.

    Decouples the short-lived QR token (30s) from the student's check-in
    workflow.  A CheckinSession lives for ~3 minutes, giving the student
    enough time to select their grade, enter their ID, verify, and confirm.
    """
    __tablename__ = "checkin_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("activity_sessions.id", ondelete="CASCADE"), nullable=False)
    checkin_token = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    activity_session = relationship("ActivitySession")


class AuditLog(Base):
    """Audit trail for administrative actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(50), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action", "action"),
    )
