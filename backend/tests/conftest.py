"""Test fixtures and configuration."""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.models import User, Student, Activity, ActivitySession
from app.auth import hash_password
from app.main import app


# Test database — in-memory SQLite
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a test HTTP client."""
    return TestClient(app)


@pytest.fixture
def admin_user(db):
    """Create an admin user and return it."""
    user = User(
        username="admin",
        password_hash=hash_password("admin123"),
        display_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def teacher_user(db):
    """Create a teacher user and return it."""
    user = User(
        username="teacher1",
        password_hash=hash_password("teacher123"),
        display_name="Test Teacher",
        role="teacher",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_students(db):
    """Create sample students."""
    students = []
    for i, (sid, name, grade, room) in enumerate([
        ("69001", "Student One", "M.6", "7"),
        ("69002", "Student Two", "M.6", "7"),
        ("68001", "Student Three", "M.5", "3"),
        ("67001", "Student Four", "M.4", "2"),
        ("66001", "Student Five", "M.3", "5"),
    ]):
        s = Student(student_id=sid, full_name=name, grade=grade, room=room)
        db.add(s)
        students.append(s)
    db.commit()
    for s in students:
        db.refresh(s)
    return students


@pytest.fixture
def sample_activity(db):
    """Create a sample activity with sessions."""
    from datetime import date, time
    activity = Activity(
        name="Sports Day 2026",
        description="Annual sports day",
        start_date=date(2026, 9, 20),
        end_date=date(2026, 9, 21),
        status="active",
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    session1 = ActivitySession(
        activity_id=activity.id,
        name="Day 1 Morning",
        date=date(2026, 9, 20),
        start_time=time(8, 0),
        end_time=time(12, 0),
        status="active",
    )
    session2 = ActivitySession(
        activity_id=activity.id,
        name="Day 1 Afternoon",
        date=date(2026, 9, 20),
        start_time=time(13, 0),
        end_time=time(16, 0),
        status="active",
    )
    db.add_all([session1, session2])
    db.commit()
    db.refresh(session1)
    db.refresh(session2)

    return activity, [session1, session2]


@pytest.fixture
def admin_client(client, admin_user):
    """Client logged in as admin."""
    response = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
    client.cookies = response.cookies
    return client


@pytest.fixture
def teacher_client(client, teacher_user):
    """Client logged in as teacher."""
    response = client.post("/login", data={"username": "teacher1", "password": "teacher123"}, follow_redirects=False)
    client.cookies = response.cookies
    return client
