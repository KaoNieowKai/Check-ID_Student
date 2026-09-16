/* Admin page JavaScript */
// Sidebar toggle for mobile
document.addEventListener('DOMContentLoaded', () => {
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        const sidebar = document.getElementById('sidebar');
        const toggle = document.querySelector('.sidebar-toggle');
        if (sidebar && sidebar.classList.contains('open') &&
            !sidebar.contains(e.target) && !toggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });
});
