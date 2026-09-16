"""Tests for authentication, role authorization, and login."""

import pytest
from app.models import User
from app.auth import hash_password


def test_login_page_loads(client):
    """Login page should render successfully."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign In" in response.text


def test_login_success_admin(client, admin_user):
    """Admin should be redirected to admin dashboard after login."""
    response = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/dashboard" in response.headers["location"]
    assert "access_token" in response.cookies


def test_login_success_teacher(client, teacher_user):
    """Teacher should be redirected to teacher dashboard after login."""
    response = client.post("/login", data={"username": "teacher1", "password": "teacher123"}, follow_redirects=False)
    assert response.status_code == 303
    assert "/teacher/dashboard" in response.headers["location"]


def test_login_invalid_password(client, admin_user):
    """Invalid password should show error."""
    response = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


def test_login_nonexistent_user(client):
    """Non-existent user should show error."""
    response = client.post("/login", data={"username": "nobody", "password": "test"})
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


def test_login_disabled_user(client, db):
    """Disabled user should not be able to login."""
    user = User(username="disabled", password_hash=hash_password("test123"),
                display_name="Disabled", role="teacher", is_active=False)
    db.add(user)
    db.commit()
    response = client.post("/login", data={"username": "disabled", "password": "test123"})
    assert "disabled" in response.text.lower() or "contact admin" in response.text.lower()


def test_admin_dashboard_requires_auth(client):
    """Admin dashboard should redirect unauthenticated users."""
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 303


def test_admin_dashboard_requires_admin_role(teacher_client):
    """Teacher should not access admin dashboard."""
    response = teacher_client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 403


def test_teacher_dashboard_accessible_by_teacher(teacher_client):
    """Teacher should access teacher dashboard."""
    response = teacher_client.get("/teacher/dashboard")
    assert response.status_code == 200


def test_teacher_dashboard_accessible_by_admin(admin_client):
    """Admin should also access teacher dashboard."""
    response = admin_client.get("/teacher/dashboard")
    assert response.status_code == 200


def test_logout(admin_client):
    """Logout should clear cookie and redirect."""
    response = admin_client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_root_redirects_to_login(client):
    """Root URL should redirect to login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (301, 302, 303, 307)
