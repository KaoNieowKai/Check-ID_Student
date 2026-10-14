"""Tests for redesigned Activity Management UI and backend routes."""

import pytest
from datetime import date, time
from app.models import Activity, ActivitySession, AttendanceRecord, Student


def test_activities_list_renders_ok(admin_client, sample_activity):
    activity, sessions = sample_activity
    res = admin_client.get("/admin/activities")
    assert res.status_code == 200
    html = res.text
    # Verify redesigned elements
    assert "จัดการกิจกรรม" in html
    assert "act-filter-bar" in html
    assert "act-search-box" in html
    assert "act-sort-select" in html
    assert "act-cards-grid" in html
    assert "act-guide" in html
    assert activity.name in html
    assert "activities.css" in html


def test_activities_list_filter(admin_client, db):
    act_active = Activity(name="Active Camp", status="active", start_date=date(2026, 10, 1))
    act_draft = Activity(name="Draft Workshop", status="draft", start_date=date(2026, 10, 2))
    db.add_all([act_active, act_draft])
    db.commit()

    # Filter active
    res = admin_client.get("/admin/activities?status=active")
    assert res.status_code == 200
    assert "Active Camp" in res.text
    assert "Draft Workshop" not in res.text

    # Filter draft
    res2 = admin_client.get("/admin/activities?status=draft")
    assert res2.status_code == 200
    assert "Draft Workshop" in res2.text
    assert "Active Camp" not in res2.text


def test_activity_form_add_and_submit(admin_client, db):
    # GET form
    get_res = admin_client.get("/admin/activities/add")
    assert get_res.status_code == 200
    assert "act-form-card" in get_res.text
    assert "act-grade-checkbox" in get_res.text

    # POST submit
    post_res = admin_client.post("/admin/activities/add", data={
        "name": "Science Fair 2026",
        "description": "Annual science project exhibition",
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "status": "scheduled",
        "eligible_grades": ["M.1", "M.2", "M.3"],
    }, follow_redirects=True)
    assert post_res.status_code == 200
    assert "Science Fair 2026" in post_res.text

    act = db.query(Activity).filter(Activity.name == "Science Fair 2026").first()
    assert act is not None
    assert act.status == "scheduled"
    assert act.eligible_grades == "M.1,M.2,M.3"


def test_activity_form_edit_and_submit(admin_client, sample_activity, db):
    activity, _ = sample_activity
    # GET edit form
    get_res = admin_client.get(f"/admin/activities/{activity.id}/edit")
    assert get_res.status_code == 200
    assert activity.name in get_res.text

    # POST update
    post_res = admin_client.post(f"/admin/activities/{activity.id}/edit", data={
        "name": "Sports Day 2026 Updated",
        "description": "Updated description",
        "start_date": "2026-09-20",
        "end_date": "2026-09-22",
        "status": "active",
        "eligible_grades": ["M.4", "M.5", "M.6"],
    }, follow_redirects=True)
    assert post_res.status_code == 200
    assert "Sports Day 2026 Updated" in post_res.text

    db.refresh(activity)
    assert activity.name == "Sports Day 2026 Updated"
    assert activity.eligible_grades == "M.4,M.5,M.6"


def test_sessions_list_and_management(admin_client, sample_activity, db):
    activity, sessions = sample_activity

    # GET sessions page
    res = admin_client.get(f"/admin/activities/{activity.id}/sessions")
    assert res.status_code == 200
    assert "sess-layout" in res.text
    assert "sess-form-card" in res.text
    assert sessions[0].name in res.text

    # POST add session
    add_res = admin_client.post(f"/admin/activities/{activity.id}/sessions/add", data={
        "name": "Day 2 Closing Ceremony",
        "session_date": "2026-09-21",
        "start_time": "15:00",
        "end_time": "17:00",
        "status": "scheduled",
    }, follow_redirects=True)
    assert add_res.status_code == 200
    assert "Day 2 Closing Ceremony" in add_res.text

    new_sess = db.query(ActivitySession).filter(ActivitySession.name == "Day 2 Closing Ceremony").first()
    assert new_sess is not None

    # POST edit session
    edit_res = admin_client.post(f"/admin/sessions/{new_sess.id}/edit", data={
        "name": "Day 2 Grand Finale",
        "session_date": "2026-09-21",
        "start_time": "15:30",
        "end_time": "18:00",
        "status": "active",
    }, follow_redirects=True)
    assert edit_res.status_code == 200
    assert "Day 2 Grand Finale" in edit_res.text

    # POST delete session
    del_res = admin_client.post(f"/admin/sessions/{new_sess.id}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    assert db.query(ActivitySession).filter(ActivitySession.id == new_sess.id).first() is None


def test_delete_activity_restrictions(admin_client, sample_activity, db):
    activity, sessions = sample_activity
    # Both sessions are active, cannot delete
    del_res = admin_client.post(f"/admin/activities/{activity.id}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    assert "ไม่สามารถลบกิจกรรมที่มีรอบกำลังเปิดใช้งานอยู่ได้" in del_res.text
    assert db.query(Activity).filter(Activity.id == activity.id).first() is not None

    # Set sessions to draft or completed
    for s in sessions:
        s.status = "completed"
    db.commit()

    # Now deletion succeeds
    del_res2 = admin_client.post(f"/admin/activities/{activity.id}/delete", follow_redirects=True)
    assert del_res2.status_code == 200
    assert db.query(Activity).filter(Activity.id == activity.id).first() is None
