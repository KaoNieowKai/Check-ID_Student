(function() {
    const THEME_STORAGE_KEY = 'app_theme_pref';
    let currentTheme = localStorage.getItem(THEME_STORAGE_KEY) || 'system';

    // Apply theme immediately to prevent flash
    function applyTheme(theme) {
        let activeTheme = theme;
        if (theme === 'system') {
            activeTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        document.documentElement.setAttribute('data-theme', activeTheme);
    }

    applyTheme(currentTheme);

    // Watch for system theme changes if using system
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (currentTheme === 'system') {
            applyTheme('system');
            updateUI();
        }
    });

    window.setTheme = function(theme) {
        currentTheme = theme;
        localStorage.setItem(THEME_STORAGE_KEY, theme);
        applyTheme(theme);
        updateUI();
    };

    function getThemeLabel(themeKey) {
        // Fallback or dynamic based on language
        const isThai = (typeof window.t === 'function' ? window.t('role_admin') === 'ผู้ดูแลระบบ' : document.documentElement.lang === 'th') || document.querySelector('[data-lang-switcher] .lang-text')?.textContent.includes('ไทย');
        
        if (themeKey === 'light') {
            return isThai ? 'Light Mode<br><small style="font-size:11px;color:var(--text-muted);font-weight:normal">(ธีมสว่าง)</small>' : 'Light Mode';
        } else if (themeKey === 'dark') {
            return isThai ? 'Dark Mode<br><small style="font-size:11px;color:var(--text-muted);font-weight:normal">(ธีมมืด)</small>' : 'Dark Mode';
        } else {
            return isThai ? 'System<br><small style="font-size:11px;color:var(--text-muted);font-weight:normal">(ตามระบบ)</small>' : 'System';
        }
    }

    function updateUI() {
        const switchers = document.querySelectorAll('[data-theme-switcher]');
        if (!switchers.length) return;

        // Icons
        const sunIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
        const moonIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
        const systemIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`;

        let activeTheme = currentTheme;
        if (currentTheme === 'system') {
            activeTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        const currentIcon = activeTheme === 'dark' ? moonIcon : sunIcon;

        switchers.forEach(switcher => {
            // Give each switcher a unique ID for the dropdown
            const dropdownId = 'theme-dropdown-' + Math.random().toString(36).substr(2, 9);
            
            switcher.innerHTML = `
                <div class="theme-switcher-container" style="position: relative;">
                    <button class="theme-btn" onclick="document.getElementById('${dropdownId}').classList.toggle('show')">
                        ${currentIcon}
                    </button>
                    <div id="${dropdownId}" class="theme-dropdown">
                        <button class="theme-option ${currentTheme === 'light' ? 'selected' : ''}" onclick="setTheme('light')">
                            ${sunIcon} <span>${getThemeLabel('light')}</span>
                            ${currentTheme === 'light' ? '<svg class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
                        </button>
                        <button class="theme-option ${currentTheme === 'dark' ? 'selected' : ''}" onclick="setTheme('dark')">
                            ${moonIcon} <span>${getThemeLabel('dark')}</span>
                            ${currentTheme === 'dark' ? '<svg class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
                        </button>
                        <button class="theme-option ${currentTheme === 'system' ? 'selected' : ''}" onclick="setTheme('system')">
                            ${systemIcon} <span>${getThemeLabel('system')}</span>
                            ${currentTheme === 'system' ? '<svg class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
                        </button>
                    </div>
                </div>
            `;
        });
    }

    // close dropdown when clicking outside
    document.addEventListener('click', function(event) {
        document.querySelectorAll('.theme-dropdown.show').forEach(dropdown => {
            const container = dropdown.closest('.theme-switcher-container');
            if (container && !container.contains(event.target)) {
                dropdown.classList.remove('show');
            }
        });
    });

    // Initialize UI on load
    document.addEventListener('DOMContentLoaded', updateUI);
    // Expose for language switcher to call when language changes
    window.updateThemeUI = updateUI;
    
    // Patch window.setLang if it exists to also update theme UI (in case of label changes)
    const originalSetLang = window.setLang;
    if (typeof originalSetLang === 'function') {
        window.setLang = function(lang) {
            originalSetLang(lang);
            setTimeout(updateUI, 50); // slight delay to allow translation to apply
        };
    }
})();
