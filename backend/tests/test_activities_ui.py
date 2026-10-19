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


def test_activity_create_and_edit_with_rooms(admin_client, db):
    # Test GET form contains room toggle and inputs
    res = admin_client.get("/admin/activities/add")
    assert res.status_code == 200
    assert "toggleSpecifyRooms" in res.text
    assert "eligible_rooms" in res.text

    # Test POST add with specific grades and rooms
    post_res = admin_client.post("/admin/activities/add", data={
        "name": "Robotics Camp 2026",
        "description": "Robotics coding camp",
        "start_date": "2026-12-01",
        "end_date": "2026-12-03",
        "status": "active",
        "eligible_grades": ["M.4", "M.5"],
        "eligible_rooms": ["1", "2", "3"],
    }, follow_redirects=True)
    assert post_res.status_code == 200

    act = db.query(Activity).filter(Activity.name == "Robotics Camp 2026").first()
    assert act is not None
    assert act.eligible_grades == "M.4,M.5"
    assert act.eligible_rooms == "1,2,3"

    # Test GET edit form loads selected rooms and toggle checked
    edit_get = admin_client.get(f"/admin/activities/{act.id}/edit")
    assert edit_get.status_code == 200
    assert 'checked' in edit_get.text

    # Test POST edit to update rooms
    edit_post = admin_client.post(f"/admin/activities/{act.id}/edit", data={
        "name": "Robotics Camp 2026",
        "description": "Updated robotics camp",
        "start_date": "2026-12-01",
        "end_date": "2026-12-03",
        "status": "active",
        "eligible_grades": ["M.4"],
        "eligible_rooms": ["1"],
    }, follow_redirects=True)
    assert edit_post.status_code == 200

    db.refresh(act)
    assert act.eligible_grades == "M.4"
    assert act.eligible_rooms == "1"


def test_activity_duplicate_flow(admin_client, db):
    # Create base activity with a session
    act = Activity(
        name="ฟิสิกส์ ม.6 ต้นฉบับ",
        description="คลาสเรียนฟิสิกส์",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        status="active",
        eligible_grades="M.6",
        eligible_rooms="1,2"
    )
    db.add(act)
    db.commit()
    db.refresh(act)

    sess = ActivitySession(
        activity_id=act.id,
        name="รอบเช้า สัปดาห์ 1",
        date=date(2026, 10, 5),
        start_time=time(8, 30),
        end_time=time(10, 30),
        status="active"
    )
    db.add(sess)
    db.commit()

    # Verify UI contains duplicate button and modal
    list_res = admin_client.get("/admin/activities")
    assert list_res.status_code == 200
    assert "openDuplicateModal" in list_res.text
    assert "duplicateModal" in list_res.text
    assert "ทำซ้ำ" in list_res.text

    # Test duplicating with sessions
    dup_res = admin_client.post(f"/admin/activities/{act.id}/duplicate", data={
        "new_name": "ฟิสิกส์ ม.6 สัปดาห์ที่ 2",
        "copy_sessions": "true",
        "status": "draft"
    }, follow_redirects=True)
    assert dup_res.status_code == 200
    assert "ทำซ้ำกิจกรรมสำเร็จแล้ว" in dup_res.text

    # Verify new activity in database
    duplicated_act = db.query(Activity).filter(Activity.name == "ฟิสิกส์ ม.6 สัปดาห์ที่ 2").first()
    assert duplicated_act is not None
    assert duplicated_act.id != act.id
    assert duplicated_act.description == act.description
    assert duplicated_act.start_date == act.start_date
    assert duplicated_act.end_date == act.end_date
    assert duplicated_act.status == "draft"
    assert duplicated_act.eligible_grades == "M.6"
    assert duplicated_act.eligible_rooms == "1,2"

    # Verify sessions were duplicated
    dup_sessions = db.query(ActivitySession).filter(ActivitySession.activity_id == duplicated_act.id).all()
    assert len(dup_sessions) == 1
    assert dup_sessions[0].name == "รอบเช้า สัปดาห์ 1"
    assert dup_sessions[0].status == "draft"  # Cloned session should be draft

    # Test duplicating without custom name (default to (สำเนา)) and without sessions
    dup_res2 = admin_client.post(f"/admin/activities/{act.id}/duplicate", data={
        "new_name": "",
        "copy_sessions": "false",
        "status": "draft"
    }, follow_redirects=True)
    assert dup_res2.status_code == 200

    copy_act = db.query(Activity).filter(Activity.name == f"{act.name} (สำเนา)").first()
    assert copy_act is not None
    copy_sessions = db.query(ActivitySession).filter(ActivitySession.activity_id == copy_act.id).all()
    assert len(copy_sessions) == 0


def test_session_duplicate_flow(admin_client, db):
    # Setup activity and a session
    act = Activity(
        name="เคมี ม.5 ทดลอง",
        start_date=date(2026, 11, 1),
        status="active"
    )
    db.add(act)
    db.commit()
    db.refresh(act)

    sess = ActivitySession(
        activity_id=act.id,
        name="ปฏิบัติการกลุ่มที่ 1",
        date=date(2026, 11, 2),
        start_time=time(9, 0),
        end_time=time(11, 0),
        status="active"
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    # 1. Verify UI renders duplicate button and modal
    sess_ui = admin_client.get(f"/admin/activities/{act.id}/sessions")
    assert sess_ui.status_code == 200
    assert "openDuplicateSessionModal" in sess_ui.text
    assert "duplicateSessionModal" in sess_ui.text

    # 2. Duplicate session with custom name and date
    dup_res = admin_client.post(f"/admin/sessions/{sess.id}/duplicate", data={
        "name": "ปฏิบัติการกลุ่มที่ 2",
        "session_date": "2026-11-03",
        "start_time": "13:00",
        "end_time": "15:00",
        "status": "draft"
    }, follow_redirects=True)
    assert dup_res.status_code == 200
    assert "ทำซ้ำรอบกิจกรรมสำเร็จแล้ว" in dup_res.text

    # Verify duplicated session in DB
    dup_sess = db.query(ActivitySession).filter(ActivitySession.name == "ปฏิบัติการกลุ่มที่ 2").first()
    assert dup_sess is not None
    assert dup_sess.id != sess.id
    assert dup_sess.activity_id == act.id
    assert dup_sess.date == date(2026, 11, 3)
    assert dup_sess.start_time == time(13, 0)
    assert dup_sess.end_time == time(15, 0)
    assert dup_sess.status == "draft"

    # 3. Duplicate without custom name (defaults to (สำเนา))
    dup_res2 = admin_client.post(f"/admin/sessions/{sess.id}/duplicate", data={
        "name": "",
        "session_date": "",
        "start_time": "",
        "end_time": "",
        "status": "draft"
    }, follow_redirects=True)
    assert dup_res2.status_code == 200

    auto_copy = db.query(ActivitySession).filter(ActivitySession.name == f"{sess.name} (สำเนา)").first()
    assert auto_copy is not None
    assert auto_copy.date == sess.date
    assert auto_copy.start_time == sess.start_time
    assert auto_copy.end_time == sess.end_time

