"""Tests for Admin Account Management, Last SA Protection, Bootstrap, and Migration."""

import json
import logging
import pytest
from fastapi import HTTPException
from app.models import User, AuditLog, Student
from app.auth import hash_password, create_access_token
from app.config import settings
from app.create_admin import create_admin
from app.main import ensure_super_admin_exists
from app.routers.admin import ensure_not_last_super_admin


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authentication and Authorization (A1 – A10)
# ─────────────────────────────────────────────────────────────────────────────

def test_a1_super_admin_can_access_admin_dashboard(super_admin_client):
    """A1: Super Admin can log in and access admin dashboard."""
    response = super_admin_client.get("/admin/dashboard")
    assert response.status_code == 200
    assert "แดชบอร์ด" in response.text or "Dashboard" in response.text


def test_a2_regular_admin_can_access_admin_dashboard(admin_client):
    """A2: Regular Admin can log in and access admin dashboard."""
    response = admin_client.get("/admin/dashboard")
    assert response.status_code == 200


def test_a3_regular_admin_gets_403_on_admin_accounts_list(admin_client):
    """A3: Regular Admin gets 403 on /admin/admin-accounts."""
    response = admin_client.get("/admin/admin-accounts", follow_redirects=False)
    assert response.status_code == 403


def test_a4_regular_admin_gets_403_on_admin_accounts_post_endpoints(admin_client, db):
    """A4: Regular Admin gets 403 on admin-accounts POST endpoints."""
    # Test add
    res = admin_client.post(
        "/admin/admin-accounts/add",
        data={"username": "new_admin", "display_name": "New Admin", "password": "password123"},
        follow_redirects=False,
    )
    assert res.status_code == 403

    # Create dummy admin to test edit, suspend, reactivate, delete
    target = User(username="subadmin", password_hash=hash_password("pw1234"),
                  display_name="Sub", role="admin", is_active=True)
    db.add(target)
    db.commit()
    db.refresh(target)

    assert admin_client.post(f"/admin/admin-accounts/{target.id}/edit",
                             data={"username": "subadmin", "display_name": "New"},
                             follow_redirects=False).status_code == 403
    assert admin_client.post(f"/admin/admin-accounts/{target.id}/suspend",
                             follow_redirects=False).status_code == 403
    assert admin_client.post(f"/admin/admin-accounts/{target.id}/reactivate",
                             follow_redirects=False).status_code == 403
    assert admin_client.post(f"/admin/admin-accounts/{target.id}/delete",
                             follow_redirects=False).status_code == 403


def test_a5_teacher_gets_403_on_admin_accounts(teacher_client):
    """A5: Teacher gets 403 on /admin/admin-accounts."""
    response = teacher_client.get("/admin/admin-accounts", follow_redirects=False)
    assert response.status_code == 403


def test_a6_unauthenticated_user_redirected_from_admin_accounts(client):
    """A6: Unauthenticated user redirected from /admin/admin-accounts."""
    response = client.get("/admin/admin-accounts", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_a7_suspended_user_cannot_access_protected_routes(client, db):
    """A7: Suspended user with valid JWT cannot access protected routes (redirects to /login)."""
    user = User(username="suspended_user", password_hash=hash_password("pass123"),
                display_name="Suspended", role="super_admin", is_active=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "role": user.role})
    client.cookies.set("access_token", token)

    response = client.get("/admin/admin-accounts", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_a8_super_admin_can_access_admin_accounts(super_admin_client):
    """A8: Super Admin can access /admin/admin-accounts."""
    response = super_admin_client.get("/admin/admin-accounts")
    assert response.status_code == 200
    assert "จัดการบัญชี Admin" in response.text


def test_a9_super_admin_can_access_teacher_dashboard(super_admin_client):
    """A9: Super Admin can access /teacher/dashboard."""
    response = super_admin_client.get("/teacher/dashboard")
    assert response.status_code == 200


def test_a10_teacher_cannot_access_admin_dashboard(teacher_client):
    """A10: Teacher cannot access /admin/dashboard."""
    response = teacher_client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 2. CRUD Operations (D1 – D8)
# ─────────────────────────────────────────────────────────────────────────────

def test_d1_super_admin_lists_only_admin_role_accounts(super_admin_client, db, super_admin_user, regular_admin_user):
    """D1: Super Admin can list admin accounts (only role='admin' shown, super_admin excluded)."""
    response = super_admin_client.get("/admin/admin-accounts")
    assert response.status_code == 200
    assert regular_admin_user.username in response.text
    # Super admin's own username should NOT appear in the accounts table
    # Check specifically within the table rows
    assert f">{regular_admin_user.username}<" in response.text
    assert f">{super_admin_user.username}<" not in response.text


def test_d2_super_admin_creates_new_admin_account(super_admin_client, db):
    """D2: Super Admin can create new admin account."""
    response = super_admin_client.post(
        "/admin/admin-accounts/add",
        data={"username": "newadmin01", "display_name": "New Admin 01", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/admin/admin-accounts?success=created" in response.headers["location"]

    created = db.query(User).filter(User.username == "newadmin01").first()
    assert created is not None
    assert created.display_name == "New Admin 01"
    assert created.role == "admin"
    assert created.is_active is True

    # Audit log check
    audit = db.query(AuditLog).filter(AuditLog.target_id == "newadmin01").first()
    assert audit is not None
    assert audit.action == "admin_account_created"


def test_d3_duplicate_username_rejected(super_admin_client, regular_admin_user):
    """D3: Duplicate username rejected with clear error."""
    response = super_admin_client.post(
        "/admin/admin-accounts/add",
        data={"username": regular_admin_user.username, "display_name": "Duplicate", "password": "password123"},
        follow_redirects=False,
    )
    # Re-renders page with error message
    assert response.status_code == 200
    assert "มีอยู่แล้ว" in response.text or "already exists" in response.text


def test_d4_newly_created_admin_can_log_in(super_admin_client, client, db):
    """D4: Newly created admin can log in and gets redirected to dashboard."""
    super_admin_client.post(
        "/admin/admin-accounts/add",
        data={"username": "login_admin", "display_name": "Login Admin", "password": "secretpassword"},
        follow_redirects=False,
    )

    login_res = client.post(
        "/login",
        data={"username": "login_admin", "password": "secretpassword"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303
    assert "/admin/dashboard" in login_res.headers["location"]


def test_d5_edit_preserves_password_when_empty(super_admin_client, db, regular_admin_user):
    """D5: Edit username/display_name preserves password when new_password is empty."""
    old_hash = regular_admin_user.password_hash
    response = super_admin_client.post(
        f"/admin/admin-accounts/{regular_admin_user.id}/edit",
        data={"username": "admin2_updated", "display_name": "Updated Name", "new_password": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db.refresh(regular_admin_user)
    assert regular_admin_user.username == "admin2_updated"
    assert regular_admin_user.display_name == "Updated Name"
    assert regular_admin_user.password_hash == old_hash


def test_d6_edit_updates_password_when_supplied(super_admin_client, db, regular_admin_user, client):
    """D6: Supplying new_password updates the hash and enables login with new password."""
    old_hash = regular_admin_user.password_hash
    response = super_admin_client.post(
        f"/admin/admin-accounts/{regular_admin_user.id}/edit",
        data={"username": regular_admin_user.username, "display_name": regular_admin_user.display_name, "new_password": "brandnewpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db.refresh(regular_admin_user)
    assert regular_admin_user.password_hash != old_hash

    # Old password fails
    fail_res = client.post("/login", data={"username": regular_admin_user.username, "password": "admin456"})
    assert "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" in fail_res.text or "Invalid username or password" in fail_res.text

    # New password succeeds
    ok_res = client.post("/login", data={"username": regular_admin_user.username, "password": "brandnewpassword"}, follow_redirects=False)
    assert ok_res.status_code == 303


def test_d7_edit_does_not_modify_role_or_is_active(super_admin_client, db, regular_admin_user):
    """D7: Edit does not change role or is_active (mass-assignment protection)."""
    response = super_admin_client.post(
        f"/admin/admin-accounts/{regular_admin_user.id}/edit",
        data={"username": regular_admin_user.username, "display_name": "New Name", "role": "super_admin", "is_active": "false"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    db.refresh(regular_admin_user)
    assert regular_admin_user.role == "admin"
    assert regular_admin_user.is_active is True


def test_d8_role_cannot_be_set_via_create(super_admin_client, db):
    """D8: Role cannot be set via client request (hardcoded to admin)."""
    super_admin_client.post(
        "/admin/admin-accounts/add",
        data={"username": "sneaky_admin", "display_name": "Sneaky", "password": "password123", "role": "super_admin"},
        follow_redirects=False,
    )
    user = db.query(User).filter(User.username == "sneaky_admin").first()
    assert user is not None
    assert user.role == "admin"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Suspend / Reactivate / Delete (S1 – S8)
# ─────────────────────────────────────────────────────────────────────────────

def test_s1_super_admin_suspends_admin(super_admin_client, db, regular_admin_user):
    """S1: Super Admin can suspend an admin account."""
    response = super_admin_client.post(
        f"/admin/admin-accounts/{regular_admin_user.id}/suspend",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/admin/admin-accounts?success=suspended" in response.headers["location"]

    db.refresh(regular_admin_user)
    assert regular_admin_user.is_active is False

    audit = db.query(AuditLog).filter(
        AuditLog.action == "admin_account_suspended",
        AuditLog.target_id == regular_admin_user.username,
    ).first()
    assert audit is not None


def test_s2_suspended_admin_cannot_login(super_admin_client, client, db, regular_admin_user):
    """S2: Suspended admin cannot log in."""
    super_admin_client.post(f"/admin/admin-accounts/{regular_admin_user.id}/suspend")
    db.refresh(regular_admin_user)

    response = client.post(
        "/login",
        data={"username": regular_admin_user.username, "password": "admin456"},
    )
    assert "ปิดใช้งาน" in response.text or "disabled" in response.text.lower() or "contact admin" in response.text.lower()


def test_s3_super_admin_reactivates_admin(super_admin_client, db, regular_admin_user):
    """S3: Super Admin can reactivate a suspended admin."""
    regular_admin_user.is_active = False
    db.commit()

    response = super_admin_client.post(
        f"/admin/admin-accounts/{regular_admin_user.id}/reactivate",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/admin/admin-accounts?success=reactivated" in response.headers["location"]

    db.refresh(regular_admin_user)
    assert regular_admin_user.is_active is True


def test_s4_reactivated_admin_can_login_again(super_admin_client, client, db, regular_admin_user):
    """S4: Reactivated admin can log in again."""
    regular_admin_user.is_active = False
    db.commit()

    super_admin_client.post(f"/admin/admin-accounts/{regular_admin_user.id}/reactivate")

    response = client.post(
        "/login",
        data={"username": regular_admin_user.username, "password": "admin456"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/admin/dashboard" in response.headers["location"]


def test_s5_super_admin_deletes_admin(super_admin_client, db, regular_admin_user):
    """S5: Super Admin can permanently delete an admin."""
    admin_id = regular_admin_user.id
    response = super_admin_client.post(
        f"/admin/admin-accounts/{admin_id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/admin/admin-accounts?success=deleted" in response.headers["location"]

    deleted = db.query(User).filter(User.id == admin_id).first()
    assert deleted is None


def test_s6_deleted_admin_cannot_login(super_admin_client, client, db, regular_admin_user):
    """S6: Deleted admin cannot log in."""
    super_admin_client.post(f"/admin/admin-accounts/{regular_admin_user.id}/delete")

    response = client.post(
        "/login",
        data={"username": regular_admin_user.username, "password": "admin456"},
    )
    assert "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" in response.text or "Invalid username or password" in response.text


def test_s7_audit_logs_preserved_after_admin_deletion(super_admin_client, db, regular_admin_user, super_admin_user):
    """S7: Audit logs are preserved after admin account deletion (SET NULL on foreign key)."""
    # Create audit log by regular admin
    audit = AuditLog(
        user_id=regular_admin_user.id,
        action="teacher_created",
        target_type="teacher",
        target_id="test_t",
    )
    db.add(audit)
    db.commit()
    audit_id = audit.id

    # Delete regular admin
    super_admin_client.post(f"/admin/admin-accounts/{regular_admin_user.id}/delete")

    # Expire session cache to read fresh state from database
    db.expire_all()
    persisted_audit = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    assert persisted_audit is not None
    assert persisted_audit.user_id is None


def test_s8_cannot_suspend_or_delete_super_admin_via_api(super_admin_client, super_admin_user):
    """S8: Cannot suspend/delete/edit Super Admin via management endpoints (returns 403 or 404)."""
    # Edit checks role=='admin', returns 404 for super_admin
    res_edit = super_admin_client.post(
        f"/admin/admin-accounts/{super_admin_user.id}/edit",
        data={"username": "hacked_sa", "display_name": "Hacked"},
    )
    assert res_edit.status_code == 404

    # Suspend rejects accounts with role != 'admin'
    res_suspend = super_admin_client.post(f"/admin/admin-accounts/{super_admin_user.id}/suspend")
    assert res_suspend.status_code in (403, 409)

    # Delete rejects accounts with role != 'admin'
    res_delete = super_admin_client.post(f"/admin/admin-accounts/{super_admin_user.id}/delete")
    assert res_delete.status_code in (403, 409)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Last Super Admin Protection (L1 – L6)
# ─────────────────────────────────────────────────────────────────────────────

def test_l1_cannot_suspend_only_active_super_admin(db, super_admin_user):
    """L1: Cannot suspend the only active Super Admin (409 Conflict)."""
    with pytest.raises(HTTPException) as excinfo:
        ensure_not_last_super_admin(db, super_admin_user)
    assert excinfo.value.status_code == 409
    assert "Super Admin คนสุดท้าย" in excinfo.value.detail


def test_l2_cannot_delete_only_active_super_admin(db, super_admin_user):
    """L2: Cannot delete the only active Super Admin (409 Conflict)."""
    with pytest.raises(HTTPException) as excinfo:
        ensure_not_last_super_admin(db, super_admin_user)
    assert excinfo.value.status_code == 409


def test_l3_can_suspend_one_of_two_super_admins(db, super_admin_user):
    """L3: Can suspend one of two Super Admins without error."""
    sa2 = User(username="sa2", password_hash=hash_password("pw"), display_name="SA 2",
               role="super_admin", is_active=True)
    db.add(sa2)
    db.commit()

    # ensure_not_last_super_admin should pass without raising
    ensure_not_last_super_admin(db, super_admin_user)


def test_l4_after_suspending_one_sa_cannot_suspend_remaining(db, super_admin_user):
    """L4: After suspending one SA, cannot suspend the remaining active SA."""
    sa2 = User(username="sa2", password_hash=hash_password("pw"), display_name="SA 2",
               role="super_admin", is_active=True)
    db.add(sa2)
    db.commit()

    # Suspend sa2
    sa2.is_active = False
    db.commit()

    # Now super_admin_user is the ONLY active SA
    with pytest.raises(HTTPException) as excinfo:
        ensure_not_last_super_admin(db, super_admin_user)
    assert excinfo.value.status_code == 409


def test_l5_protection_applies_regardless_of_frontend(db, super_admin_user):
    """L5: Protection is enforced at service/backend level."""
    # Even if called directly, it must reject
    with pytest.raises(HTTPException) as excinfo:
        ensure_not_last_super_admin(db, super_admin_user)
    assert excinfo.value.status_code == 409


def test_l6_sqlite_fallback_works_for_serial_protection(db, super_admin_user):
    """L6: SQLite fallback path works properly for serial protection."""
    # Under SQLite (our test DB), ensure_not_last_super_admin operates cleanly
    assert "sqlite" in str(db.bind.url)
    with pytest.raises(HTTPException) as excinfo:
        ensure_not_last_super_admin(db, super_admin_user)
    assert excinfo.value.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# 5. Bootstrap and Migration (M1 – M12)
# ─────────────────────────────────────────────────────────────────────────────

def test_m1_create_admin_creates_super_admin_role(db, monkeypatch):
    """M1: create_admin.py creates initial user with role='super_admin'."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "brand_new_admin")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "strong_password")

    create_admin(db=db)

    user = db.query(User).filter(User.username == "brand_new_admin").first()
    assert user is not None
    assert user.role == "super_admin"
    assert user.is_active is True


def test_m2_create_admin_does_not_modify_existing_user(db, monkeypatch):
    """M2: create_admin.py does not modify an existing user."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "existing_admin")
    user = User(username="existing_admin", password_hash=hash_password("original_pw"),
                display_name="Original", role="admin", is_active=True)
    db.add(user)
    db.commit()

    create_admin(db=db)

    db.refresh(user)
    assert user.role == "admin"  # Not changed by create_admin


def test_m3_migration_promotes_bootstrap_account_from_admin_to_super_admin(db, monkeypatch):
    """M3: Migration promotes bootstrap account from 'admin' to 'super_admin'."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "bootstrap_admin")
    user = User(username="bootstrap_admin", password_hash=hash_password("pw"),
                display_name="Bootstrap", role="admin", is_active=True)
    db.add(user)
    db.commit()

    ensure_super_admin_exists(db=db)

    db.refresh(user)
    assert user.role == "super_admin"

    audit = db.query(AuditLog).filter(
        AuditLog.action == "super_admin_migration",
        AuditLog.target_id == "bootstrap_admin",
    ).first()
    assert audit is not None
    assert audit.previous_value == "admin"
    assert audit.new_value == "super_admin"


def test_m4_migration_is_noop_when_super_admin_already_exists(db, monkeypatch, super_admin_user):
    """M4: Migration is a no-op when a super_admin already exists."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "another_admin")
    other = User(username="another_admin", password_hash=hash_password("pw"),
                 display_name="Other", role="admin", is_active=True)
    db.add(other)
    db.commit()

    ensure_super_admin_exists(db=db)

    db.refresh(other)
    assert other.role == "admin"  # Unchanged


def test_m5_migration_does_not_promote_if_bootstrap_account_missing(db, monkeypatch):
    """M5: Migration does not promote anything if the bootstrap account does not exist."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "ghost_account")
    regular = User(username="regular1", password_hash=hash_password("pw"),
                   display_name="Regular", role="admin", is_active=True)
    db.add(regular)
    db.commit()

    ensure_super_admin_exists(db=db)

    db.refresh(regular)
    assert regular.role == "admin"


def test_m6_migration_does_not_promote_if_bootstrap_is_suspended(db, monkeypatch):
    """M6: Migration does not promote if the bootstrap account is suspended."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "suspended_boot")
    boot = User(username="suspended_boot", password_hash=hash_password("pw"),
                display_name="Suspended", role="admin", is_active=False)
    db.add(boot)
    db.commit()

    ensure_super_admin_exists(db=db)

    db.refresh(boot)
    assert boot.role == "admin"


def test_m7_migration_does_not_promote_if_bootstrap_is_teacher(db, monkeypatch):
    """M7: Migration does not promote if the bootstrap account has role='teacher'."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "teacher_boot")
    boot = User(username="teacher_boot", password_hash=hash_password("pw"),
                display_name="Teacher", role="teacher", is_active=True)
    db.add(boot)
    db.commit()

    ensure_super_admin_exists(db=db)

    db.refresh(boot)
    assert boot.role == "teacher"


def test_m8_migration_only_promotes_bootstrap_account_not_others(db, monkeypatch):
    """M8: Migration only promotes the bootstrap account; other admin accounts remain 'admin'."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "primary_admin")
    primary = User(username="primary_admin", password_hash=hash_password("pw"),
                   display_name="Primary", role="admin", is_active=True)
    secondary = User(username="secondary_admin", password_hash=hash_password("pw"),
                     display_name="Secondary", role="admin", is_active=True)
    db.add_all([primary, secondary])
    db.commit()

    ensure_super_admin_exists(db=db)

    db.refresh(primary)
    db.refresh(secondary)
    assert primary.role == "super_admin"
    assert secondary.role == "admin"


def test_m9_migration_is_idempotent(db, monkeypatch):
    """M9: Running migration twice has the exact same result."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "idempotent_admin")
    boot = User(username="idempotent_admin", password_hash=hash_password("pw"),
                display_name="Idempotent", role="admin", is_active=True)
    db.add(boot)
    db.commit()

    ensure_super_admin_exists(db=db)
    ensure_super_admin_exists(db=db)

    db.refresh(boot)
    assert boot.role == "super_admin"
    # Only 1 audit log entry
    count = db.query(AuditLog).filter(
        AuditLog.action == "super_admin_migration",
        AuditLog.target_id == "idempotent_admin",
    ).count()
    assert count == 1


def test_m10_migration_does_not_log_passwords_or_hashes(db, monkeypatch, caplog):
    """M10: Migration does not log passwords, password hashes, or secrets."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "safe_admin")
    secret_pass = "very_secret_password_12345"
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", secret_pass)

    boot = User(username="safe_admin", password_hash=hash_password(secret_pass),
                display_name="Safe", role="admin", is_active=True)
    db.add(boot)
    db.commit()

    with caplog.at_level(logging.DEBUG):
        ensure_super_admin_exists(db=db)

    log_text = caplog.text
    assert secret_pass not in log_text
    assert boot.password_hash not in log_text
    assert settings.SECRET_KEY not in log_text

    # Audit log check
    audit = db.query(AuditLog).filter(AuditLog.target_id == "safe_admin").first()
    assert secret_pass not in (audit.previous_value or "")
    assert secret_pass not in (audit.new_value or "")


def test_m11_promoted_user_can_login_and_access_admin_dashboard(db, client, monkeypatch):
    """M11: Promoted user can log in and access admin dashboard."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "promoted_login")
    user = User(username="promoted_login", password_hash=hash_password("promote123"),
                display_name="Promoted", role="admin", is_active=True)
    db.add(user)
    db.commit()

    ensure_super_admin_exists(db=db)

    res = client.post("/login", data={"username": "promoted_login", "password": "promote123"}, follow_redirects=False)
    assert res.status_code == 303
    assert "/admin/dashboard" in res.headers["location"]


def test_m12_other_admin_accounts_retain_admin_role_after_migration(db, monkeypatch):
    """M12: Other admin accounts retain 'admin' role after migration."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "boot_user")
    boot = User(username="boot_user", display_name="Boot Admin", password_hash=hash_password("pw"), role="admin", is_active=True)
    admin_a = User(username="admin_a", display_name="Admin A", password_hash=hash_password("pw"), role="admin", is_active=True)
    admin_b = User(username="admin_b", display_name="Admin B", password_hash=hash_password("pw"), role="admin", is_active=True)
    db.add_all([boot, admin_a, admin_b])
    db.commit()

    ensure_super_admin_exists(db=db)

    db.refresh(admin_a)
    db.refresh(admin_b)
    assert admin_a.role == "admin"
    assert admin_b.role == "admin"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Regression (R1 – R5)
# ─────────────────────────────────────────────────────────────────────────────

def test_r1_dashboard_access_works_for_both_roles(admin_client, super_admin_client):
    """R1: Admin dashboard access works for both 'admin' and 'super_admin'."""
    assert admin_client.get("/admin/dashboard").status_code == 200
    assert super_admin_client.get("/admin/dashboard").status_code == 200


def test_r2_teacher_management_continues_to_work(admin_client, db):
    """R2: Existing teacher management continues to work for admin."""
    res_list = admin_client.get("/admin/teachers")
    assert res_list.status_code == 200


def test_r3_student_management_continues_to_work(admin_client, db):
    """R3: Existing student management continues to work for admin."""
    res_list = admin_client.get("/admin/students")
    assert res_list.status_code == 200


def test_r4_existing_login_logout_flow_unchanged(client, admin_user):
    """R4: Existing login/logout flow is completely preserved."""
    login_res = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
    assert login_res.status_code == 303
    assert "access_token" in login_res.cookies

    client.cookies = login_res.cookies
    logout_res = client.get("/logout", follow_redirects=False)
    assert logout_res.status_code == 303
    assert "/login" in logout_res.headers["location"]


def test_r5_i18n_keys_exist_for_both_th_and_en():
    """R5: All required i18n keys for admin accounts exist in both languages in i18n.js."""
    import re
    import os
    js_path = "static/js/i18n.js" if os.path.exists("static/js/i18n.js") else "backend/static/js/i18n.js"
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_keys = [
        "nav_admin_accounts",
        "role_super_admin",
        "admin_accounts_title",
        "admin_accounts_subtitle",
        "admin_accounts_add",
        "admin_accounts_add_title",
        "admin_accounts_edit_title",
        "admin_accounts_empty",
        "admin_accounts_search_placeholder",
        "admin_accounts_col_username",
        "admin_accounts_col_display_name",
        "admin_accounts_col_status",
        "admin_accounts_col_created",
        "admin_accounts_col_actions",
        "admin_accounts_success_created",
        "admin_accounts_success_edited",
        "admin_accounts_success_suspended",
        "admin_accounts_success_reactivated",
        "admin_accounts_success_deleted",
        "status_suspended",
        "btn_suspend",
        "btn_reactivate",
        "btn_save",
        "label_username",
        "label_display_name",
        "label_password",
        "label_new_password",
    ]

    for key in required_keys:
        matches = re.findall(rf"'{key}':", content)
        assert len(matches) >= 2, f"Key '{key}' should appear in both TH and EN dictionaries, found {len(matches)}"
