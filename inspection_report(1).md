# Revised Implementation Plan — Admin Account Management (v2)

> **Status:** Draft — awaiting review and approval before implementation.
> **Revision date:** 2026-10-11
> **Scope:** Planning and documentation only. No application code, database schema, production data, or account privileges have been modified.

---

## Table of Contents

1. [Issue 1 — Last Active Super Admin Protection](#1-last-active-super-admin-protection)
2. [Issue 2 — CSRF Protection Reassessment](#2-csrf-protection-reassessment)
3. [Issue 3 — Super Admin Access to Teacher Routes](#3-super-admin-access-to-teacher-routes)
4. [Issue 4 — Safe Bootstrap and Migration](#4-safe-bootstrap-and-migration)
5. [Role and Authorization Matrix](#5-role-and-authorization-matrix)
6. [Exact Files, Functions, Routes, and DB Objects to Change](#6-exact-files-functions-routes-and-db-objects-to-change)
7. [Automated Test Plan](#7-automated-test-plan)
8. [Unchanged Application Features](#8-unchanged-application-features)
9. [Unresolved Risks and Assumptions](#9-unresolved-risks-and-assumptions)

---

## 1. Last Active Super Admin Protection

### Problem with the Original Plan

The original plan proposed:

```python
active_count = db.query(func.count(User.id)).filter(
    User.role == "super_admin", User.is_active == True
).with_for_update().scalar()
```

This is **incorrect for PostgreSQL**. `SELECT ... FOR UPDATE` acquires row-level locks on the rows that *satisfy* the query. However, aggregate functions like `COUNT(*)` return a single computed row — not a reference to any table row. PostgreSQL will:
- Either lock the individual rows scanned (non-deterministic depending on query plan), or
- Raise an error / produce unexpected locking behavior.

In neither case does it provide the serializable protection needed to prevent two concurrent requests from both reading `count=2`, each proceeding to suspend one Super Admin, and leaving zero active Super Admins.

### Selected Strategy: Advisory Lock + Row-Level Verification

**Mechanism:** PostgreSQL [session-level advisory locks](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS) provide an application-level mutex that is:
- Fully supported by Supabase PostgreSQL.
- Independent of table structure — no schema changes needed.
- Released automatically on session/transaction close.
- Ignored by SQLite (fallback strategy for dev/test).

**Lock ID:** A fixed, application-defined `bigint` constant: `7777777001` (chosen to avoid collision with other advisory lock users; documented in code).

#### Transaction Flow (PostgreSQL)

For every **suspend**, **delete**, or **demote** operation targeting a `super_admin` account:

```
BEGIN TRANSACTION

1. Acquire advisory lock:
   SELECT pg_advisory_xact_lock(7777777001);
   -- Blocks until the lock is available. Released on COMMIT/ROLLBACK.

2. Count active super admins:
   SELECT COUNT(*) FROM users
   WHERE role = 'super_admin' AND is_active = true;

3. IF count <= 1 AND target is one of those active super admins:
     ROLLBACK
     Return error 409 Conflict with localized message.

4. ELSE:
     Perform the operation (suspend / delete / demote).
     Log audit entry.
     COMMIT
```

**Why this works:** `pg_advisory_xact_lock` is a blocking exclusive lock. If two requests arrive concurrently:
- Request A acquires the lock, reads count=2, proceeds to suspend Super Admin X. Commits → releases lock.
- Request B was blocked at step 1. After A commits, B acquires the lock, reads count=1 (X is now suspended), and **rejects** the operation.

There is no TOCTOU race because the count is read *inside* the critical section.

#### SQLite Fallback (dev/test)

SQLite does not support advisory locks. For the development and test environments:

- Use the **same code path** but skip the `pg_advisory_xact_lock` call.
- SQLite operates in WAL mode with serialized writes — single-writer semantics provide adequate protection for development.
- The function will detect the database backend at runtime:

```python
def _acquire_super_admin_lock(db: Session) -> None:
    """Acquire an exclusive advisory lock for super admin operations.
    No-op on SQLite (single-writer provides sufficient protection)."""
    bind_url = str(db.bind.url) if db.bind else ""
    if "postgresql" in bind_url:
        db.execute(text("SELECT pg_advisory_xact_lock(7777777001)"))
```

#### Implementation in `app/routers/admin.py`

A reusable helper function:

```python
def ensure_not_last_super_admin(db: Session, target_user: User, operation: str) -> None:
    """Prevent operations that would remove the last active Super Admin.

    Must be called within a transaction. Raises HTTPException 409 on violation.
    """
    _acquire_super_admin_lock(db)

    active_count = db.query(func.count(User.id)).filter(
        User.role == "super_admin",
        User.is_active == True
    ).scalar()

    is_target_active_super = (
        target_user.role == "super_admin" and target_user.is_active
    )

    if active_count <= 1 and is_target_active_super:
        raise HTTPException(
            status_code=409,
            detail="ไม่สามารถดำเนินการได้ เนื่องจากเป็น Super Admin คนสุดท้ายในระบบ / "
                   "Cannot perform this operation on the last active Super Admin."
        )
```

This function is called **before** every suspend, delete, and demote operation, regardless of whether the frontend hides Super Admin accounts from the management list.

#### Failure Handling

| Scenario | Behavior |
|---|---|
| Lock acquisition timeout | `pg_advisory_xact_lock` blocks indefinitely by default. If `statement_timeout` is configured on Supabase, the query will fail with a `QueryCanceledError` → transaction rolls back, client receives 500. |
| Transaction interrupted mid-operation | Advisory lock is released on ROLLBACK. No state corruption. |
| Concurrent requests | Serialized by the advisory lock. Second request sees the updated state. |
| Application crash while holding lock | PostgreSQL releases session-level locks when the session disconnects. `pg_advisory_xact_lock` (transaction-scoped) is released on implicit ROLLBACK. |

#### Error Messages

| Language | Message |
|---|---|
| TH | `ไม่สามารถดำเนินการได้ เนื่องจากเป็น Super Admin คนสุดท้ายในระบบ` |
| EN | `Cannot perform this operation on the last active Super Admin.` |

#### Test Cases (PostgreSQL-specific)

| # | Test | How |
|---|---|---|
| P1 | Serial: suspend the only Super Admin → rejected | Single request against 1-super-admin DB |
| P2 | Serial: suspend one of two Super Admins → allowed | Single request against 2-super-admin DB |
| P3 | Serial: delete the only Super Admin → rejected | Single request |
| P4 | Concurrent: two threads each try to suspend one of two Super Admins simultaneously → one succeeds, one is rejected | Two threads with shared PostgreSQL test DB, synchronized start |
| P5 | Advisory lock released after ROLLBACK | Verify second request proceeds after first rolls back |
| P6 | SQLite fallback path works for serial operations | Standard test DB (in-memory SQLite) |

> [!IMPORTANT]
> Tests P1–P5 require a PostgreSQL test database. They will be marked with `@pytest.mark.postgres` and skipped when the test database URL starts with `sqlite`. The CI/CD pipeline should run these tests against a PostgreSQL instance.

---

## 2. CSRF Protection Reassessment

### Current State Analysis

**Cookie configuration** (from [`routers/auth.py:52-58`](file:///k:/Project_CheckID_Student/backend/app/routers/auth.py#L52-L58)):

```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    samesite="lax",
    max_age=60 * 480,  # 8 hours
)
```

| Property | Value | CSRF Implication |
|---|---|---|
| `httponly` | `True` | ✅ Cookie not accessible to JavaScript |
| `samesite` | `"lax"` | ⚠️ Blocks cross-site POST from external origins in modern browsers. **Does NOT protect** GET endpoints that cause state changes. |
| `secure` | **Not set** | ❌ Cookie is sent over HTTP in development. In production (Supabase/HTTPS), cookie will be sent over HTTPS but browser may also send it over HTTP without `Secure` flag. |
| `domain` | **Not set** | ✅ Defaults to the exact host (no subdomain sharing) |

### State-Changing GET Endpoints — Vulnerability Assessment

Scanning all routes in the application:

| Router | Method | Route | State change? | Risk |
|---|---|---|---|---|
| `admin.py` | `GET` | `/admin/students/template` | No (file download) | None |
| `admin.py` | `GET` | `/admin/reports/export` | No (file download) | None |
| `admin.py` | `GET` | `/admin/reports/pdf` | No (file download) | None |
| `auth.py` | `GET` | `/logout` | **Yes** — deletes auth cookie | **Low** — logout CSRF is nuisance, not privilege escalation |
| `teacher.py` | `GET` | `/teacher/api/qr/{session_id}` | **Yes** — creates QRToken in DB | **Medium** — generates valid QR tokens if teacher is logged in |
| All `POST` routes | `POST` | Various | Yes | Protected by `SameSite=Lax` against cross-site form submits |

**Key finding:** `/teacher/api/qr/{session_id}` is a GET endpoint that creates database records (QR tokens). `SameSite=Lax` does **not** protect GET requests — a cross-site `<img>` tag or `<script>` tag could trigger this endpoint. However, the tokens expire in 30 seconds and the endpoint requires a valid auth cookie, making exploitation impractical in most scenarios.

### Assessment Conclusion

| Defense | Coverage |
|---|---|
| `SameSite=Lax` | ✅ Protects all POST endpoints against cross-site form submissions |
| `httponly` | ✅ Prevents XSS-based cookie theft |
| `Secure` flag | ❌ Missing — should be added for production (HTTPS) |
| CSRF tokens | ❌ Not present anywhere in the application |
| Origin/Referer validation | ❌ Not present |

### Proposed Mitigation (Scoped to This Feature)

**Decision: Add lightweight Origin/Referer validation middleware for all state-changing requests, plus add `Secure` flag in production.**

Rationale:
- Adding CSRF tokens to only the new admin-account endpoints would be inconsistent with the 20+ existing POST endpoints. The entire app would need CSRF tokens to be meaningful.
- Origin/Referer validation is stateless (no tokens to manage), consistent across the entire app, and can be applied as a single middleware without modifying any existing forms.
- This provides defense-in-depth on top of `SameSite=Lax`.

#### Implementation: `app/middleware/csrf.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from urllib.parse import urlparse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

async def csrf_origin_check(request: Request, call_next):
    """Validate Origin/Referer header for state-changing requests.
    
    Rejects POST/PUT/DELETE/PATCH requests where the Origin (or Referer)
    does not match the application's host. This is defense-in-depth
    on top of SameSite=Lax cookies.
    """
    if request.method in SAFE_METHODS:
        return await call_next(request)

    # Allow requests with no Origin AND no Referer (same-origin form submits
    # from some browsers may omit both headers)
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    if origin:
        origin_host = urlparse(origin).netloc
        request_host = request.headers.get("host", "")
        if origin_host != request_host:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected"}
            )
    elif referer:
        referer_host = urlparse(referer).netloc
        request_host = request.headers.get("host", "")
        if referer_host != request_host:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected"}
            )
    # If neither Origin nor Referer is present, allow the request.
    # This handles same-origin requests from clients that strip these headers.

    return await call_next(request)
```

Register in `app/main.py`:
```python
from app.middleware.csrf import csrf_origin_check
app.middleware("http")(csrf_origin_check)
```

#### Cookie `Secure` Flag

Add the `Secure` flag when not in development:

```python
is_dev = settings.DATABASE_URL.startswith("sqlite")
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    samesite="lax",
    secure=not is_dev,  # Secure=True in production (HTTPS)
    max_age=60 * 480,
)
```

#### Ensure No State-Changing GET Endpoints in New Routes

**All new admin-account-management routes will use POST exclusively for state changes:**
- `POST /admin/admin-accounts/add` — create account
- `POST /admin/admin-accounts/{id}/edit` — edit account
- `POST /admin/admin-accounts/{id}/suspend` — suspend account
- `POST /admin/admin-accounts/{id}/reactivate` — reactivate account
- `POST /admin/admin-accounts/{id}/delete` — permanently delete account

**`GET` is used only for:**
- `GET /admin/admin-accounts` — list page (read-only)

#### Existing Risks (Outside This Feature's Scope)

> [!WARNING]
> **`GET /teacher/api/qr/{session_id}`** creates QR tokens via GET. This should be converted to POST in a future security hardening pass. It is not addressed in this feature because:
> 1. It exists in the Teacher router, not Admin Account Management.
> 2. Changing it requires updating the frontend JavaScript (QR auto-refresh loop).
> 3. The 30-second token expiry limits exploit impact.
>
> **`GET /logout`** deletes the auth cookie via GET. This is a minor nuisance vulnerability (logout CSRF). It should be changed to POST with a logout button/form in a future pass.
>
> **Recommendation:** File a separate security ticket to address these two GET-based state changes app-wide.

#### CSRF Test Cases

| # | Test | Category |
|---|---|---|
| C1 | POST with matching Origin header → accepted | Middleware |
| C2 | POST with mismatched Origin header → rejected 403 | Middleware |
| C3 | POST with matching Referer (no Origin) → accepted | Middleware |
| C4 | POST with mismatched Referer (no Origin) → rejected 403 | Middleware |
| C5 | POST with neither Origin nor Referer → accepted | Middleware |
| C6 | GET request with mismatched Origin → allowed (safe method) | Middleware |
| C7 | All new admin-account POST endpoints reject cross-origin | Integration |
| C8 | Cookie has `Secure` flag in PostgreSQL (production) mode | Cookie config |

---

## 3. Super Admin Access to Teacher Routes

### Current State

[`auth.py:79-92`](file:///k:/Project_CheckID_Student/backend/app/auth.py#L79-L92) — `require_teacher` currently allows `"teacher"`, `"admin"`, and `"super_admin"`:

```python
if user.role not in ("teacher", "admin", "super_admin"):
```

### Inspection of Teacher Routes

All routes in [`routers/teacher.py`](file:///k:/Project_CheckID_Student/backend/app/routers/teacher.py) use `require_teacher`:

| Route | Method | Function | Purpose |
|---|---|---|---|
| `/teacher/dashboard` | GET | `teacher_dashboard` | Select activity/session |
| `/teacher/api/sessions/{id}` | GET | `get_sessions` | AJAX: session list |
| `/teacher/api/activities_list` | GET | `activities_list` | AJAX: activity list |
| `/teacher/attendance/{session_id}` | GET | `attendance_screen` | QR display + attendance |
| `/teacher/api/qr/{session_id}` | GET | `generate_qr` | Generate QR token |
| `/teacher/api/stats/{session_id}` | GET | `attendance_stats` | Attendance counts |
| `/teacher/attendance-list/{session_id}` | GET | `attendance_list` | Attendance overview |
| `/teacher/ws/attendance/{session_id}` | WS | `websocket_attendance` | Real-time updates |
| `/teacher/api/monitoring/{session_id}` | GET | `monitoring_data` | Student list + stats |
| `/teacher/api/attendance/{session_id}/status` | POST | `update_attendance_status` | Change student status |
| `/teacher/reports` | GET | `teacher_reports` | Report page |
| `/teacher/api/classrooms` | GET | `get_classrooms` | Classroom list |
| `/teacher/api/attendance_pdf` | GET | `attendance_pdf_by_grade_room` | PDF by grade/room |
| `/teacher/api/attendance_pdf_all` | GET | `attendance_pdf_all_students` | PDF all students |
| `/teacher/api/summary_pdf/{session_id}` | GET | `summary_pdf` | Summary PDF |

### Analysis

These are **operational teaching functions**: running attendance sessions, scanning QR codes, generating reports. They are the day-to-day tools a teacher uses in a classroom.

**Question: Does a Super Admin need access to these routes?**

- A `super_admin` is an elevated `admin`. Admins **already** have access to teacher routes (the original `require_teacher` allowed `admin`).
- The admin dashboard at [`routers/admin.py`](file:///k:/Project_CheckID_Student/backend/app/routers/admin.py) provides its own attendance management, reports, and exports that are **more powerful** than the teacher equivalents.
- The teacher dashboard and QR functionality are designed for **classroom use**. There is no business requirement for a Super Admin to access the teacher QR screen or teacher reports — the admin equivalents already cover these needs.

**However**, the existing codebase already grants `admin` role access to teacher routes. This is an existing design choice (admins can observe teacher functionality). Removing `admin` from `require_teacher` would be a breaking change.

### Decision: Preserve Existing Behavior, Do Not Expand

**Keep `require_teacher` unchanged at `("teacher", "admin", "super_admin")`.**

Justification:
1. **`admin` already has teacher access.** Since `super_admin` is a superset of `admin`, excluding `super_admin` from teacher routes would create a paradox: a lower-privileged `admin` has more access than a higher-privileged `super_admin`.
2. **The login flow redirects both `admin` and `super_admin` to `/admin/dashboard`**, not `/teacher/dashboard`. Super Admins will not accidentally land on teacher pages.
3. **No new teacher permissions are being added.** The `require_teacher` check already includes `admin`; adding `super_admin` simply maintains role hierarchy consistency.
4. **Removing `admin` from teacher routes is out of scope** and would break existing behavior.

### What Will NOT Be Done

- ❌ **Will not add new teacher routes** accessible only to Super Admins.
- ❌ **Will not add `super_admin` to teacher routes that currently only allow `teacher`** — but upon inspection, all teacher routes already use `require_teacher` which accepts `admin` too, so this is a non-issue.
- ❌ **Will not modify any teacher route authorization.**

### Authorization Tests

| # | Test | Expected |
|---|---|---|
| T1 | Teacher can access `/teacher/dashboard` | ✅ 200 |
| T2 | Admin can access `/teacher/dashboard` | ✅ 200 (existing behavior) |
| T3 | Super Admin can access `/teacher/dashboard` | ✅ 200 (consistent with admin) |
| T4 | Unauthenticated user accessing `/teacher/dashboard` | Redirect to `/login` |
| T5 | Admin can access `/admin/dashboard` | ✅ 200 |
| T6 | Super Admin can access `/admin/dashboard` | ✅ 200 |
| T7 | Teacher cannot access `/admin/dashboard` | ❌ 403 |
| T8 | Teacher cannot access `/admin/admin-accounts` | ❌ 403 |
| T9 | Admin cannot access `/admin/admin-accounts` | ❌ 403 |
| T10 | Super Admin can access `/admin/admin-accounts` | ✅ 200 |

---

## 4. Safe Bootstrap and Migration

### Current Bootstrap Process

1. **Script:** [`create_admin.py`](file:///k:/Project_CheckID_Student/backend/app/create_admin.py) reads `ADMIN_USERNAME` / `ADMIN_PASSWORD` from env, creates a `User` with `role="admin"`.
2. **Startup:** [`main.py`](file:///k:/Project_CheckID_Student/backend/app/main.py) calls `init_db()` (creates tables). No user creation or migration at startup.
3. **Production config:** `.env` has `ADMIN_USERNAME` configured, `DATABASE_URL=postgresql://...supabase...`.
4. **The bootstrap account may already exist** in the production database as `role="admin"`.

### Revised Procedure

#### Step A: Modify `create_admin.py` — New Installations Only

For **new** installations, `create_admin.py` will create the bootstrap account with `role="super_admin"` instead of `role="admin"`:

```python
admin = User(
    username=settings.ADMIN_USERNAME,
    password_hash=hash_password(settings.ADMIN_PASSWORD),
    display_name="Administrator",
    role="super_admin",  # Changed from "admin"
    is_active=True,
)
```

**If the bootstrap account already exists**, the script prints a message and exits — **no modification**.

#### Step B: Application Startup Migration — `ensure_super_admin_exists()`

A function added to `main.py`'s startup event. This handles the case where the application starts against an **existing** production database that has the bootstrap admin as `role="admin"`.

```python
def ensure_super_admin_exists():
    """One-time idempotent migration: ensure at least one super_admin exists.

    Rules:
    1. If ANY user with role='super_admin' AND is_active=True exists → do nothing.
    2. If no active super_admin exists → look for the bootstrap account
       (matching ADMIN_USERNAME from env) with role='admin'.
       - If found and is_active: promote to 'super_admin'. Log the promotion.
       - If found but is_active=False: skip (suspended account — do not promote).
       - If not found: skip (admin must run create_admin.py manually).
    3. Never promote multiple accounts. Never promote non-bootstrap accounts.
    """
```

#### Behavioral Matrix

| Scenario | Behavior | Result |
|---|---|---|
| No Super Admin exists. Bootstrap account exists as `role="admin"`, `is_active=True`. | Promote the bootstrap account to `super_admin`. Log `super_admin_migration`. | ✅ System has a super_admin. |
| A Super Admin already exists. | Do nothing. Function is a no-op. | ✅ No change. |
| No Super Admin exists. Bootstrap account does not exist at all. | Log a warning: "No super_admin found and bootstrap account does not exist. Run create_admin.py." Skip. | ⚠️ System has no super_admin — manual action required. |
| No Super Admin exists. Bootstrap account exists but `is_active=False`. | Log a warning: "Bootstrap account is suspended. Cannot auto-promote." Skip. | ⚠️ System has no super_admin — manual action required. |
| No Super Admin exists. Bootstrap account exists with `role="teacher"`. | **Do not promote.** Log: "Bootstrap account has unexpected role 'teacher'. Skipping." | ⚠️ No promotion of non-admin accounts. |
| No Super Admin exists. Multiple accounts with `role="admin"` exist. | Promote **only** the one matching `settings.ADMIN_USERNAME`. Others remain `admin`. | ✅ Only the designated bootstrap account is promoted. |
| Migration runs twice (restart). | Second run finds a Super Admin exists → no-op. | ✅ Idempotent. |
| Migration is interrupted (crash mid-transaction). | Transaction rolls back. No partial state. Next startup retries. | ✅ Safe. |
| Deployed against production DB with existing super_admin. | Condition 1 is met → no-op. | ✅ No unintended changes. |

#### Verification Before Promotion

The function verifies **all three conditions** before promoting:
1. `user.username == settings.ADMIN_USERNAME` — matches the configured bootstrap account.
2. `user.role == "admin"` — the account is currently an admin (not teacher, not already super_admin).
3. `user.is_active == True` — the account is active.

If any condition fails, the promotion is skipped with a diagnostic log message.

#### What Is Logged

| Event | Log Output | Audit Log Entry |
|---|---|---|
| Promotion occurs | `INFO: Promoted user '{username}' from admin to super_admin.` | `action="super_admin_migration"`, `target_type="user"`, `target_id=username`, `previous_value="admin"`, `new_value="super_admin"` |
| No-op (SA exists) | `DEBUG: Super Admin already exists. Skipping migration.` | None |
| Bootstrap not found | `WARNING: No super_admin exists. Bootstrap account '{username}' not found. Run create_admin.py.` | None |
| Bootstrap suspended | `WARNING: Bootstrap account '{username}' is suspended. Cannot auto-promote.` | None |
| Bootstrap wrong role | `WARNING: Bootstrap account '{username}' has role '{role}', expected 'admin'. Skipping.` | None |

**Never logged:** passwords, password hashes, JWT secrets, `SECRET_KEY`, database credentials.

#### Rollback / Recovery

- **If the promotion was incorrect:** A Super Admin can demote the account back to `admin` through the admin-accounts management UI, or a database administrator can run:
  ```sql
  UPDATE users SET role = 'admin' WHERE username = '<bootstrap_username>';
  ```
- **If the migration created an unintended Super Admin:** The same SQL or management UI can correct it. The advisory lock ensures the last Super Admin cannot be demoted.

#### Production Deployment Considerations

1. **First deployment** after this change: The startup migration will promote the bootstrap account from `admin` to `super_admin`. Existing admin accounts remain unchanged.
2. **Subsequent deployments:** The migration is a no-op.
3. **If `ADMIN_USERNAME` is changed** in production `.env`: The migration looks for the new username. If no user with that username exists as `admin`, it skips. The existing super_admin is not affected.
4. **No downtime required.** The migration runs in the application startup event within a single transaction.

#### Test Cases

| # | Test | Category |
|---|---|---|
| M1 | `create_admin.py` creates user with `role="super_admin"` | Bootstrap |
| M2 | `create_admin.py` does not modify existing user | Bootstrap |
| M3 | Migration promotes bootstrap account from `admin` to `super_admin` | Migration |
| M4 | Migration is no-op when Super Admin already exists | Migration |
| M5 | Migration does not promote if bootstrap account doesn't exist | Migration |
| M6 | Migration does not promote if bootstrap account is suspended | Migration |
| M7 | Migration does not promote if bootstrap account is `teacher` | Migration |
| M8 | Migration only promotes the bootstrap account, not other admins | Migration |
| M9 | Migration is idempotent — running twice has same result | Migration |
| M10 | Migration does not log passwords, hashes, or secrets | Security |
| M11 | Promoted user can log in and access admin dashboard | Regression |
| M12 | Other admin accounts retain `admin` role after migration | Regression |

---

## 5. Role and Authorization Matrix

### Role Definitions

| Role | Description | Created By |
|---|---|---|
| `super_admin` | Full system administrator. Can manage admin accounts. | `create_admin.py` or migration |
| `admin` | System administrator. Can manage students, teachers, activities, attendance, reports, audit logs. | Super Admin via admin-accounts UI |
| `teacher` | Can run attendance sessions, generate QR codes, view/export reports. | Admin via teacher management |

### Route Authorization Matrix

| Route Group | `super_admin` | `admin` | `teacher` | Unauthenticated |
|---|---|---|---|---|
| `/login`, `/logout` | ✅ | ✅ | ✅ | ✅ (`/login` only) |
| `/admin/dashboard` | ✅ | ✅ | ❌ 403 | Redirect `/login` |
| `/admin/students/**` | ✅ | ✅ | ❌ 403 | Redirect `/login` |
| `/admin/teachers/**` | ✅ | ✅ | ❌ 403 | Redirect `/login` |
| `/admin/activities/**` | ✅ | ✅ | ❌ 403 | Redirect `/login` |
| `/admin/attendance/**` | ✅ | ✅ | ❌ 403 | Redirect `/login` |
| `/admin/reports/**` | ✅ | ✅ | ❌ 403 | Redirect `/login` |
| `/admin/audit-logs` | ✅ | ✅ | ❌ 403 | Redirect `/login` |
| **`/admin/admin-accounts/**`** | **✅** | **❌ 403** | **❌ 403** | **Redirect `/login`** |
| `/teacher/dashboard` | ✅ | ✅ | ✅ | Redirect `/login` |
| `/teacher/attendance/**` | ✅ | ✅ | ✅ | Redirect `/login` |
| `/teacher/api/**` | ✅ | ✅ | ✅ | Redirect `/login` |
| `/teacher/reports` | ✅ | ✅ | ✅ | Redirect `/login` |
| `/checkin`, `/api/checkin/**` | N/A | N/A | N/A | ✅ (public, QR-token gated) |

### Dependency Functions

| Function | Allowed Roles | Used By |
|---|---|---|
| `require_login` | Any authenticated user | — |
| `require_admin` | `admin`, `super_admin` | All `/admin/**` routes (except admin-accounts) |
| `require_super_admin` **(new)** | `super_admin` only | `/admin/admin-accounts/**` |
| `require_teacher` | `teacher`, `admin`, `super_admin` | All `/teacher/**` routes |

---

## 6. Exact Files, Functions, Routes, and DB Objects to Change

### Files Modified

| File | Changes | Step |
|---|---|---|
| [`app/auth.py`](file:///k:/Project_CheckID_Student/backend/app/auth.py) | Add `require_super_admin` function | 1 |
| [`app/routers/auth.py`](file:///k:/Project_CheckID_Student/backend/app/routers/auth.py) | Add `secure` flag to cookie set_cookie call | 2 |
| [`app/templating.py`](file:///k:/Project_CheckID_Student/backend/app/templating.py) | Add `"super_admin": "ผู้ดูแลระบบสูงสุด"` to `ROLE_THAI` | 3 |
| [`app/create_admin.py`](file:///k:/Project_CheckID_Student/backend/app/create_admin.py) | Change `role="admin"` → `role="super_admin"` | 4 |
| [`app/main.py`](file:///k:/Project_CheckID_Student/backend/app/main.py) | Add `ensure_super_admin_exists()` in startup; register CSRF middleware | 5 |
| [`app/routers/admin.py`](file:///k:/Project_CheckID_Student/backend/app/routers/admin.py) | Add admin-account CRUD routes with `require_super_admin`, advisory lock helper, last-SA protection | 6 |
| [`templates/admin/base_admin.html`](file:///k:/Project_CheckID_Student/backend/templates/admin/base_admin.html) | Add conditional sidebar link for admin-accounts (visible only to `super_admin`) | 8 |
| [`static/js/i18n.js`](file:///k:/Project_CheckID_Student/backend/static/js/i18n.js) | Add TH/EN keys for admin-accounts UI | 9 |
| [`tests/conftest.py`](file:///k:/Project_CheckID_Student/backend/tests/conftest.py) | Add `super_admin_user`, `super_admin_client`, `regular_admin_user` fixtures | 10 |

### Files Created

| File | Purpose | Step |
|---|---|---|
| `app/middleware/__init__.py` | Package init | 5 |
| `app/middleware/csrf.py` | Origin/Referer CSRF validation middleware | 5 |
| `templates/admin/admin_accounts.html` | Full management UI | 7 |
| `tests/test_admin_accounts.py` | All admin-account test cases | 10 |
| `tests/test_csrf.py` | CSRF middleware test cases | 10 |

### Files NOT Modified

| File | Reason |
|---|---|
| `app/models.py` | No schema changes. `User.role` column already supports any string. |
| `app/database.py` | No changes needed. |
| `app/config.py` | No changes needed. |
| `app/websocket.py` | Unrelated to admin account management. |
| `app/routers/student.py` | Unrelated. |
| `app/routers/teacher.py` | No authorization changes (see Issue 3 analysis). |
| `static/css/admin.css` | Existing styles sufficient; new page reuses existing patterns. |
| `static/css/main.css` | Unrelated. |
| All student templates | Unrelated. |
| All teacher templates | Unrelated. |

### New Functions

| Function | Location | Purpose |
|---|---|---|
| `require_super_admin()` | `app/auth.py` | FastAPI dependency: require `super_admin` role |
| `ensure_super_admin_exists()` | `app/main.py` | Startup migration: promote bootstrap admin |
| `_acquire_super_admin_lock()` | `app/routers/admin.py` | Advisory lock for PostgreSQL |
| `ensure_not_last_super_admin()` | `app/routers/admin.py` | Validation: reject operations on last SA |
| `csrf_origin_check()` | `app/middleware/csrf.py` | ASGI middleware: Origin/Referer validation |

### New Routes

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/admin/admin-accounts` | `require_super_admin` | List admin accounts (only `role="admin"`) |
| `POST` | `/admin/admin-accounts/add` | `require_super_admin` | Create new admin account |
| `POST` | `/admin/admin-accounts/{id}/edit` | `require_super_admin` | Edit admin account |
| `POST` | `/admin/admin-accounts/{id}/suspend` | `require_super_admin` | Suspend admin account |
| `POST` | `/admin/admin-accounts/{id}/reactivate` | `require_super_admin` | Reactivate admin account |
| `POST` | `/admin/admin-accounts/{id}/delete` | `require_super_admin` | Permanently delete admin account |

### Database Objects

**No schema changes.** The `users` table already supports:
- `role` column: accepts `"super_admin"` as a string value.
- `is_active` column: boolean for suspend/reactivate.
- `username` column: `unique=True` for duplicate prevention.

**New advisory lock (PostgreSQL only):** Lock ID `7777777001` — not a database object; application-level convention.

---

## 7. Automated Test Plan

### Test Fixtures to Add (`conftest.py`)

```python
@pytest.fixture
def super_admin_user(db):
    """Create a super_admin user."""
    user = User(username="superadmin", password_hash=hash_password("super123"),
                display_name="Super Admin", role="super_admin", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    return user

@pytest.fixture
def super_admin_client(client, super_admin_user):
    """Client logged in as super_admin."""
    response = client.post("/login", data={"username": "superadmin", "password": "super123"}, follow_redirects=False)
    client.cookies = response.cookies
    return client

@pytest.fixture
def regular_admin_user(db):
    """Create a regular admin (distinct from bootstrap admin)."""
    user = User(username="admin2", password_hash=hash_password("admin456"),
                display_name="Regular Admin", role="admin", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    return user
```

### Complete Test Case Matrix

#### Authentication and Authorization (10 tests)

| # | Test | Expected |
|---|---|---|
| A1 | Super Admin can log in and access admin dashboard | 200 |
| A2 | Regular Admin can log in and access admin dashboard | 200 |
| A3 | Regular Admin gets 403 on `/admin/admin-accounts` | 403 |
| A4 | Regular Admin gets 403 on admin-accounts POST endpoints | 403 |
| A5 | Teacher gets 403 on `/admin/admin-accounts` | 403 |
| A6 | Unauthenticated user redirected from `/admin/admin-accounts` | Redirect |
| A7 | Suspended user with valid JWT cannot access protected routes | Redirect |
| A8 | Super Admin can access `/admin/admin-accounts` | 200 |
| A9 | Super Admin can access `/teacher/dashboard` | 200 |
| A10 | Teacher cannot access `/admin/dashboard` | 403 |

#### CRUD Operations (8 tests)

| # | Test | Expected |
|---|---|---|
| D1 | Super Admin can list admin accounts (only `role="admin"` shown) | 200, no super_admin in list |
| D2 | Super Admin can create new admin account | 303 redirect, user created |
| D3 | Duplicate username rejected with clear error | Error message |
| D4 | Newly created admin can log in | 303 redirect to dashboard |
| D5 | Edit username/display_name preserves password when `new_password` is empty | Password hash unchanged |
| D6 | Supplying `new_password` updates the hash | New hash, old password fails |
| D7 | Edit does not change `role` or `is_active` (mass-assignment prevention) | Fields unchanged |
| D8 | `role` cannot be set via client request | Hardcoded to `"admin"` |

#### Suspend / Reactivate / Delete (8 tests)

| # | Test | Expected |
|---|---|---|
| S1 | Super Admin can suspend an admin account | `is_active=False` |
| S2 | Suspended admin cannot log in | Login rejected |
| S3 | Super Admin can reactivate a suspended admin | `is_active=True` |
| S4 | Reactivated admin can log in again | 303 redirect |
| S5 | Super Admin can permanently delete an admin | User removed from DB |
| S6 | Deleted admin cannot log in | Login rejected |
| S7 | Audit logs preserved after admin deletion (SET NULL) | `user_id=NULL` in audit_logs |
| S8 | Cannot suspend/delete/modify Super Admin via management API | 403/404 (SA accounts not in scope) |

#### Last Super Admin Protection (6 tests + PostgreSQL-specific)

| # | Test | Expected |
|---|---|---|
| L1 | Cannot suspend the only active Super Admin | 409 error |
| L2 | Cannot delete the only active Super Admin | 409 error |
| L3 | Can suspend one of two Super Admins | Success |
| L4 | After suspending one SA, cannot suspend the remaining SA | 409 error |
| L5 | Protection applies regardless of frontend restrictions | Backend rejects |
| L6 | SQLite fallback works for serial protection | Same as L1-L5 |
| P1–P6 | PostgreSQL advisory lock + concurrency tests | See Section 1 |

#### Bootstrap and Migration (12 tests)

See Section 4 test table (M1–M12).

#### CSRF Middleware (8 tests)

See Section 2 test table (C1–C8).

#### Regression (5 tests)

| # | Test | Expected |
|---|---|---|
| R1 | Existing admin dashboard access works for both roles | 200 |
| R2 | Existing teacher management continues to work | 200, CRUD |
| R3 | Existing student management continues to work | 200, CRUD |
| R4 | Existing login/logout flow unchanged | Works |
| R5 | i18n keys exist for both TH and EN | Keys present |

**Total: 43 test cases** (+ 6 PostgreSQL-specific = 49 total)

---

## 8. Unchanged Application Features

The following features and files **will not be modified**:

| Category | Details |
|---|---|
| Student management | CRUD, import, export, history — all unchanged |
| Teacher management | CRUD, toggle — all unchanged |
| Activity management | CRUD — all unchanged |
| Session management | CRUD — all unchanged |
| Attendance management | Check-in, correction, manual add — all unchanged |
| QR check-in flow | Scan → verify → confirm — all unchanged |
| WebSocket real-time updates | `websocket.py`, `ConnectionManager` — unchanged |
| Excel export | `/admin/reports/export` — unchanged |
| PDF export | `/admin/reports/pdf`, teacher PDFs — unchanged |
| Audit logs | `/admin/audit-logs` — unchanged (new entries added, no existing entries modified) |
| Student check-in pages | All student templates — unchanged |
| Teacher pages | All teacher templates — unchanged |
| CSS files | `admin.css`, `main.css`, `student.css`, `teacher.css` — unchanged |
| Database schema | No `ALTER TABLE`, no new tables, no column changes |

---

## 9. Unresolved Risks and Assumptions

### Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | `GET /teacher/api/qr/{session_id}` is a state-changing GET endpoint | Medium | Documented for future remediation. Not in scope. |
| R2 | `GET /logout` is a state-changing GET endpoint (logout CSRF) | Low | Documented for future remediation. |
| R3 | Cookie `Secure` flag is not currently set in production | Medium | Will be added as part of this feature. |
| R4 | PostgreSQL `statement_timeout` on Supabase could cause advisory lock acquisition to fail | Low | If timeout is configured, the request fails with 500 and rolls back safely. No data corruption. |
| R5 | `ADMIN_USERNAME` or `ADMIN_PASSWORD` in `.env` could be changed without coordination | Low | Migration checks current DB state. If the bootstrap account doesn't match, it logs a warning and skips. |

### Assumptions

1. **Supabase PostgreSQL supports `pg_advisory_xact_lock`.** — Standard PostgreSQL function; Supabase has no documented restrictions on advisory locks.
2. **The bootstrap account currently exists in the production database with `role="admin"`.** — If it doesn't exist, the migration will skip and log a warning.
3. **No other application or process uses advisory lock ID `7777777001`.** — This ID is documented in the codebase and unlikely to collide.
4. **Tests will use in-memory SQLite by default.** PostgreSQL-specific tests require a separate test database URL configured via environment variable.

### Decisions Requiring Approval

1. **Advisory lock ID `7777777001`** — Is this acceptable, or should a different mechanism (e.g., dedicated lock table) be used?
2. **Origin/Referer CSRF middleware** — Is this acceptable as a defense-in-depth measure, or should full CSRF tokens be implemented app-wide?
3. **`GET /teacher/api/qr/{session_id}` remediation** — Should this be addressed now or deferred to a separate ticket?
4. **`Secure` cookie flag** — Confirming that the development environment uses SQLite and production uses PostgreSQL/HTTPS, so the detection heuristic (`sqlite` in URL → dev) is correct.
