// rechtliches.js - CSP-compliant event handlers
document.addEventListener('DOMContentLoaded', () => {
    // Handle logo fallback (replaces inline onerror)
    const logo = document.getElementById('nav-logo');
    if (logo) {
        logo.addEventListener('error', function () {
            this.src = 'https://via.placeholder.com/150x50?text=Server';
        });
    }
});
