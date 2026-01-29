// ==================== SECURITY CORE ====================
const PanelSecurity = {
    isAuthenticated: false,

    async init() {
        try {
            // Check session via HttpOnly Cookie (Server handles validation)
            const res = await fetch('/api/admin/stats', { headers: { 'X-Requested-With': 'Server-Panel' } });
            this.isAuthenticated = res.ok;
            return res.ok;
        } catch (e) {
            console.error('Auth Check Failed', e);
            return false;
        }
    },

    async apiCall(url, options = {}) {
        const headers = { ...options.headers, 'X-Requested-With': 'Server-Panel' };

        try {
            const response = await fetch(url, { ...options, headers });
            if (response.status === 401) {
                this.isAuthenticated = false;
                window.location.reload(); // Force login screen
                throw new Error('Session expired');
            }
            return response;
        } catch (error) {
            showToast(error.message || 'Verbindungsfehler', 'error');
            throw error;
        }
    }
};

// ==================== LOGIN HANDLER ====================
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const btn = loginForm.querySelector('button[type="submit"]');

        if (btn) btn.disabled = true;

        try {
            const response = await fetch('/api/admin/session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                // Success
                window.location.reload();
            } else {
                const data = await response.json();
                showToast(data.error || 'Login fehlgeschlagen', 'error');
                if (btn) btn.disabled = false;
            }
        } catch (e) {
            console.error(e);
            showToast('Verbindungsfehler', 'error');
            if (btn) btn.disabled = false;
        }
    });
}

// ==================== LOGOUT FUNCTION ====================
window.logout = async function () {
    try {
        await fetch('/api/admin/logout', { method: 'POST' });
        window.location.reload();
    } catch (e) {
        window.location.reload();
    }
};
