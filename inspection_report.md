# Revised Implementation Plan — Admin Account Management

## Addressing Each Requirement

---

### 1. Safe Super Admin Initialization

**Current state:** `create_admin.py` creates user with `role="admin"`. No `super_admin` role exists.

**Approach:**
- Modify `create_admin.py` to create the bootstrap account with `role="super_admin"` instead of `role="admin"`.
- Add a **one-time, idempotent migration function** `ensure_super_admin_exists()` called at app startup.
- This function checks: *"Does at least one active `super_admin` exist?"*
  - If **yes** → do nothing (safe to run repeatedly).
  - If **no** → check if a user with `username == settings.ADMIN_USERNAME` exists AND has `role="admin"`:
    - If found, promote **only that specific account** to `super_admin`. Log the promotion.
    - If not found, skip (admin must run `create_admin.py` manually).
- **Never** promotes all admins. **Never** promotes arbitrary accounts.
- Once any `super_admin` exists, the function becomes a no-op permanently.

**Risk mitigation:** The migration is wrapped in a transaction and checks a precise condition. It cannot promote the wrong account.

---

### 2. Strengthen Authentication and Authorization

**Current state:**
- `get_current_user_from_cookie()` already queries the DB: `User.username == username, User.is_active == True`.
- This means suspended users (`is_active=False`) are **already rejected** even with a valid JWT — good.
- Role changes also take effect immediately since the role is read from DB at each request, not from the JWT payload.

**Approach:**
- Update `require_admin` to accept **both** `role == "admin"` and `role == "super_admin"`:
  ```python
  if user.role not in ("admin", "super_admin"):
      raise HTTPException(status_code=403, ...)
  ```
- Add new `require_super_admin` dependency:
  ```python
  def require_super_admin(request, db):
      user = get_current_user_from_cookie(request, db)
      if user is None:
          raise redirect to /login
      if user.role != "super_admin":
          raise HTTPException(status_code=403, ...)
      return user
  ```
- Both dependencies read the **current DB state**, not the JWT role. This ensures:
  - Suspended users lose access immediately.
  - Role changes take effect on the next request.
  - Old JWTs cannot bypass updated permissions.

**No changes needed to the JWT structure** — the `sub` claim (username) is what matters for DB lookup.

---

### 3. Protect the Last Active Super Admin

**Approach:**
- Before any suspend/delete/demote operation on a `super_admin`, count active super admins:
  ```python
  active_count = db.query(func.count(User.id)).filter(
      User.role == "super_admin", User.is_active == True
  ).scalar()
  ```
- If `active_count <= 1` and the target is the last one, **reject the operation** with a clear error.
- Use `with_for_update()` on the count query within a transaction to prevent TOCTOU races:
  ```python
  active_count = db.query(func.count(User.id)).filter(
      User.role == "super_admin", User.is_active == True
  ).with_for_update().scalar()
  ```
- The management interface **never shows** Super Admin accounts as manageable targets — but this is defense-in-depth, not the primary protection. The backend enforces the rule regardless.
- Return localized error messages:
  - TH: `ไม่สามารถดำเนินการได้ เนื่องจากเป็น Super Admin คนสุดท้ายในระบบ`
  - EN: `Cannot perform this operation on the last active Super Admin.`

> [!IMPORTANT]
> For SQLite (dev/test), `SELECT ... FOR UPDATE` is not supported. The implementation will use a regular count query in SQLite mode but use `FOR UPDATE` in PostgreSQL. SQLite's transaction isolation provides adequate protection for single-server development.

---

### 4. Audit Log and Account Deletion

**Current state:**
- `AuditLog.user_id` has `ForeignKey("users.id", ondelete="SET NULL")`.
- This means deleting a user **sets `user_id` to NULL** in audit logs — audit records are preserved.

**Approach:**
- Before deleting an admin account:
  1. Verify the target is `role="admin"` (not `super_admin`).
  2. Check for foreign-key dependencies beyond audit logs.
  3. The `ondelete="SET NULL"` ensures audit history survives deletion.
- Log a `admin_account_deleted` audit entry **before** the delete (recording the acting super_admin, the target account details).
- **All account-management actions are logged:**
  - `admin_account_created` — new admin created
  - `admin_account_edited` — username/display_name changed
  - `admin_account_password_reset` — password was reset (no password/hash logged)
  - `admin_account_suspended` — account suspended
  - `admin_account_reactivated` — account reactivated
  - `admin_account_deleted` — permanent deletion
- **Never log** passwords, hashes, tokens, or secrets.

---

### 5. CSRF Protection

**Current state analysis:**
- Auth uses JWT in httpOnly cookies with `samesite="lax"`.
- `SameSite=Lax` **blocks cross-site POST requests** from external origins — this is the browser-level CSRF protection.
- **None of the existing 20+ POST endpoints** in the app use CSRF tokens. The entire app relies on `SameSite=Lax` as its CSRF defense.

**Decision:** Follow the existing security convention.
- The new admin account management POST endpoints will have the same `SameSite=Lax` cookie protection as all other endpoints.
- Adding CSRF tokens only to the new endpoints would be inconsistent and provide a false sense of security (the rest of the app would remain unprotected).
- **If CSRF tokens are desired**, they should be added as a separate, app-wide enhancement — not scoped to this feature alone.

> [!NOTE]
> `SameSite=Lax` is considered adequate CSRF protection for modern browsers. All major browsers have supported it since 2020.

---

### 6. Restrict Super Admin Privileges

**Approach:**
- All admin account management routes use `require_super_admin` dependency.
- Account creation **always sets** `role="admin"` server-side. The role is never accepted from the client:
  ```python
  new_user = User(
      username=username,
      display_name=display_name,
      password_hash=hash_password(password),
      role="admin",  # hardcoded, never from client
      is_active=True,
  )
  ```
- The management page queries **only** `role="admin"` accounts — Super Admin accounts never appear in the list.
- The sidebar nav link for "Admin Accounts" is rendered only when `user.role == "super_admin"` in the template.
- **Backend enforcement** is independent of frontend visibility — even if a regular admin crafts a direct request, `require_super_admin` rejects it with 403.

---

### 7. Enforce Database Integrity

**Current state:** `User.username` has `unique=True, nullable=False` at the database level.

**Approach:**
- Catch `IntegrityError` on insert/update operations and return a clear duplicate-username error.
- Validate inputs server-side:
  - Username: required, stripped, length 1-50, no special characters beyond alphanumerics/underscores/dots.
  - Display name: required, stripped, length 1-100.
  - Password: required for creation, min 6 characters (matching existing pattern from teacher management).
  - Role: **never accepted from client** — always `"admin"`.
- Use explicit field assignment (not `**kwargs` or `dict.update()`) to prevent mass-assignment:
  ```python
  user.username = validated_username
  user.display_name = validated_display_name
  # role, is_active are NEVER set from request data
  ```
- **Never expose** in responses: `password_hash`, JWT secrets, database credentials.

---

### 8. Preserve Password Security

**Approach:**
- Use existing `hash_password()` (bcrypt via passlib) for all new accounts and password resets.
- Use existing `verify_password()` — no algorithm changes.
- New accounts authenticate through the existing `/login` flow without modification.
- Password reset in edit form:
  - If `new_password` field is empty → **no change** to `password_hash`.
  - If provided → validate (min 6 chars), hash with `hash_password()`, update.
- **Never store, log, or return** plaintext passwords or hashes.

---

### 9. Preserve Existing Application Behavior

**Changes that preserve compatibility:**

| Component | Change | Impact |
|---|---|---|
| `require_admin` | Accept `super_admin` in addition to `admin` | Super Admin retains all existing admin access |
| Login redirect | Add `super_admin` → `/admin/dashboard` | Same destination as `admin` |
| `get_current_user_from_cookie` | No change needed | Already queries DB by username + is_active |
| `require_teacher` | Add `super_admin` to allowed roles | Super Admin can access teacher routes too |
| Sidebar nav | Conditional "Admin Accounts" link | No visual change for regular admins |
| All existing routes | No changes | Student, Teacher, QR, attendance, reports all unchanged |

**Files NOT modified:**
- `routers/student.py` — no changes
- `routers/teacher.py` — no changes  
- `websocket.py` — no changes
- All student/teacher/activity templates — no changes
- `admin.css`, `main.css`, `student.css`, `teacher.css` — no changes
- Excel/PDF export logic — no changes

---

### 10. Test Plan

Tests will be added in `tests/test_admin_accounts.py` and `tests/conftest.py`:

**Fixtures to add:**
- `super_admin_user` — creates a user with `role="super_admin"`
- `super_admin_client` — logged-in client as super_admin
- `regular_admin_user` — creates a user with `role="admin"` (distinct from bootstrap admin)

**Test cases:**

| # | Test | Category |
|---|---|---|
| 1 | Super Admin initialization is idempotent | Init |
| 2 | Bootstrap migration promotes only the specific bootstrap account | Init |
| 3 | Super Admin can log in and access admin dashboard | Auth |
| 4 | Regular Admin can log in and access admin dashboard | Auth |
| 5 | Regular Admin gets 403 on admin-accounts page | Auth |
| 6 | Regular Admin gets 403 on admin-accounts API endpoints | Auth |
| 7 | Unauthenticated user gets redirected from admin-accounts | Auth |
| 8 | Suspended user with valid JWT cannot access protected routes | Auth |
| 9 | Super Admin can list admin accounts (only `role="admin"`) | CRUD |
| 10 | Super Admin can create a new admin account | CRUD |
| 11 | Duplicate username is rejected with clear error | CRUD |
| 12 | Newly created admin can log in with initial password | CRUD |
| 13 | Passwords are stored as bcrypt hashes, not plaintext | Security |
| 14 | API responses never expose password_hash | Security |
| 15 | Edit username/display_name preserves password when new_password is empty | Edit |
| 16 | Supplying new_password updates the hash | Edit |
| 17 | Edit does not change role or is_active | Edit |
| 18 | Super Admin can suspend an admin account | Suspend |
| 19 | Suspended admin cannot log in | Suspend |
| 20 | Super Admin can reactivate a suspended admin | Reactivate |
| 21 | Reactivated admin can log in again | Reactivate |
| 22 | Super Admin can permanently delete an admin | Delete |
| 23 | Deleted admin cannot log in | Delete |
| 24 | Audit logs are preserved after admin deletion (SET NULL) | Delete |
| 25 | Super Admin accounts don't appear in management list | Protection |
| 26 | Cannot suspend/delete/modify Super Admin via management API | Protection |
| 27 | Cannot delete/suspend the last active Super Admin | Protection |
| 28 | Role cannot be set via client request (mass-assignment prevention) | Security |
| 29 | Regular Admin cannot change own role | Security |
| 30 | Existing admin dashboard access works for both roles | Regression |
| 31 | Existing teacher management continues to work | Regression |
| 32 | Existing student management continues to work | Regression |
| 33 | Existing login/logout flow unchanged | Regression |
| 34 | i18n keys exist for both TH and EN | Localization |

---

## Implementation Steps (In Order)

### Step 1: Update `app/auth.py`
- Modify `require_admin`: accept `super_admin` too
- Modify `require_teacher`: accept `super_admin` too  
- Add `require_super_admin` dependency
- **No other changes**

### Step 2: Update `app/routers/auth.py`
- Add `super_admin` to login redirect logic

### Step 3: Update `app/templating.py`
- Add `super_admin` to `ROLE_THAI` dictionary

### Step 4: Update `app/create_admin.py`
- Change bootstrap role to `super_admin`

### Step 5: Update `app/main.py`
- Add idempotent `ensure_super_admin_exists()` in startup

### Step 6: Add admin account management routes to `app/routers/admin.py`
- All new routes under `/admin/admin-accounts/`
- All protected by `require_super_admin`
- Server-side validation, explicit field assignment
- Last-super-admin protection with transactional checks
- IntegrityError handling for duplicate usernames
- Audit logging for all operations

### Step 7: Create `templates/admin/admin_accounts.html`
- Full management UI with search, filter, create, edit, suspend, reactivate, delete
- Confirmation modals for destructive actions
- All strings use `data-i18n` attributes

### Step 8: Update `templates/admin/base_admin.html`
- Add conditional sidebar link for super_admin

### Step 9: Update `static/js/i18n.js`
- Add all new TH/EN translation keys

### Step 10: Update tests
- Add fixtures in `conftest.py`
- Create `test_admin_accounts.py` with all 34 test cases

### Step 11: Run all tests and verify regression
