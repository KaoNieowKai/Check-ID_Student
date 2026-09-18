"""Shared Jinja2Templates configuration with Bangkok timezone and Thai filters."""

from datetime import datetime, date, time, timezone, timedelta
from fastapi.templating import Jinja2Templates

BANGKOK_TZ = timezone(timedelta(hours=7), name="Asia/Bangkok")
UTC_TZ = timezone.utc

templates = Jinja2Templates(directory="templates")

STATUS_THAI = {
    "draft": "แบบร่าง",
    "active": "กำลังใช้งาน",
    "scheduled": "กำหนดการแล้ว",
    "completed": "เสร็จสิ้น",
    "cancelled": "ยกเลิก",
    "present": "มา",
    "late": "สาย",
    "absent": "ขาด",
    "leave": "ลา",
}

ROLE_THAI = {
    "admin": "ผู้ดูแลระบบ",
    "teacher": "ครู",
    "student": "นักเรียน",
}


def _ensure_bangkok_dt(val):
    """Convert aware datetime or ISO string to Asia/Bangkok datetime. Naive datetimes are assumed to be already in BKK time."""
    if not val:
        return None
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val)
        except Exception:
            return None
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            val = val.astimezone(BANGKOK_TZ)
        return val
    return None


def to_bangkok(val):
    """Format timestamp to Thai Bangkok format: DD/MM/YYYY HH:MM:SS."""
    if not val:
        return "—"
    dt = _ensure_bangkok_dt(val)
    if dt:
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    if isinstance(val, date):
        return val.strftime("%d/%m/%Y")
    return str(val)


def to_bangkok_date(val):
    """Format date to DD/MM/YYYY in Bangkok timezone."""
    if not val:
        return "—"
    dt = _ensure_bangkok_dt(val)
    if dt:
        return dt.strftime("%d/%m/%Y")
    if isinstance(val, date):
        return val.strftime("%d/%m/%Y")
    return str(val)


def to_bangkok_time(val):
    """Format time to HH:MM in Bangkok timezone."""
    if not val:
        return "—"
    dt = _ensure_bangkok_dt(val)
    if dt:
        return dt.strftime("%H:%M")
    if isinstance(val, time):
        return val.strftime("%H:%M")
    return str(val)


def thai_status(val):
    """Translate status key to Thai."""
    if not val:
        return "—"
    return STATUS_THAI.get(str(val).lower(), str(val))


def thai_role(val):
    """Translate user role to Thai."""
    if not val:
        return "—"
    return ROLE_THAI.get(str(val).lower(), str(val))


# Register filters
templates.env.filters["to_bangkok"] = to_bangkok
templates.env.filters["to_bangkok_date"] = to_bangkok_date
templates.env.filters["to_bangkok_time"] = to_bangkok_time
templates.env.filters["thai_status"] = thai_status
templates.env.filters["thai_role"] = thai_role
