/**
 * Content Core UI JavaScript
 */

// Theme management
function getPreferredTheme() {
    const stored = localStorage.getItem('theme');
    if (stored) {
        return stored;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateThemeIcon(theme);
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const theme = getPreferredTheme();
    setTheme(theme);
});

// HTMX event handlers
document.addEventListener('htmx:beforeRequest', function(event) {
    // Disable form during submission
    const form = event.detail.elt;
    if (form.tagName === 'FORM') {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
        }
    }
});

document.addEventListener('htmx:afterRequest', function(event) {
    // Re-enable form after submission
    const form = event.detail.elt;
    if (form.tagName === 'FORM') {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }
});

document.addEventListener('htmx:responseError', function(event) {
    // Handle network errors
    const target = document.getElementById('result-container');
    if (target) {
        target.innerHTML = `
            <article class="error-card">
                <header>
                    <h3>Network Error</h3>
                </header>
                <p>Failed to connect to the server. Please check your connection and try again.</p>
            </article>
        `;
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + Enter to submit form
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        const form = document.getElementById('extract-form');
        if (form) {
            form.requestSubmit();
        }
    }
});
