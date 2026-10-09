"""Tests for Admin Account Management."""

import pytest
from app.models import User
from app.auth import verify_password
from app.main import ensure_super_admin_exists

# --- Initialization Tests ---

def test_ensure_super_admin_exists_no_admin_account(db):
    """If no super_admin exists and no bootstrap admin exists, it does nothing gracefully."""
    ensure_super_admin_exists(db)
    assert db.query(User).filter(User.role == "super_admin").count() == 0

def test_ensure_super_admin_exists_promotes_bootstrap(db, monkeypatch):
    """If bootstrap admin exists and no super_admin exists, it promotes the bootstrap."""
    from app.config import settings
    
    # Create bootstrap as regular admin
    bootstrap = User(
        username=settings.ADMIN_USERNAME,
        password_hash="fakehash",
        display_name="Bootstrap",
        role="admin",
        is_active=True
    )
    db.add(bootstrap)
    db.commit()

    ensure_super_admin_exists(db)
    
    # Verify it was promoted
    db.refresh(bootstrap)
    assert bootstrap.role == "super_admin"

def test_ensure_super_admin_exists_idempotent(db, super_admin_user):
    """If a super_admin already exists, it does nothing."""
    from app.config import settings
    
    # Create a regular admin with the bootstrap username (should NOT be promoted if SA exists)
    bootstrap = User(
        username=settings.ADMIN_USERNAME,
        password_hash="fakehash",
        display_name="Bootstrap",
        role="admin",
        is_active=True
    )
    db.add(bootstrap)
    db.commit()
    
    # Call init
    ensure_super_admin_exists(db)
    
    # Verify bootstrap was NOT promoted because super_admin_user already exists
    db.refresh(bootstrap)
    assert bootstrap.role == "admin"
    assert db.query(User).filter(User.role == "super_admin").count() == 1


# --- Auth & Access Control Tests ---

def test_super_admin_can_access_dashboard(super_admin_client):
    response = super_admin_client.get("/admin/dashboard")
    assert response.status_code == 200

def test_regular_admin_can_access_dashboard(admin_client):
    response = admin_client.get("/admin/dashboard")
    assert response.status_code == 200

def test_regular_admin_forbidden_admin_accounts(admin_client):
    """Regular admin cannot access admin-accounts page."""
    response = admin_client.get("/admin/admin-accounts")
    assert response.status_code == 403

def test_regular_admin_forbidden_admin_accounts_api(admin_client, admin_user):
    """Regular admin cannot hit admin-accounts modification endpoints."""
    response = admin_client.post(
        "/admin/admin-accounts/add", 
        data={"username": "test", "display_name": "Test", "password": "password"}
    )
    assert response.status_code == 403

def test_unauthenticated_user_redirected(client):
    response = client.get("/admin/admin-accounts", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_suspended_super_admin_cannot_access(client, super_admin_user, db):
    """Even with a valid cookie, if user is suspended in DB, they lose access immediately."""
    # Login first
    response = client.post("/login", data={"username": super_admin_user.username, "password": "superadmin123"}, follow_redirects=False)
    client.cookies = response.cookies
    
    # Suspend them in DB
    super_admin_user.is_active = False
    db.commit()
    
    # Try access
    response = client.get("/admin/admin-accounts", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


# --- CRUD Tests ---

def test_list_admin_accounts(super_admin_client, admin_user):
    """Listing should show regular admins but NOT super admins."""
    response = super_admin_client.get("/admin/admin-accounts")
    assert response.status_code == 200
    html = response.text
    assert admin_user.username in html
    assert "superadmin" not in html  # super_admin_user shouldn't be listed

def test_create_admin_account(super_admin_client, db):
    response = super_admin_client.post(
        "/admin/admin-accounts/add",
        data={
            "username": "new_admin",
            "display_name": "New Admin",
            "password": "newpassword123"
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "success=created" in response.headers["location"]
    
    user = db.query(User).filter(User.username == "new_admin").first()
    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True
    assert verify_password("newpassword123", user.password_hash)

def test_create_admin_duplicate_username(super_admin_client, admin_user):
    response = super_admin_client.post(
        "/admin/admin-accounts/add",
        data={
            "username": admin_user.username,
            "display_name": "Copy Cat",
            "password": "password"
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "error=duplicate_username" in response.headers["location"]

def test_edit_admin_preserves_password(super_admin_client, admin_user, db):
    old_hash = admin_user.password_hash
    response = super_admin_client.post(
        f"/admin/admin-accounts/{admin_user.id}/edit",
        data={
            "username": "admin_test_updated",
            "display_name": "Updated Admin",
            "new_password": ""
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    db.refresh(admin_user)
    assert admin_user.username == "admin_test_updated"
    assert admin_user.display_name == "Updated Admin"
    assert admin_user.password_hash == old_hash

def test_edit_admin_changes_password(super_admin_client, admin_user, db):
    response = super_admin_client.post(
        f"/admin/admin-accounts/{admin_user.id}/edit",
        data={
            "username": admin_user.username,
            "display_name": admin_user.display_name,
            "new_password": "newsecurepassword"
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    db.refresh(admin_user)
    assert verify_password("newsecurepassword", admin_user.password_hash)

def test_edit_admin_prevents_role_change(super_admin_client, admin_user, db):
    """Client cannot inject role modifications."""
    response = super_admin_client.post(
        f"/admin/admin-accounts/{admin_user.id}/edit",
        data={
            "username": admin_user.username,
            "display_name": admin_user.display_name,
            "new_password": "",
            "role": "super_admin"  # Malicious injection
        },
        follow_redirects=False
    )
    db.refresh(admin_user)
    assert admin_user.role == "admin"


# --- Suspend/Reactivate/Delete Tests ---

def test_suspend_reactivate_admin(super_admin_client, admin_user, db):
    # Suspend
    response = super_admin_client.post(f"/admin/admin-accounts/{admin_user.id}/suspend", follow_redirects=False)
    assert response.status_code == 303
    db.refresh(admin_user)
    assert admin_user.is_active is False
    
    # Reactivate
    response = super_admin_client.post(f"/admin/admin-accounts/{admin_user.id}/reactivate", follow_redirects=False)
    assert response.status_code == 303
    db.refresh(admin_user)
    assert admin_user.is_active is True

def test_delete_admin(super_admin_client, admin_user, db):
    admin_id = admin_user.id
    response = super_admin_client.post(f"/admin/admin-accounts/{admin_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    
    user = db.query(User).filter(User.id == admin_id).first()
    assert user is None


# --- Protection Tests ---

def test_cannot_modify_super_admin(super_admin_client, super_admin_user):
    """Even a super admin cannot suspend/delete another super admin via this interface."""
    target_id = super_admin_user.id
    
    # Try suspend
    response = super_admin_client.post(f"/admin/admin-accounts/{target_id}/suspend", follow_redirects=False)
    assert "error=cannot_modify_super_admin" in response.headers["location"]
    
    # Try edit
    response = super_admin_client.post(
        f"/admin/admin-accounts/{target_id}/edit",
        data={"username": "hacked", "display_name": "Hacked"},
        follow_redirects=False
    )
    assert response.status_code == 404  # Edit query explicitly filters by role='admin'
    
    # Try delete
    response = super_admin_client.post(f"/admin/admin-accounts/{target_id}/delete", follow_redirects=False)
    assert "error=cannot_modify_super_admin" in response.headers["location"]

def test_role_change_revokes_access_immediately(super_admin_client, super_admin_user, db):
    """If a super admin's role is changed in the DB, their active session immediately loses access."""
    # Change the role to admin in DB while they are still holding a super_admin JWT
    super_admin_user.role = "admin"
    db.commit()
    
    # Try to access a super admin only endpoint
    response = super_admin_client.get("/admin/admin-accounts")
    assert response.status_code == 403
