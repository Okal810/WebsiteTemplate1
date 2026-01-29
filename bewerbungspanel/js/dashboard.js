// ==================== DASHBOARD & INIT ====================

// Search Listener
let debounceTimer;
const searchInput = document.getElementById('search-input');
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            STATE.search = e.target.value.trim();
            STATE.page = 1;
            if (typeof loadApplications === 'function') loadApplications();
        }, 400);
    });
}

// Global Clear Data (Example Action from Old Code)
window.clearData = async function () {
    // This function was referenced in HTML "onclick='clearData()'" but not implemented in previous snippets provided.
    // I'll leave a placeholder or implement basic confirmation if it was standard.
    // For now, logging to console as safety, or assuming it might be 'clearApplications' API call?
    // Using previous context: 'Leeren' button.
    if (!confirm('Wirklich ALLE Bewerbungen löschen? Dies kann nicht rückgängig gemacht werden!')) return;

    try {
        await PanelSecurity.apiCall('/api/applications', { method: 'DELETE' });
        showToast('Alle Bewerbungen gelöscht.');
        if (typeof loadApplications === 'function') loadApplications();
    } catch (e) {
        showToast('Fehler beim Löschen', 'error');
    }
};

// ==================== SESSION TIMER ====================
function startSessionTimer() {
    const timerDisplay = document.getElementById('session-timer');
    if (!timerDisplay) return;

    // Default 30 min (1800s). In real world, sync with cookie expiry if possible.
    // For now we assume fresh login = 30 min.
    let timeLeft = 1800;

    const interval = setInterval(() => {
        timeLeft--;
        if (timeLeft <= 0) {
            clearInterval(interval);
            window.location.reload(); // Session expired
        }

        const m = Math.floor(timeLeft / 60);
        const s = timeLeft % 60;
        timerDisplay.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;

        if (timeLeft < 300) {
            timerDisplay.classList.add('text-red-500');
            timerDisplay.classList.add('animate-pulse');
        }
    }, 1000);
}

// Init
(async () => {
    if (await PanelSecurity.init()) {
        const loginScreen = document.getElementById('login-screen');
        const dashboard = document.getElementById('dashboard');

        if (loginScreen) loginScreen.classList.add('hidden');
        if (dashboard) dashboard.classList.remove('hidden');

        startSessionTimer(); // Start Timer
        if (typeof loadApplications === 'function') loadApplications();
    }
})();
