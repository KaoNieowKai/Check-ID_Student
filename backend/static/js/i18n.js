/**
 * i18n Translation Engine for Student Activity Attendance System
 * Supports: Thai (th) and English (en)
 */

const I18N_DICTIONARY = {
    th: {
        // App / Brand
        'app_name': 'ระบบเช็คชื่อกิจกรรมนักเรียน',
        'app_subtitle': 'Activity Attendance Management System',
        'attendance': 'การเช็คชื่อ',

        // Navigation
        'nav_dashboard': 'แดชบอร์ด',
        'nav_students': 'ข้อมูลนักเรียน',
        'nav_import': 'นำเข้า Excel',
        'nav_teachers': 'จัดการครู',
        'nav_activities': 'กิจกรรม',
        'nav_attendance': 'การเช็คชื่อ',
        'nav_reports': 'รายงานสรุป',
        'nav_audit_logs': 'ประวัติระบบ',
        'nav_logout': 'ออกจากระบบ',

        // Dashboard
        'total_students': 'นักเรียนทั้งหมด',
        'total_teachers': 'คุณครูทั้งหมด',
        'total_activities': 'กิจกรรมทั้งหมด',
        'active_sessions': 'รอบที่เปิดใช้งาน',
        'recent_activities': 'กิจกรรมล่าสุด',
        'recent_audit_logs': 'ประวัติระบบล่าสุด',
        'view_all': 'ดูทั้งหมด',
        'no_activities_yet': 'ยังไม่มีกิจกรรม',
        'create_one': 'สร้างกิจกรรมใหม่',
        'no_audit_logs_yet': 'ยังไม่มีบันทึกประวัติระบบ',

        // Common Buttons & Actions
        'add_student': 'เพิ่มนักเรียน',
        'add_teacher': 'เพิ่มคุณครู',
        'add_activity': 'สร้างกิจกรรมใหม่',
        'add_session': 'เพิ่มรอบกิจกรรม',
        'save': 'บันทึก',
        'save_changes': 'บันทึกการเปลี่ยนแปลง',
        'cancel': 'ยกเลิก',
        'confirm': 'ยืนยัน',
        'delete': 'ลบ',
        'edit': 'แก้ไข',
        'actions': 'จัดการ',
        'back': 'ย้อนกลับ',
        'search': 'ค้นหา...',
        'filter': 'กรองข้อมูล',
        'reset': 'รีเซ็ต',
        'reset_password': 'รีเซ็ตรหัสผ่าน',
        'export_excel': 'ส่งออกเป็น Excel',
        'import_file': 'นำเข้าไฟล์',
        'download_template': 'ดาวน์โหลดไฟล์ตัวอย่าง',
        'enable': 'เปิดใช้งาน',
        'disable': 'ปิดใช้งาน',
        'close': 'ปิด',
        'change': 'เปลี่ยน',

        // Statuses
        'status': 'สถานะ',
        'status_active': 'เปิดใช้งาน',
        'status_disabled': 'ปิดใช้งาน',
        'status_completed': 'เสร็จสิ้น',
        'status_draft': 'ร่าง',
        'status_cancelled': 'ยกเลิก',
        'status_present': 'มา',
        'status_late': 'สาย',
        'status_leave': 'ลา',
        'status_absent': 'ขาด',

        // Student Check-in
        'checkin_title': 'เช็คชื่อเข้าร่วมกิจกรรม',
        'step1_title': 'ขั้นตอนที่ 1: เลือกระดับชั้น',
        'step2_title': 'ขั้นตอนที่ 2: กรอกรหัสนักเรียน',
        'step3_title': 'ขั้นตอนที่ 3: ตรวจสอบและยืนยันข้อมูล',
        'grade_label': 'ระดับชั้น:',
        'student_id': 'รหัสนักเรียน',
        'enter_student_id': 'กรอกรหัสนักเรียนของคุณ',
        'verify_student': 'ตรวจสอบข้อมูลนักเรียน',
        'name': 'ชื่อ-นามสกุล',
        'confirm_checkin': 'ยืนยันการเช็คชื่อ',
        'checkin_success': 'เช็คชื่อสำเร็จแล้ว!',
        'you_are_checked_in': 'บันทึกการเข้าร่วมกิจกรรมเรียบร้อยแล้ว',
        'status_recorded': 'สถานะที่บันทึก',
        'time_recorded': 'เวลาที่บันทึก',
        'scan_new_qr': 'สแกนเช็คชื่อคนต่อไป',
        'qr_refresh_prefix': 'QR Code จะเปลี่ยนใหม่ในอีก',
        'seconds': 'วินาที',
        'qr_invalid': 'QR Code ไม่ถูกต้อง กรุณาสแกนใหม่จากหน้าจอของคุณครู',
        'qr_expired': 'QR Code นี้หมดอายุแล้ว กรุณาสแกนรหัสปัจจุบันจากหน้าจอครู',

        // Teacher Flow
        'teacher_welcome': 'ยินดีต้อนรับ,',
        'teacher_instruction': 'เลือกกิจกรรมและรอบเวลาเพื่อเปิดการเช็คชื่อ',
        'select_activity': '1. เลือกกิจกรรม',
        'select_session': '2. เลือกรอบเวลา',
        'start_attendance': 'เริ่มการเช็คชื่อ',
        'end_attendance': 'สิ้นสุดการเช็คชื่อ',
        'not_checked_in': 'รายชื่อที่ยังไม่มาเช็ค',
        'total_students_count': 'นักเรียนทั้งหมด',
        'present_count': 'มาเช็คชื่อแล้ว',
        'quick_checkin': 'เช็คชื่อด่วน (รายบุคคล)',
        'live_attendance': 'รายชื่อที่เช็คชื่อล่าสุด (เรียลไทม์)',
        'search_by_name_or_id': 'ค้นหาด้วยรหัส หรือชื่อนักเรียน...',

        // Login Page
        'login_title': 'เข้าสู่ระบบ',
        'username': 'ชื่อผู้ใช้งาน',
        'password': 'รหัสผ่าน',
        'new_password': 'รหัสผ่านใหม่',
        'display_name': 'ชื่อ-นามสกุล / ชื่อแสดง',
        'enter_username': 'กรอกชื่อผู้ใช้งาน',
        'enter_password': 'กรอกรหัสผ่าน',
        'sign_in': 'เข้าสู่ระบบ',
        'min_6_chars': 'อย่างน้อย 6 ตัวอักษร',

        // Table Headers & Fields
        'th_username': 'ชื่อผู้ใช้',
        'th_display_name': 'ชื่อที่แสดง',
        'th_status': 'สถานะ',
        'th_created': 'วันที่สร้าง',
        'th_actions': 'จัดการ',
        'th_student_id': 'รหัสนักเรียน',
        'th_name': 'ชื่อ-นามสกุล',
        'th_prefix': 'คำนำหน้า',
        'th_first_name': 'ชื่อ',
        'th_last_name': 'นามสกุล',
        'th_grade': 'ระดับชั้น',
        'th_room': 'ห้อง',
        'th_number': 'เลขที่',
        'th_activity': 'กิจกรรม',
        'th_session': 'รอบกิจกรรม',
        'th_date': 'วันที่',
        'th_start_time': 'เวลาเริ่ม',
        'th_end_time': 'เวลาสิ้นสุด',
        'th_time': 'เวลา',
        'th_method': 'วิธีเช็คชื่อ',
        'th_attendance_pct': 'เปอร์เซ็นต์การเข้า',
        'th_action': 'การกระทำ',
        'th_user': 'ผู้ใช้งาน',
        'th_details': 'รายละเอียด',

        // Teacher management
        'add_new_teacher': 'เพิ่มบัญชีคุณครูใหม่',
        'reset_password_for': 'รีเซ็ตรหัสผ่านสำหรับ:',
        'teacher_created_success': 'สร้างบัญชีครูเรียบร้อยแล้ว',
        'no_teachers_yet': 'ยังไม่มีรายชื่อคุณครูในระบบ',

        // Reports
        'all_activities': 'ทุกกิจกรรม',
        'all_grades': 'ทุกระดับชั้น',
        'all_rooms': 'ทุกห้อง',
        'summary_statistics': 'สถิติภาพรวม'
    },
    en: {
        'app_name': 'Student Activity Attendance',
        'app_subtitle': 'Activity Attendance Management System',
        'attendance': 'Attendance',

        'nav_dashboard': 'Dashboard',
        'nav_students': 'Students',
        'nav_import': 'Import Excel',
        'nav_teachers': 'Teachers',
        'nav_activities': 'Activities',
        'nav_attendance': 'Attendance',
        'nav_reports': 'Reports',
        'nav_audit_logs': 'Audit Logs',
        'nav_logout': 'Logout',

        'total_students': 'Total Students',
        'total_teachers': 'Teachers',
        'total_activities': 'Activities',
        'active_sessions': 'Active Sessions',
        'recent_activities': 'Recent Activities',
        'recent_audit_logs': 'Recent Audit Logs',
        'view_all': 'View All',
        'no_activities_yet': 'No activities yet.',
        'create_one': 'Create one',
        'no_audit_logs_yet': 'No audit logs yet.',

        'add_student': 'Add Student',
        'add_teacher': 'Add Teacher',
        'add_activity': 'New Activity',
        'add_session': 'Add Session',
        'save': 'Save',
        'save_changes': 'Save Changes',
        'cancel': 'Cancel',
        'confirm': 'Confirm',
        'delete': 'Delete',
        'edit': 'Edit',
        'actions': 'Actions',
        'back': 'Back',
        'search': 'Search...',
        'filter': 'Filter',
        'reset': 'Reset',
        'reset_password': 'Reset Password',
        'export_excel': 'Export to Excel',
        'import_file': 'Import File',
        'download_template': 'Download Template',
        'enable': 'Enable',
        'disable': 'Disable',
        'close': 'Close',
        'change': 'Change',

        'status': 'Status',
        'status_active': 'Active',
        'status_disabled': 'Disabled',
        'status_completed': 'Completed',
        'status_draft': 'Draft',
        'status_cancelled': 'Cancelled',
        'status_present': 'Present',
        'status_late': 'Late',
        'status_leave': 'Leave',
        'status_absent': 'Absent',

        'checkin_title': 'Attendance Check-In',
        'step1_title': 'Step 1: Select Your Grade',
        'step2_title': 'Step 2: Enter Student ID',
        'step3_title': 'Step 3: Confirm Your Information',
        'grade_label': 'Grade:',
        'student_id': 'Student ID',
        'enter_student_id': 'Enter your Student ID',
        'verify_student': 'Verify Student',
        'name': 'Name',
        'confirm_checkin': 'Confirm Check-In',
        'checkin_success': 'Check-In Successful!',
        'you_are_checked_in': 'Your attendance has been recorded.',
        'status_recorded': 'Recorded Status',
        'time_recorded': 'Recorded Time',
        'scan_new_qr': 'Scan For Next Student',
        'qr_refresh_prefix': 'QR Code refreshes in',
        'seconds': 'seconds',
        'qr_invalid': 'Invalid QR Code. Please scan the current QR Code.',
        'qr_expired': 'This QR Code has expired. Please scan the current QR Code.',

        'teacher_welcome': 'Welcome,',
        'teacher_instruction': 'Select an activity and session to start attendance',
        'select_activity': '1. Select Activity',
        'select_session': '2. Select Session',
        'start_attendance': 'Start Attendance',
        'end_attendance': 'End Attendance',
        'not_checked_in': 'Not Checked In',
        'total_students_count': 'Total Students',
        'present_count': 'Present',
        'quick_checkin': 'Quick Check-in',
        'live_attendance': 'Live Attendance',
        'search_by_name_or_id': 'Search by student ID or name...',

        'login_title': 'Sign In',
        'username': 'Username',
        'password': 'Password',
        'new_password': 'New Password',
        'display_name': 'Display Name',
        'enter_username': 'Enter username',
        'enter_password': 'Enter password',
        'sign_in': 'Sign In',
        'min_6_chars': 'Min 6 characters',

        'th_username': 'Username',
        'th_display_name': 'Display Name',
        'th_status': 'Status',
        'th_created': 'Created',
        'th_actions': 'Actions',
        'th_student_id': 'Student ID',
        'th_name': 'Name',
        'th_prefix': 'Prefix',
        'th_first_name': 'First Name',
        'th_last_name': 'Last Name',
        'th_grade': 'Grade',
        'th_room': 'Room',
        'th_number': 'Number',
        'th_activity': 'Activity',
        'th_session': 'Session',
        'th_date': 'Date',
        'th_start_time': 'Start Time',
        'th_end_time': 'End Time',
        'th_time': 'Time',
        'th_method': 'Method',
        'th_attendance_pct': 'Attendance %',
        'th_action': 'Action',
        'th_user': 'User',
        'th_details': 'Details',

        'add_new_teacher': 'Add New Teacher',
        'reset_password_for': 'Reset password for:',
        'teacher_created_success': 'Teacher created successfully',
        'no_teachers_yet': 'No teachers yet.',

        'all_activities': 'All Activities',
        'all_grades': 'All Grades',
        'all_rooms': 'All Rooms',
        'summary_statistics': 'Summary Statistics'
    }
};

/** Exact phrase fallback map for plain text nodes without data-i18n */
const EXACT_PHRASE_MAP = {
    'Dashboard': 'nav_dashboard',
    'Students': 'nav_students',
    'Import Excel': 'nav_import',
    'Teachers': 'nav_teachers',
    'Teacher Management': 'nav_teachers',
    'Activities': 'nav_activities',
    'Attendance': 'nav_attendance',
    'Reports': 'nav_reports',
    'Audit Logs': 'nav_audit_logs',
    'Logout': 'nav_logout',
    'Total Students': 'total_students',
    'Active Sessions': 'active_sessions',
    'Recent Activities': 'recent_activities',
    'Recent Audit Logs': 'recent_audit_logs',
    'View All': 'view_all',
    'Add Student': 'add_student',
    'Add Teacher': 'add_teacher',
    'Add New Teacher': 'add_new_teacher',
    'New Activity': 'add_activity',
    'Add Session': 'add_session',
    'Save': 'save',
    'Cancel': 'cancel',
    'Confirm': 'confirm',
    'Delete': 'delete',
    'Edit': 'edit',
    'Actions': 'actions',
    'Reset Password': 'reset_password',
    'Export to Excel': 'export_excel',
    'Status': 'status',
    'Active': 'status_active',
    'Disabled': 'status_disabled',
    'Completed': 'status_completed',
    'Draft': 'status_draft',
    'Cancelled': 'status_cancelled',
    'Present': 'status_present',
    'Late': 'status_late',
    'Leave': 'status_leave',
    'Absent': 'status_absent',
    'Username': 'username',
    'Display Name': 'display_name',
    'Password': 'password',
    'New Password': 'new_password',
    'Created': 'th_created',
    'Student ID': 'student_id',
    'Name': 'name',
    'Grade': 'th_grade',
    'Room': 'th_room',
    'Number': 'th_number',
    'Sign In': 'sign_in',
    'Start Attendance': 'start_attendance',
    'End Attendance': 'end_attendance',
    'Not Checked In': 'not_checked_in',
    '1. Select Activity': 'select_activity',
    '2. Select Session': 'select_session',
    'Step 1: Select Your Grade': 'step1_title',
    'Step 2: Enter Student ID': 'step2_title',
    'Step 3: Confirm Your Information': 'step3_title',
    'Verify Student': 'verify_student',
    'Confirm Check-In': 'confirm_checkin',
    'Check-In Successful!': 'checkin_success',
    'Change': 'change'
};

// Current language: Default to Thai ('th') or user saved preference
let currentLang = localStorage.getItem('app_language') || 'th';

/**
 * Get translation string
 */
function t(key, fallback = null) {
    const dict = I18N_DICTIONARY[currentLang] || I18N_DICTIONARY['th'];
    if (dict && dict[key] !== undefined) {
        return dict[key];
    }
    const enDict = I18N_DICTIONARY['en'];
    if (enDict && enDict[key] !== undefined) {
        return enDict[key];
    }
    return fallback !== null ? fallback : key;
}

/**
 * Change system language and re-translate DOM
 */
function setLanguage(lang) {
    if (lang !== 'th' && lang !== 'en') lang = 'th';
    currentLang = lang;
    localStorage.setItem('app_language', lang);
    document.documentElement.lang = lang;
    
    if (lang === 'th') {
        document.body.classList.add('lang-th');
    } else {
        document.body.classList.remove('lang-th');
    }

    applyTranslations();
    updateSwitcherButtons();
}

/**
 * Apply translations to DOM
 */
function applyTranslations() {
    // 1. Elements with data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const translated = t(key);
        if (translated) {
            el.textContent = translated;
        }
    });

    // 2. Elements with data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        const translated = t(key);
        if (translated) {
            el.placeholder = translated;
        }
    });

    // 3. Elements with data-i18n-title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        const translated = t(key);
        if (translated) {
            el.title = translated;
        }
    });

    // 4. Automatic exact phrase matching for standard elements (buttons, th, labels, status-badges)
    const candidates = document.querySelectorAll('th, label, button, .btn, .status-badge, .stat-label, .nav-item, h1, h2, h3');
    candidates.forEach(el => {
        // Skip if already handled by data-i18n or has complex children (except svg)
        if (el.hasAttribute('data-i18n') || el.classList.contains('lang-btn')) return;

        // If element has text node
        const childNodes = Array.from(el.childNodes);
        childNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent.trim();
                if (!text) return;
                
                // Store original English text if not already stored
                if (!node.__origText) {
                    node.__origText = text;
                }

                const orig = node.__origText;
                if (EXACT_PHRASE_MAP[orig]) {
                    const key = EXACT_PHRASE_MAP[orig];
                    node.textContent = node.textContent.replace(text, t(key, orig));
                }
            }
        });
    });
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

// Auto initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    // Mount language switchers in placeholders if present
    document.querySelectorAll('[data-lang-switcher]').forEach(holder => {
        holder.innerHTML = createLanguageSwitcherHTML(holder.getAttribute('data-lang-class') || '');
    });

    setLanguage(currentLang);
});
