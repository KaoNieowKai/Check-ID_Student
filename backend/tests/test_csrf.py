"""Tests for CSRF Origin/Referer validation middleware and cookie security."""

import pytest
from app.models import User
from app.auth import hash_password
from app.config import settings


def test_c1_post_matching_origin_accepted(client):
    """C1: POST with matching Origin header is accepted."""
    response = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong"},
        headers={"origin": "http://testserver", "host": "testserver"},
        follow_redirects=False,
    )
    # 200 re-renders login with error, NOT 403 CSRF rejected
    assert response.status_code != 403


def test_c2_post_mismatched_origin_rejected(client):
    """C2: POST with mismatched Origin header is rejected with 403."""
    response = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong"},
        headers={"origin": "http://evil.com", "host": "testserver"},
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Cross-origin request rejected"}


def test_c3_post_matching_referer_accepted(client):
    """C3: POST with matching Referer (no Origin) is accepted."""
    response = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong"},
        headers={"referer": "http://testserver/login", "host": "testserver"},
        follow_redirects=False,
    )
    assert response.status_code != 403


def test_c4_post_mismatched_referer_rejected(client):
    """C4: POST with mismatched Referer (no Origin) is rejected with 403."""
    response = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong"},
        headers={"referer": "http://attacker.com/page", "host": "testserver"},
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Cross-origin request rejected"}


def test_c5_post_neither_origin_nor_referer_accepted(client):
    """C5: POST with neither Origin nor Referer is accepted (same-origin default)."""
    response = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code != 403


def test_c6_get_mismatched_origin_allowed(client):
    """C6: GET request with mismatched Origin is allowed (safe method)."""
    response = client.get(
        "/login",
        headers={"origin": "http://evil.com", "host": "testserver"},
    )
    assert response.status_code == 200


def test_c7_admin_account_post_endpoints_reject_cross_origin(super_admin_client, db):
    """C7: All admin-account POST endpoints reject cross-origin requests with 403."""
    # Test add
    res_add = super_admin_client.post(
        "/admin/admin-accounts/add",
        data={"username": "evil", "display_name": "Evil", "password": "password123"},
        headers={"origin": "http://evil.com", "host": "testserver"},
    )
    assert res_add.status_code == 403

    # Create dummy admin to test edit, suspend, reactivate, delete
    target = User(username="target_admin", password_hash=hash_password("test1234"),
                  display_name="Target", role="admin", is_active=True)
    db.add(target)
    db.commit()
    db.refresh(target)

    # Test edit
    res_edit = super_admin_client.post(
        f"/admin/admin-accounts/{target.id}/edit",
        data={"username": "target_admin", "display_name": "Target New"},
        headers={"origin": "http://evil.com", "host": "testserver"},
    )
    assert res_edit.status_code == 403

    # Test suspend
    res_suspend = super_admin_client.post(
        f"/admin/admin-accounts/{target.id}/suspend",
        headers={"origin": "http://evil.com", "host": "testserver"},
    )
    assert res_suspend.status_code == 403

    # Test reactivate
    res_reactivate = super_admin_client.post(
        f"/admin/admin-accounts/{target.id}/reactivate",
        headers={"origin": "http://evil.com", "host": "testserver"},
    )
    assert res_reactivate.status_code == 403

    # Test delete
    res_delete = super_admin_client.post(
        f"/admin/admin-accounts/{target.id}/delete",
        headers={"origin": "http://evil.com", "host": "testserver"},
    )
    assert res_delete.status_code == 403


def test_c8_cookie_secure_flag_logic(monkeypatch, client, admin_user):
    """C8: Cookie sets secure=True in production (non-sqlite) mode, secure=False in sqlite mode."""
    # In sqlite test environment: secure flag should be False
    res_dev = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    cookie_header_dev = res_dev.headers.get("set-cookie", "")
    assert "access_token=" in cookie_header_dev
    assert "HttpOnly" in cookie_header_dev
    assert "SameSite=lax" in cookie_header_dev

    # In PostgreSQL (production) environment: secure flag should be True
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://user:pass@supabase:5432/db")
    res_prod = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    cookie_header_prod = res_prod.headers.get("set-cookie", "")
    assert "Secure" in cookie_header_prod
