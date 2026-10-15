/* ══════════════════════════════════════════════
   ADMIN JAVASCRIPT — Responsive Navigation & Controls
   ══════════════════════════════════════════════ */

/**
 * Toggle the admin sidebar drawer on mobile / tablet.
 * @param {boolean} [open] - Optional explicit state
 */
function toggleSidebar(open) {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar) return;

    const shouldOpen = (open !== undefined) ? !!open : !sidebar.classList.contains('open');
    if (shouldOpen) {
        sidebar.classList.add('open');
        if (backdrop) backdrop.classList.add('show');
        document.body.classList.add('sidebar-drawer-open');
    } else {
        sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('show');
        document.body.classList.remove('sidebar-drawer-open');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');

    // Close sidebar when clicking outside or clicking any nav item on mobile
    if (sidebar) {
        sidebar.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 1024) {
                    toggleSidebar(false);
                }
            });
        });
    }

    // Close on Escape key press
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (sidebar && sidebar.classList.contains('open')) {
                toggleSidebar(false);
            }
            document.querySelectorAll('.profile-dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });

    // Close profile dropdown when clicking outside
    document.addEventListener('click', (e) => {
        const wrapper = e.target.closest('.profile-dropdown-wrapper');
        if (!wrapper) {
            document.querySelectorAll('.profile-dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });

    // Close drawer if resized to desktop width
    window.addEventListener('resize', () => {
        if (window.innerWidth > 1024 && sidebar && sidebar.classList.contains('open')) {
            toggleSidebar(false);
        }
    });
});
