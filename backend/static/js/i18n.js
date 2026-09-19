/**
 * i18n Translation Engine for Student Activity Attendance System
 * Supports: Thai (th) and English (en)
 * Features:
 * - Direct data-i18n, data-i18n-placeholder, and data-i18n-title translation
 * - Full bi-directional phrase mapping for dynamic text
 * - Dynamic pattern matching for counters, rooms, and pagination
 * - Dynamic document.title translation
 * - MutationObserver to automatically translate newly added DOM nodes
 * - Persistent language preference via localStorage and cookies
 */

const I18N_DICTIONARY = {
    th: {
        // App / Brand
        'app_name': 'ระบบเช็คชื่อกิจกรรมนักเรียน',
        'app_subtitle': 'Activity Attendance Management System',
        'brand_logo': 'ระบบเช็คชื่อ',
        'attendance': 'การเช็คชื่อ',

        // Navigation Sidebar
        'nav_dashboard': 'แดชบอร์ด',
        'sec_students': 'จัดการนักเรียน',
        'nav_students': 'รายชื่อนักเรียน',
        'nav_import': 'นำเข้า Excel',
        'sec_teachers': 'จัดการครู',
        'nav_teachers': 'รายชื่อครู',
        'sec_activities': 'จัดการกิจกรรม',
        'nav_activities': 'รายการกิจกรรม',
        'sec_attendance': 'การเข้าร่วม',
        'nav_attendance': 'จัดการการเข้าร่วม',
        'sec_reports': 'รายงาน',
        'nav_reports': 'ส่งออก Excel',
        'sec_system': 'ระบบ',
        'nav_audit_logs': 'บันทึกการใช้งาน',
        'nav_logout': 'ออกจากระบบ',
        'role_admin': 'ผู้ดูแลระบบ',
        'role_teacher': 'ครู',

        // Page Titles & Headings
        'title_dashboard': 'แดชบอร์ด',
        'title_activities': 'จัดการกิจกรรม',
        'title_activity_new': 'สร้างกิจกรรมใหม่',
        'title_activity_edit': 'แก้ไขกิจกรรม',
        'title_students': 'จัดการข้อมูลนักเรียน',
        'title_student_new': 'เพิ่มนักเรียนใหม่',
        'title_student_edit': 'แก้ไขข้อมูลนักเรียน',
        'title_student_import': 'นำเข้าข้อมูลนักเรียนจากไฟล์ Excel',
        'title_student_history': 'ประวัติการเข้าร่วมกิจกรรม',
        'title_teachers': 'จัดการข้อมูลครู',
        'title_sessions': 'รอบกิจกรรม',
        'title_attendance': 'จัดการการเช็คชื่อ',
        'title_reports': 'รายงานและส่งออกข้อมูล',
        'title_audit_logs': 'บันทึกประวัติการใช้งานระบบ',

        // Dashboard Stat Cards & Sections
        'total_students': 'นักเรียนทั้งหมด',
        'total_teachers': 'ครูทั้งหมด',
        'total_activities': 'กิจกรรมทั้งหมด',
        'active_sessions': 'เซสชันที่ใช้งาน',
        'recent_activities': 'กิจกรรมล่าสุด',
        'recent_audit_logs': 'บันทึกระบบล่าสุด',
        'view_all': 'ดูทั้งหมด',
        'view_sessions': 'ดูรอบ',
        'no_activities_yet': 'ยังไม่มีกิจกรรม',
        'create_one': 'สร้างกิจกรรมใหม่',
        'create_first_activity': 'สร้างกิจกรรมแรก',
        'no_audit_logs_yet': 'ยังไม่มีบันทึกระบบ',
        'sys_user': 'ระบบ',

        // Filters & Status Badges
        'filter_all': 'ทั้งหมด',
        'filter_draft': 'แบบร่าง',
        'filter_active': 'กำลังใช้งาน',
        'filter_scheduled': 'กำหนดการแล้ว',
        'filter_completed': 'เสร็จสิ้น',
        'filter_cancelled': 'ยกเลิก',
        'status_active': 'กำลังใช้งาน',
        'status_disabled': 'ปิดใช้งาน',
        'status_completed': 'เสร็จสิ้น',
        'status_draft': 'แบบร่าง',
        'status_scheduled': 'กำหนดการแล้ว',
        'status_cancelled': 'ยกเลิก',
        'status_present': 'มา',
        'status_late': 'สาย',
        'status_leave': 'ลา',
        'status_absent': 'ขาด',
        'status_manual': 'ปรับแก้โดยครู',

        // Common Buttons & Actions
        'btn_create_activity': 'สร้างกิจกรรมใหม่',
        'btn_create_first_activity': 'สร้างกิจกรรมแรก',
        'btn_sessions': 'รอบกิจกรรม',
        'btn_edit': 'แก้ไข',
        'btn_delete': 'ลบ',
        'btn_cancel': 'ยกเลิก',
        'btn_cancel_edit': 'ยกเลิกการแก้ไข',
        'btn_confirm_delete': 'ยืนยันการลบ',
        'btn_save_changes': 'บันทึกการเปลี่ยนแปลง',
        'btn_create': 'สร้างกิจกรรม',
        'btn_add_student': 'เพิ่มนักเรียน',
        'btn_import_excel': 'นำเข้า Excel',
        'btn_filter': 'กรองข้อมูล',
        'btn_view_all': 'ดูทั้งหมด',
        'btn_view_sessions': 'ดูรอบ',
        'btn_add_teacher': 'เพิ่มครู',
        'btn_reset_password': 'รีเซ็ตรหัสผ่าน',
        'btn_enable': 'เปิดใช้งาน',
        'btn_disable': 'ปิดใช้งาน',
        'btn_save_password': 'บันทึกรหัสผ่านใหม่',
        'btn_correct_status': 'แก้ไขสถานะ',
        'btn_save_correction': 'บันทึกการแก้ไข',
        'btn_export_excel': 'ส่งออกเป็นไฟล์ Excel',
        'btn_choose_file': 'เลือกไฟล์',
        'btn_upload_preview': 'อัปโหลดและตรวจสอบข้อมูล',
        'btn_confirm_import': 'ยืนยันการนำเข้าข้อมูล',
        'btn_download_template': 'ดาวน์โหลดไฟล์ตัวอย่าง',
        'btn_view_students': 'ดูรายชื่อนักเรียน',
        'btn_prev': '← ก่อนหน้า',
        'btn_next': 'ถัดไป →',
        'btn_search': 'ค้นหา',
        'btn_history': 'ประวัติการเช็คชื่อ',

        // Activity Management
        'lbl_activity_name': 'ชื่อกิจกรรม',
        'lbl_activity_desc': 'รายละเอียดกิจกรรม',
        'lbl_start_date': 'วันที่เริ่มต้น',
        'lbl_end_date': 'วันที่สิ้นสุด',
        'lbl_status': 'สถานะ',
        'lbl_eligible_grades': 'ระดับชั้นที่เข้าร่วม (เว้นว่างไว้หากเข้าร่วมได้ทุกระดับชั้น)',
        'ph_activity_name': 'เช่น วันกีฬาสี ประจำปี 2026',
        'ph_activity_desc': 'กรอกรายละเอียดสั้นๆ เกี่ยวกับกิจกรรม...',
        'all_grades_badge': '🎓 ทุกระดับชั้น',
        'all_grades': 'ทุกระดับชั้น',
        'all_rooms': 'ทุกห้อง',
        'empty_activities': 'ยังไม่มีกิจกรรมในระบบ',
        'modal_delete_activity_title': 'ยืนยันการลบกิจกรรม',
        'modal_delete_activity_warning': 'การดำเนินการนี้จะลบข้อมูลรอบกิจกรรม ประวัติการเช็คชื่อ และ QR Code ทั้งหมดที่เกี่ยวข้องกับกิจกรรมนี้อย่างถาวร',
        'modal_delete_activity_prefix': '⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบกิจกรรม',
        'modal_delete_session_confirm': 'คุณแน่ใจหรือไม่ว่าต้องการลบรอบกิจกรรมนี้?',
        'confirm_disable_student': 'คุณแน่ใจหรือไม่ว่าต้องการระงับการใช้งานนักเรียนคนนี้?',
        'confirm_import_prompt': 'ยืนยันการนำเข้าข้อมูลนักเรียน',

        // Table Headers
        'th_activity_name': 'ชื่อกิจกรรม',
        'th_status': 'สถานะ',
        'th_date': 'วันที่',
        'th_actions': 'จัดการ',
        'th_student_id': 'รหัสนักเรียน',
        'th_fullname': 'ชื่อ-นามสกุล',
        'th_grade': 'ระดับชั้น',
        'th_room': 'ห้อง',
        'th_username': 'ชื่อผู้ใช้',
        'th_display_name': 'ชื่อที่แสดง',
        'th_created_date': 'วันที่สร้าง',
        'th_timestamp': 'วันที่และเวลา',
        'th_user': 'ผู้ใช้งาน',
        'th_operation': 'การดำเนินการ',
        'th_target': 'เป้าหมาย',
        'th_details': 'รายละเอียด',
        'th_checkin_time': 'เวลาเช็คชื่อ',
        'th_checkin_method': 'วิธีการเช็คชื่อ',
        'th_index': 'ลำดับ',
        'th_sheet': 'แผ่นงาน',
        'th_session_round': 'รอบกิจกรรม',
        'th_activity': 'กิจกรรม',

        // Student Management
        'ph_search_student': 'ค้นหาด้วยรหัสหรือชื่อ...',
        'opt_all_grades': 'ทุกระดับชั้น',
        'opt_all_rooms': 'ทุกห้อง',
        'opt_select_grade': 'เลือกระดับชั้น',
        'lbl_student_id': 'รหัสนักเรียน',
        'lbl_fullname': 'ชื่อ-นามสกุล',
        'lbl_grade': 'ระดับชั้น',
        'lbl_room': 'ห้อง',
        'ph_student_id': 'เช่น 69001',
        'ph_fullname': 'เช่น นายธนกฤต พุ่มเจริญ',
        'ph_room': 'เช่น 7',
        'empty_students': 'ไม่พบข้อมูลนักเรียน',
        'showing_label': 'แสดง',
        'of_total_label': 'จากทั้งหมด',
        'person_unit': 'คน',
        'page_label': 'หน้า',
        'of_page_label': 'จาก',

        // Import Students Excel
        'import_complete_title': 'นำเข้าข้อมูลสำเร็จ',
        'stat_imported': 'เพิ่มนักเรียนใหม่',
        'stat_updated': 'อัปเดตข้อมูลนักเรียนเดิม',
        'upload_excel_title': 'อัปโหลดไฟล์ Excel',
        'upload_excel_desc': 'อัปโหลดไฟล์ .xlsx ที่มีข้อมูลนักเรียน โดยระบบรองรับโครงสร้างดังนี้:',
        'upload_single_sheet': 'แผ่นงานเดียว: ประกอบด้วยคอลัมน์ student_id, full_name, grade, room',
        'upload_multi_sheet': 'หลายแผ่นงาน (แยกตามระดับชั้น): ตั้งชื่อแผ่นงานตามระดับชั้น (เช่น M.1, M.2, ...) ประกอบด้วยคอลัมน์ student_id, full_name, room',
        'drag_drop_text': 'ลากและวางไฟล์ Excel ของคุณที่นี่ หรือ',
        'errors_warnings': '⚠️ ข้อผิดพลาดและคำเตือน',
        'preview_header': 'ตรวจสอบข้อมูลก่อนนำเข้า',
        'badge_new': 'ใหม่',
        'badge_existing': 'อัปเดตข้อมูลเดิม',
        'showing_first_100': 'แสดง 100 รายการแรก จากทั้งหมด',
        'row_prefix': 'แถวที่',

        // Student History
        'breadcrumb_students': 'รายชื่อนักเรียน',
        'lbl_history_student_id': 'รหัสนักเรียน:',
        'lbl_history_grade': 'ระดับชั้น:',
        'lbl_history_room': 'ห้อง:',
        'method_qr': 'สแกน QR',
        'method_manual': 'โดยครูผู้สอน',
        'method_admin_manual': 'สแกน QR',
        'empty_history': 'ไม่พบประวัติการเข้าร่วมกิจกรรม',

        // Teacher Management
        'add_new_teacher_title': 'เพิ่มครูใหม่',
        'lbl_teacher_username': 'ชื่อผู้ใช้',
        'lbl_teacher_display_name': 'ชื่อที่แสดง',
        'lbl_teacher_password': 'รหัสผ่าน',
        'ph_teacher_username': 'เช่น teacher01',
        'ph_teacher_display_name': 'เช่น ครูสมชาย ใจดี',
        'ph_teacher_password': 'อย่างน้อย 6 ตัวอักษร',
        'modal_reset_pwd_title': 'รีเซ็ตรหัสผ่าน',
        'modal_reset_pwd_for': 'รีเซ็ตรหัสผ่านสำหรับ:',
        'lbl_new_password': 'รหัสผ่านใหม่',
        'empty_teachers': 'ยังไม่มีข้อมูลครูในระบบ',

        // Sessions Management
        'breadcrumb_activities': 'รายการกิจกรรม',
        'add_new_session_title': 'เพิ่มรอบกิจกรรมใหม่',
        'edit_session_title': 'แก้ไขรอบกิจกรรม',
        'lbl_session_name': 'ชื่อรอบกิจกรรม',
        'lbl_session_date': 'วันที่',
        'lbl_start_time': 'เวลาเริ่มต้น',
        'lbl_end_time': 'เวลาสิ้นสุด',
        'ph_session_name': 'เช่น ช่วงเช้า วันที่ 1',
        'checked_in_prefix': 'เช็คชื่อแล้ว',
        'empty_sessions': 'ยังไม่มีรอบกิจกรรมสำหรับกิจกรรมนี้ กรุณาเพิ่มรอบกิจกรรมจากแบบฟอร์มด้านขวา',

        // Attendance Management
        'opt_select_activity': 'เลือกกิจกรรม',
        'opt_select_session': 'เลือกรอบกิจกรรม',
        'found_records': 'พบข้อมูล',
        'records_unit': 'รายการ',
        'empty_attendance': 'ไม่พบรายการเช็คชื่อ',
        'btn_add_student': 'เพิ่มรายชื่อนักเรียน',
        'modal_correct_title': 'แก้ไขสถานะการเช็คชื่อ',
        'lbl_new_status': 'สถานะใหม่',
        'lbl_reason_required': 'เหตุผลในการแก้ไข',
        'ph_correction_reason': 'เช่น นักเรียนเข้าร่วมกิจกรรมแต่สแกน QR ไม่สำเร็จ',
        'opt_status_present': 'มา (Present)',
        'opt_status_manual': 'ปรับแก้โดยครู (Manual)',

        // Reports
        'export_excel_heading': 'ส่งออกข้อมูลการเช็คชื่อเป็นไฟล์ Excel',
        'export_excel_desc': 'เลือกกิจกรรมหรือรอบกิจกรรมที่ต้องการดาวน์โหลดรายงานสรุปการเข้าร่วมของนักเรียน',
        'lbl_activity_required': 'กิจกรรม',
        'opt_select_activity_report': 'เลือกกิจกรรม (สำหรับรายงานทั้งกิจกรรม)',
        'lbl_session_optional': 'รอบกิจกรรม (ไม่บังคับ — เลือกเมื่อต้องการเฉพาะรอบ)',
        'opt_all_sessions': 'ทุกรอบกิจกรรม',
        'lbl_filter_grade': 'กรองระดับชั้น',
        'lbl_filter_room': 'กรองห้อง',
        'ph_room_filter': 'เช่น 7',

        // Audit Logs
        'ph_filter_action': 'กรองตามการดำเนินการ...',
        'total_entries_label': 'ทั้งหมด',
        'lbl_reason': 'เหตุผล:',
        'lbl_prev': 'ค่าเดิม:',
        'lbl_new': 'ค่าใหม่:',
        'empty_audit': 'ไม่พบข้อมูลบันทึกประวัติระบบ',

        // Login
        'login_title': 'เข้าสู่ระบบ',
        'username': 'ชื่อผู้ใช้',
        'password': 'รหัสผ่าน',
        'lbl_username': 'ชื่อผู้ใช้',
        'lbl_password': 'รหัสผ่าน',
        'enter_username': 'กรอกชื่อผู้ใช้',
        'enter_password': 'กรอกรหัสผ่าน',
        'ph_enter_username': 'กรอกชื่อผู้ใช้',
        'ph_enter_password': 'กรอกรหัสผ่าน',
        'btn_sign_in': 'เข้าสู่ระบบ',
        'sign_in': 'เข้าสู่ระบบ',
        'toggle_password': 'แสดง/ซ่อนรหัสผ่าน',

        // Teacher Interface
        'teacher_welcome': 'ยินดีต้อนรับ,',
        'teacher_instruction': 'เลือกกิจกรรมและรอบกิจกรรมเพื่อเริ่มเปิดระบบเช็คชื่อ',
        'select_activity': '1. เลือกกิจกรรม',
        'select_session': '2. เลือกรอบกิจกรรม',
        'start_attendance': 'เริ่มการเช็คชื่อ',
        'checked_in': 'เช็คชื่อแล้ว',
        'not_checked_in': 'รายชื่อที่ยังไม่เช็คชื่อ',
        'end_attendance': 'สิ้นสุดการเช็คชื่อ',
        'qr_loading': 'กำลังโหลด QR Code...',
        'qr_refresh_prefix': 'QR Code จะเปลี่ยนใหม่ในอีก',
        'seconds': 'วินาที',
        'total_students_count': 'นักเรียนทั้งหมด',
        'present_count': 'มาเช็คชื่อแล้ว',
        'attendance_rate': 'อัตราการเข้าร่วม',
        'recent_checkin_title': 'นักเรียนที่เช็คชื่อล่าสุด',
        'empty_teacher_activities': 'ไม่มีกิจกรรมที่เปิดใช้งานในขณะนี้ กรุณาติดต่อผู้ดูแลระบบ',
        'empty_teacher_sessions': 'ไม่มีรอบกิจกรรมสำหรับกิจกรรมนี้',
        'title_not_checked_in': 'รายชื่อนักเรียนที่ยังไม่เช็คชื่อ',
        'back_to_attendance': '← กลับไปหน้าระบบเช็คชื่อ',
        'all_checked_in_success': 'นักเรียนทุกคนเช็คชื่อครบแล้ว! 🎉',
        'ph_search_not_checked': 'ค้นหาด้วยชื่อหรือรหัสนักเรียน...',
        'remaining_prefix': 'เหลืออีก',
        'not_checked_in_unit': 'คนที่ยังไม่เช็คชื่อ',
        'attendance_list': 'รายชื่อผู้เข้าร่วม',

        // Student Interface
        'checkin_title': 'ระบบเช็คชื่อเข้าร่วมกิจกรรม',
        'step1_title': 'ขั้นตอนที่ 1: เลือกระดับชั้นของคุณ',
        'step2_title': 'ขั้นตอนที่ 2: กรอกรหัสนักเรียน',
        'grade_label': 'ระดับชั้น:',
        'change': 'เปลี่ยน',
        'enter_student_id': 'กรอกรหัสนักเรียนของคุณ',
        'verify_student': 'ตรวจสอบข้อมูลนักเรียน',
        'step3_title': 'ขั้นตอนที่ 3: ตรวจสอบและยืนยันข้อมูลของคุณ',
        'name': 'ชื่อ-นามสกุล',
        'student_id': 'รหัสนักเรียน',
        'confirm_checkin': '✓ ยืนยันการเช็คชื่อ',
        'back': '← ย้อนกลับ',
        'checkin_success': 'บันทึกการเช็คชื่อสำเร็จแล้ว!',
        'session_expired_title': 'การเช็คชื่อหมดเวลา กรุณาสแกน QR Code ใหม่',
        'scan_qr_hint': 'กรุณาสแกน QR Code ที่แสดงบนหน้าจอของคุณครู',
        'scan_qr_prompt': 'กรุณาสแกน QR Code เพื่อเช็คชื่อ',
        'verifying': 'กำลังตรวจสอบ...',
        'saving': 'กำลังบันทึก...',
        'checkin_time_label': 'เวลาเช็คชื่อ: ',
        'err_conn': 'เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่',
        'err_enter_id': 'กรุณากรอกรหัสนักเรียน'
    },
    en: {
        // App / Brand
        'app_name': 'Student Attendance System',
        'app_subtitle': 'Activity Attendance Management System',
        'brand_logo': 'Check-ID',
        'attendance': 'Attendance',

        // Navigation Sidebar
        'nav_dashboard': 'Dashboard',
        'sec_students': 'Student Management',
        'nav_students': 'Students',
        'nav_import': 'Import Excel',
        'sec_teachers': 'Teacher Management',
        'nav_teachers': 'Teachers',
        'sec_activities': 'Activity Management',
        'nav_activities': 'Activities',
        'sec_attendance': 'Attendance',
        'nav_attendance': 'Manage Attendance',
        'sec_reports': 'Reports',
        'nav_reports': 'Export Excel',
        'sec_system': 'System',
        'nav_audit_logs': 'Audit Logs',
        'nav_logout': 'Logout',
        'role_admin': 'Administrator',
        'role_teacher': 'Teacher',

        // Page Titles & Headings
        'title_dashboard': 'Dashboard',
        'title_activities': 'Activity Management',
        'title_activity_new': 'Create New Activity',
        'title_activity_edit': 'Edit Activity',
        'title_students': 'Student Management',
        'title_student_new': 'Add New Student',
        'title_student_edit': 'Edit Student',
        'title_student_import': 'Import Students from Excel',
        'title_student_history': 'Attendance History',
        'title_teachers': 'Teacher Management',
        'title_sessions': 'Sessions',
        'title_attendance': 'Attendance Management',
        'title_reports': 'Reports & Export',
        'title_audit_logs': 'Audit Logs',

        // Dashboard Stat Cards & Sections
        'total_students': 'Total Students',
        'total_teachers': 'Teachers',
        'total_activities': 'Activities',
        'active_sessions': 'Active Sessions',
        'recent_activities': 'Recent Activities',
        'recent_audit_logs': 'Recent Audit Logs',
        'view_all': 'View All',
        'view_sessions': 'Sessions',
        'no_activities_yet': 'No activities yet',
        'create_one': 'Create New Activity',
        'create_first_activity': 'Create First Activity',
        'no_audit_logs_yet': 'No audit logs yet',
        'sys_user': 'System',

        // Filters & Status Badges
        'filter_all': 'All',
        'filter_draft': 'Draft',
        'filter_active': 'Active',
        'filter_scheduled': 'Scheduled',
        'filter_completed': 'Completed',
        'filter_cancelled': 'Cancelled',
        'status_active': 'Active',
        'status_disabled': 'Disabled',
        'status_completed': 'Completed',
        'status_draft': 'Draft',
        'status_scheduled': 'Scheduled',
        'status_cancelled': 'Cancelled',
        'status_present': 'Present',
        'status_late': 'Late',
        'status_leave': 'Leave',
        'status_absent': 'Absent',
        'status_manual': 'Manual',

        // Common Buttons & Actions
        'btn_create_activity': 'New Activity',
        'btn_create_first_activity': 'Create First Activity',
        'btn_sessions': 'Sessions',
        'btn_edit': 'Edit',
        'btn_delete': 'Delete',
        'btn_cancel': 'Cancel',
        'btn_cancel_edit': 'Cancel Edit',
        'btn_confirm_delete': 'Confirm Delete',
        'btn_save_changes': 'Save Changes',
        'btn_create': 'Create Activity',
        'btn_add_student': 'Add Student',
        'btn_import_excel': 'Import Excel',
        'btn_filter': 'Filter',
        'btn_view_all': 'View All',
        'btn_view_sessions': 'Sessions',
        'btn_add_teacher': 'Add Teacher',
        'btn_reset_password': 'Reset Password',
        'btn_enable': 'Enable',
        'btn_disable': 'Disable',
        'btn_save_password': 'Save New Password',
        'btn_correct_status': 'Correct Status',
        'btn_save_correction': 'Save Correction',
        'btn_export_excel': 'Export to Excel',
        'btn_choose_file': 'Choose File',
        'btn_upload_preview': 'Upload & Preview',
        'btn_confirm_import': 'Confirm Import',
        'btn_download_template': 'Download Template',
        'btn_view_students': 'View Students',
        'btn_prev': '← Previous',
        'btn_next': 'Next →',
        'btn_search': 'Search',
        'btn_history': 'Attendance History',

        // Activity Management
        'lbl_activity_name': 'Activity Name',
        'lbl_activity_desc': 'Description',
        'lbl_start_date': 'Start Date',
        'lbl_end_date': 'End Date',
        'lbl_status': 'Status',
        'lbl_eligible_grades': 'Eligible Grades (leave blank for all grades)',
        'ph_activity_name': 'e.g. Sports Day 2026',
        'ph_activity_desc': 'Brief description of the activity...',
        'all_grades_badge': '🎓 All Grades',
        'all_grades': 'All Grades',
        'all_rooms': 'All Rooms',
        'empty_activities': 'No activities in system',
        'modal_delete_activity_title': 'Confirm Activity Deletion',
        'modal_delete_activity_warning': 'This will permanently delete all associated sessions, attendance records, and QR tokens.',
        'modal_delete_activity_prefix': '⚠️ Are you sure you want to delete activity',
        'modal_delete_session_confirm': 'Are you sure you want to delete this session?',
        'confirm_disable_student': 'Are you sure you want to disable this student?',
        'confirm_import_prompt': 'Confirm importing student records',

        // Table Headers
        'th_activity_name': 'Activity Name',
        'th_status': 'Status',
        'th_date': 'Date',
        'th_actions': 'Actions',
        'th_student_id': 'Student ID',
        'th_fullname': 'Full Name',
        'th_grade': 'Grade',
        'th_room': 'Room',
        'th_username': 'Username',
        'th_display_name': 'Display Name',
        'th_created_date': 'Created Date',
        'th_timestamp': 'Timestamp',
        'th_user': 'User',
        'th_operation': 'Action',
        'th_target': 'Target',
        'th_details': 'Details',
        'th_checkin_time': 'Check-in Time',
        'th_checkin_method': 'Method',
        'th_index': '#',
        'th_sheet': 'Sheet',
        'th_session_round': 'Session',
        'th_activity': 'Activity',

        // Student Management
        'ph_search_student': 'Search by ID or name...',
        'opt_all_grades': 'All Grades',
        'opt_all_rooms': 'All Rooms',
        'opt_select_grade': 'Select Grade',
        'lbl_student_id': 'Student ID',
        'lbl_fullname': 'Full Name',
        'lbl_grade': 'Grade',
        'lbl_room': 'Room',
        'ph_student_id': 'e.g. 69001',
        'ph_fullname': 'e.g. John Doe',
        'ph_room': 'e.g. 7',
        'empty_students': 'No students found',
        'showing_label': 'Showing',
        'of_total_label': 'of',
        'person_unit': 'students',
        'page_label': 'Page',
        'of_page_label': 'of',

        // Import Students Excel
        'import_complete_title': 'Import Complete',
        'stat_imported': 'New Students Imported',
        'stat_updated': 'Existing Students Updated',
        'upload_excel_title': 'Upload Excel File',
        'upload_excel_desc': 'Upload a .xlsx file containing student data. The system supports:',
        'upload_single_sheet': 'Single sheet: columns student_id, full_name, grade, room',
        'upload_multi_sheet': 'Multiple sheets named by grade (e.g. M.1, M.2, ...): columns student_id, full_name, room',
        'drag_drop_text': 'Drag & drop your Excel file here, or',
        'errors_warnings': '⚠️ Errors & Warnings',
        'preview_header': 'Preview',
        'badge_new': 'new',
        'badge_existing': 'existing',
        'showing_first_100': 'Showing first 100 of',
        'row_prefix': 'Row',

        // Student History
        'breadcrumb_students': 'Students',
        'lbl_history_student_id': 'Student ID:',
        'lbl_history_grade': 'Grade:',
        'lbl_history_room': 'Room:',
        'method_qr': 'QR Scan',
        'method_manual': 'Manual',
        'method_admin_manual': 'QR Scan',
        'empty_history': 'No attendance records found',

        // Teacher Management
        'add_new_teacher_title': 'Add New Teacher',
        'lbl_teacher_username': 'Username',
        'lbl_teacher_display_name': 'Display Name',
        'lbl_teacher_password': 'Password',
        'ph_teacher_username': 'e.g. teacher01',
        'ph_teacher_display_name': 'e.g. Mr. Smith',
        'ph_teacher_password': 'Min 6 characters',
        'modal_reset_pwd_title': 'Reset Password',
        'modal_reset_pwd_for': 'Reset password for:',
        'lbl_new_password': 'New Password',
        'empty_teachers': 'No teachers found in system',

        // Sessions Management
        'breadcrumb_activities': 'Activities',
        'add_new_session_title': 'Add New Session',
        'edit_session_title': 'Edit Session',
        'lbl_session_name': 'Session Name',
        'lbl_session_date': 'Date',
        'lbl_start_time': 'Start Time',
        'lbl_end_time': 'End Time',
        'ph_session_name': 'e.g. Day 1 Morning',
        'checked_in_prefix': 'Checked in',
        'empty_sessions': 'No sessions yet. Add one using the form on the right.',

        // Attendance Management
        'opt_select_activity': 'Select Activity',
        'opt_select_session': 'Select Session',
        'found_records': 'Found',
        'records_unit': 'records',
        'empty_attendance': 'No attendance records found',
        'btn_add_student': 'Add Student',
        'modal_correct_title': 'Correct Attendance Status',
        'lbl_new_status': 'New Status',
        'lbl_reason_required': 'Reason (required)',
        'ph_correction_reason': 'e.g. Student attended but QR check-in failed',
        'opt_status_present': 'Present',
        'opt_status_manual': 'Manual',

        // Reports
        'export_excel_heading': 'Export Attendance to Excel',
        'export_excel_desc': 'Select activity and optional session to download attendance report.',
        'lbl_activity_required': 'Activity',
        'opt_select_activity_report': 'Select Activity (for full report)',
        'lbl_session_optional': 'Session (optional — for single session report)',
        'opt_all_sessions': 'All Sessions',
        'lbl_filter_grade': 'Grade Filter',
        'lbl_filter_room': 'Room Filter',
        'ph_room_filter': 'e.g. 7',

        // Audit Logs
        'ph_filter_action': 'Filter by action...',
        'total_entries_label': 'Total',
        'lbl_reason': 'Reason:',
        'lbl_prev': 'Previous:',
        'lbl_new': 'New:',
        'empty_audit': 'No audit logs found',

        // Login
        'login_title': 'Sign In',
        'username': 'Username',
        'password': 'Password',
        'lbl_username': 'Username',
        'lbl_password': 'Password',
        'enter_username': 'Enter username',
        'enter_password': 'Enter password',
        'ph_enter_username': 'Enter username',
        'ph_enter_password': 'Enter password',
        'btn_sign_in': 'Sign In',
        'sign_in': 'Sign In',
        'toggle_password': 'Show/hide password',

        // Teacher Interface
        'teacher_welcome': 'Welcome,',
        'teacher_instruction': 'Select an activity and session to start attendance check-in',
        'select_activity': '1. Select Activity',
        'select_session': '2. Select Session',
        'start_attendance': 'Start Attendance',
        'checked_in': 'Checked In',
        'not_checked_in': 'Not Checked In',
        'end_attendance': 'End Attendance',
        'qr_loading': 'Loading QR Code...',
        'qr_refresh_prefix': 'QR Code refreshes in',
        'seconds': 'seconds',
        'total_students_count': 'Total Students',
        'present_count': 'Present',
        'attendance_rate': 'Attendance Rate',
        'recent_checkin_title': 'Recent Check-in',
        'empty_teacher_activities': 'No active activities found. Please contact administrator.',
        'empty_teacher_sessions': 'No sessions found for this activity.',
        'title_not_checked_in': 'Students Not Checked In',
        'back_to_attendance': '← Back to Attendance',
        'all_checked_in_success': 'All students have checked in! 🎉',
        'ph_search_not_checked': 'Search by name or student ID...',
        'remaining_prefix': 'Remaining',
        'not_checked_in_unit': 'students not checked in',
        'attendance_list': 'Attendance List',

        // Student Interface
        'checkin_title': 'Attendance Check-In',
        'step1_title': 'Step 1: Select Your Grade',
        'step2_title': 'Step 2: Enter Student ID',
        'grade_label': 'Grade:',
        'change': 'Change',
        'enter_student_id': 'Enter your Student ID',
        'verify_student': 'Verify Student',
        'step3_title': 'Step 3: Confirm Your Information',
        'name': 'Full Name',
        'student_id': 'Student ID',
        'confirm_checkin': '✓ Confirm Attendance',
        'back': '← Go Back',
        'checkin_success': 'Attendance Recorded!',
        'session_expired_title': 'Check-in session expired. Please scan QR Code again.',
        'scan_qr_hint': 'Please scan the QR Code displayed on teacher\'s screen.',
        'scan_qr_prompt': 'Please scan QR Code to check in.',
        'verifying': 'Verifying...',
        'saving': 'Saving...',
        'checkin_time_label': 'Check-in Time: ',
        'err_conn': 'Connection error. Please try again.',
        'err_enter_id': 'Please enter your Student ID.'
    }
};

/** Build fast reverse-lookup map: text phrase -> translation key */
const PHRASE_TO_KEY = {};

function initPhraseMap() {
    for (const [key, val] of Object.entries(I18N_DICTIONARY.th)) {
        if (typeof val === 'string' && val.trim()) {
            PHRASE_TO_KEY[val.trim().toLowerCase()] = key;
        }
    }
    for (const [key, val] of Object.entries(I18N_DICTIONARY.en)) {
        if (typeof val === 'string' && val.trim()) {
            PHRASE_TO_KEY[val.trim().toLowerCase()] = key;
        }
    }
}
initPhraseMap();

let currentLang = localStorage.getItem('app_language') || 'th';

/**
 * Get translation string safely. Returns null if key is not found to prevent overwriting with raw key names.
 */
function t(key, fallback = null) {
    if (!key) return fallback;
    const dict = I18N_DICTIONARY[currentLang] || I18N_DICTIONARY['th'];
    if (dict && dict[key] !== undefined) {
        return dict[key];
    }
    const enDict = I18N_DICTIONARY['en'];
    if (enDict && enDict[key] !== undefined) {
        return enDict[key];
    }
    const thDict = I18N_DICTIONARY['th'];
    if (thDict && thDict[key] !== undefined) {
        return thDict[key];
    }
    return fallback !== null ? fallback : null;
}

/**
 * Change system language and re-translate DOM
 */
function setLanguage(lang) {
    if (lang !== 'th' && lang !== 'en') lang = 'th';
    currentLang = lang;
    try {
        localStorage.setItem('app_language', lang);
        document.cookie = 'app_language=' + lang + ';path=/;max-age=31536000';
    } catch (e) {}

    document.documentElement.lang = lang;
    if (lang === 'th') {
        document.body.classList.add('lang-th');
    } else {
        document.body.classList.remove('lang-th');
    }

    applyTranslations();
    updateSwitcherButtons();

    try {
        window.dispatchEvent(new CustomEvent('languagechange', { detail: { lang } }));
    } catch (e) {}
}

/**
 * Helper to translate regex patterns in dynamic strings
 */
function translateDynamicPatterns(text) {
    if (!text) return text;
    const isEn = currentLang === 'en';

    if (isEn) {
        // Room options: "ห้อง 1" -> "Room 1"
        text = text.replace(/^ห้อง\s*(\d+)$/i, 'Room $1');
        // "แสดง 25 จากทั้งหมด 100 คน"
        text = text.replace(/แสดง\s*(\d+)\s*จากทั้งหมด\s*(\d+)\s*คน/g, 'Showing $1 of $2 students');
        // "แสดง 100 รายการแรก จากทั้งหมด X รายการ"
        text = text.replace(/แสดง\s*(\d+)\s*รายการแรก\s*จากทั้งหมด\s*(\d+)\s*รายการ/g, 'Showing first $1 of $2 records');
        // "หน้า 1 จาก 5"
        text = text.replace(/หน้า\s*(\d+)\s*จาก\s*(\d+)/g, 'Page $1 of $2');
        // "พบข้อมูล 5 รายการ"
        text = text.replace(/พบข้อมูล\s*(\d+)\s*รายการ/g, 'Found $1 records');
        // "ทั้งหมด 5 รายการ"
        text = text.replace(/ทั้งหมด\s*(\d+)\s*รายการ/g, 'Total $1 records');
        // "เช็คชื่อแล้ว 10 คน"
        text = text.replace(/เช็คชื่อแล้ว\s*(\d+)\s*คน/g, 'Checked in $1 students');
        // "ใหม่ 10 คน"
        text = text.replace(/ใหม่\s*(\d+)\s*คน/g, 'New $1 students');
        // "อัปเดตข้อมูลเดิม 10 คน"
        text = text.replace(/อัปเดตข้อมูลเดิม\s*(\d+)\s*คน/g, 'Updated $1 students');
        // "เหลืออีก 5 คนที่ยังไม่เช็คชื่อ"
        text = text.replace(/เหลืออีก\s*(\d+)\s*คนที่ยังไม่เช็คชื่อ/g, '$1 students remaining');
        // Dropdown statuses:
        text = text.replace(/แบบร่าง\s*\(Draft\)/gi, 'Draft');
        text = text.replace(/กำหนดการแล้ว\s*\(Scheduled\)/gi, 'Scheduled');
        text = text.replace(/กำลังใช้งาน\s*\(Active\)/gi, 'Active');
        text = text.replace(/เสร็จสิ้น\s*\(Completed\)/gi, 'Completed');
        text = text.replace(/ยกเลิก\s*\(Cancelled\)/gi, 'Cancelled');
        text = text.replace(/มา\s*\(Present\)/gi, 'Present');
        text = text.replace(/ปรับแก้โดยครู\s*\(Manual\)/gi, 'Manual');
    } else {
        // "Room 1" -> "ห้อง 1"
        text = text.replace(/^Room\s*(\d+)$/i, 'ห้อง $1');
        // "Showing 25 of 100 students"
        text = text.replace(/Showing\s*(\d+)\s*of\s*(\d+)\s*students/g, 'แสดง $1 จากทั้งหมด $2 คน');
        // "Showing first 100 of X records"
        text = text.replace(/Showing\s*first\s*(\d+)\s*of\s*(\d+)\s*records/g, 'แสดง $1 รายการแรก จากทั้งหมด $2 รายการ');
        // "Page 1 of 5"
        text = text.replace(/Page\s*(\d+)\s*of\s*(\d+)/g, 'หน้า $1 จาก $2');
        // "Found 5 records"
        text = text.replace(/Found\s*(\d+)\s*records/g, 'พบข้อมูล $1 รายการ');
        // "Total 5 records"
        text = text.replace(/Total\s*(\d+)\s*records/g, 'ทั้งหมด $1 รายการ');
        // "Checked in 10 students"
        text = text.replace(/Checked\s*in\s*(\d+)\s*students/g, 'เช็คชื่อแล้ว $1 คน');
        // "New 10 students"
        text = text.replace(/New\s*(\d+)\s*students/g, 'ใหม่ $1 คน');
        // "Updated 10 students"
        text = text.replace(/Updated\s*(\d+)\s*students/g, 'อัปเดตข้อมูลเดิม $1 คน');
        // "$1 students remaining"
        text = text.replace(/(\d+)\s*students\s*remaining/g, 'เหลืออีก $1 คนที่ยังไม่เช็คชื่อ');
    }
    return text;
}

// Guard flag to prevent re-entrant translation calls (fixes infinite loop with MutationObserver)
let _isTranslating = false;
// Reference to the MutationObserver so we can disconnect/reconnect around DOM mutations
let _domObserver = null;

/**
 * Apply translations to DOM
 * Disconnects the MutationObserver before making changes, then reconnects after,
 * preventing the observer from triggering itself in an infinite loop.
 */
function applyTranslations() {
    if (_isTranslating) return;  // re-entrancy guard
    _isTranslating = true;

    // Pause the observer so our DOM writes don't retrigger it
    if (_domObserver) _domObserver.disconnect();

    try {
    // 1. Elements with explicit data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const translated = t(key);
        if (translated !== null && translated !== undefined) {
            el.textContent = translated;
        }
    });

    // 2. Elements with data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        const translated = t(key);
        if (translated !== null && translated !== undefined) {
            el.placeholder = translated;
        }
    });

    // 3. Elements with data-i18n-title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        const translated = t(key);
        if (translated !== null && translated !== undefined) {
            el.title = translated;
        }
    });

    // 4. Input placeholders without explicit data-i18n-placeholder
    document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(el => {
        if (el.hasAttribute('data-i18n-placeholder')) return;
        const ph = el.placeholder.trim();
        if (!el.__i18n_ph_key && PHRASE_TO_KEY[ph.toLowerCase()]) {
            el.__i18n_ph_key = PHRASE_TO_KEY[ph.toLowerCase()];
        }
        if (el.__i18n_ph_key) {
            const tr = t(el.__i18n_ph_key);
            if (tr) el.placeholder = tr;
        }
    });

    // 5. Select dropdown options: Handle dynamic rooms and statuses
    document.querySelectorAll('select option').forEach(opt => {
        if (opt.hasAttribute('data-i18n')) return;
        const txt = opt.textContent.trim();
        const translated = translateDynamicPatterns(txt);
        if (translated !== txt) {
            opt.textContent = translated;
        } else if (PHRASE_TO_KEY[txt.toLowerCase()]) {
            const tr = t(PHRASE_TO_KEY[txt.toLowerCase()]);
            if (tr) opt.textContent = tr;
        }
    });

    // 6. Dynamic pattern replacement across text containers
    document.querySelectorAll('.table-info, .page-info, .activity-meta, .session-meta, .empty-state, .preview-stats span, .header-meta, .breadcrumb, p, h1, h2, h3, h4, th, span, div, strong').forEach(el => {
        if (el.closest('.lang-switcher') || el.hasAttribute('data-i18n')) return;
        el.childNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent;
                const trimmed = text.trim();
                if (!trimmed) return;

                let key = node.__i18n_key;
                if (!key && PHRASE_TO_KEY[trimmed.toLowerCase()]) {
                    key = PHRASE_TO_KEY[trimmed.toLowerCase()];
                    node.__i18n_key = key;
                }

                if (key) {
                    const translated = t(key);
                    if (translated && translated !== trimmed) {
                        node.textContent = text.replace(trimmed, translated);
                    }
                } else {
                    const patternTranslated = translateDynamicPatterns(trimmed);
                    if (patternTranslated !== trimmed) {
                        node.textContent = text.replace(trimmed, patternTranslated);
                    }
                }
            }
        });
    });

    // 7. Translate document title
    const docTitle = document.title;
    if (currentLang === 'en') {
        document.title = docTitle
            .replace('จัดการกิจกรรม', 'Activity Management')
            .replace('จัดการข้อมูลนักเรียน', 'Student Management')
            .replace('จัดการข้อมูลครู', 'Teacher Management')
            .replace('จัดการการเช็คชื่อ', 'Attendance Management')
            .replace('รายงานและส่งออกข้อมูล', 'Reports & Export')
            .replace('บันทึกประวัติระบบ', 'Audit Logs')
            .replace('บันทึกประวัติการใช้งานระบบ', 'Audit Logs')
            .replace('แดชบอร์ดคุณครู — ระบบเช็คชื่อกิจกรรม', 'Teacher Dashboard — Attendance System')
            .replace('แดชบอร์ด', 'Dashboard')
            .replace('รอบกิจกรรม', 'Sessions')
            .replace('แก้ไขกิจกรรม', 'Edit Activity')
            .replace('สร้างกิจกรรมใหม่', 'New Activity')
            .replace('เข้าสู่ระบบ', 'Sign In')
            .replace('ผู้ดูแลระบบ', 'Admin')
            .replace('ระบบเช็คชื่อกิจกรรมนักเรียน', 'Student Attendance System')
            .replace('ระบบเช็คชื่อ', 'Attendance System')
            .replace('รายชื่อที่ยังไม่เช็คชื่อ', 'Not Checked In');
    } else {
        document.title = docTitle
            .replace('Activity Management', 'จัดการกิจกรรม')
            .replace('Student Management', 'จัดการข้อมูลนักเรียน')
            .replace('Teacher Management', 'จัดการข้อมูลครู')
            .replace('Attendance Management', 'จัดการการเช็คชื่อ')
            .replace('Reports & Export', 'รายงานและส่งออกข้อมูล')
            .replace('Audit Logs', 'บันทึกประวัติการใช้งานระบบ')
            .replace('Teacher Dashboard — Attendance System', 'แดชบอร์ดคุณครู — ระบบเช็คชื่อกิจกรรม')
            .replace('Dashboard', 'แดชบอร์ด')
            .replace('Sessions', 'รอบกิจกรรม')
            .replace('Edit Activity', 'แก้ไขกิจกรรม')
            .replace('New Activity', 'สร้างกิจกรรมใหม่')
            .replace('Sign In', 'เข้าสู่ระบบ')
            .replace('Admin', 'ผู้ดูแลระบบ')
            .replace('Student Attendance System', 'ระบบเช็คชื่อกิจกรรมนักเรียน')
            .replace('Attendance System', 'ระบบเช็คชื่อ')
            .replace('Not Checked In', 'รายชื่อที่ยังไม่เช็คชื่อ');
    }
    } finally {
        // Always restore observer and clear guard — even if translation threw
        _isTranslating = false;
        if (_domObserver) {
            _domObserver.observe(document.body, { childList: true, subtree: true });
        }
    }
}

/**
 * Update active state on language switcher buttons
 */
function updateSwitcherButtons() {
    document.querySelectorAll('.lang-switcher').forEach(switcher => {
        const thBtn = switcher.querySelector('[data-lang="th"]');
        const enBtn = switcher.querySelector('[data-lang="en"]');
        if (thBtn) thBtn.classList.toggle('active', currentLang === 'th');
        if (enBtn) enBtn.classList.toggle('active', currentLang === 'en');
    });
}

/**
 * Create language switcher HTML element
 */
function createLanguageSwitcherHTML(extraClass = '') {
    return `
        <div class="lang-switcher ${extraClass}">
            <button type="button" class="lang-btn ${currentLang === 'th' ? 'active' : ''}" data-lang="th" onclick="setLanguage('th')">
                <span class="flag">🇹🇭</span> TH
            </button>
            <button type="button" class="lang-btn ${currentLang === 'en' ? 'active' : ''}" data-lang="en" onclick="setLanguage('en')">
                <span class="flag">🇬🇧</span> EN
            </button>
        </div>
    `;
}

// Auto initialize on DOMContentLoaded or immediately if already loaded
function initI18n() {
    document.querySelectorAll('[data-lang-switcher]').forEach(holder => {
        holder.innerHTML = createLanguageSwitcherHTML(holder.getAttribute('data-lang-class') || '');
    });
    setLanguage(currentLang);

    // Debounce timer for observer — batches rapid DOM mutations into one translation pass
    let _observerTimer = null;

    // Watch for dynamic DOM changes (e.g. AJAX loaded sessions or checkin steps)
    // IMPORTANT: applyTranslations() disconnects this observer before writing to the DOM
    // and reconnects it afterwards, preventing the infinite loop that caused the freeze.
    _domObserver = new MutationObserver((mutations) => {
        // If we are currently inside applyTranslations(), ignore — the observer is
        // already disconnected there, but as a safety belt skip anyway.
        if (_isTranslating) return;

        let hasNewNodes = false;
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                // Ignore text-only nodes and lang-switcher injections
                if (node.nodeType !== Node.ELEMENT_NODE) continue;
                if (node.classList && node.classList.contains('lang-switcher')) continue;
                hasNewNodes = true;
                break;
            }
            if (hasNewNodes) break;
        }

        if (hasNewNodes && currentLang === 'en') {
            // Debounce: wait 50 ms before translating to batch multiple simultaneous DOM insertions
            clearTimeout(_observerTimer);
            _observerTimer = setTimeout(() => { applyTranslations(); }, 50);
        }
    });

    _domObserver.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initI18n);
} else {
    initI18n();
}
