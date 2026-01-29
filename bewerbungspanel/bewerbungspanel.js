// ==================== CONFIG & STATE ====================
const STATE = {
    page: 1,
    limit: 20,
    filter: 'all',
    search: '',
    isLoading: false
};

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

// ==================== UTILS ====================
const Sanitizer = {
    escape(str) {
        if (!str) return '';
        return String(str).replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        })[m]);
    }
};

const showToast = (msg, type = 'success') => {
    const toast = document.getElementById('toast');
    if (!toast) return; // Fallback
    toast.textContent = msg;
    toast.className = `toast show ${type === 'error' ? 'bg-red-500' : 'bg-green-500'}`;
    setTimeout(() => toast.classList.remove('show'), 3000);
};

// ==================== DATA LAYER (Backend-Verlagerung) ====================
async function loadApplications() {
    if (STATE.isLoading) return;
    STATE.isLoading = true;

    const list = document.getElementById('app-list');
    list.innerHTML = '<div class="text-center py-10"><i class="fas fa-spinner fa-spin text-2xl"></i></div>';

    try {
        // OPTIMIERUNG: Query Params an Backend senden!
        const params = new URLSearchParams({
            page: STATE.page,
            limit: STATE.limit,
            status: STATE.filter === 'all' ? '' : STATE.filter,
            q: STATE.search
        });

        const response = await PanelSecurity.apiCall(`/api/applications?${params}`);
        const data = await response.json(); // Erwartet: { apps: [], meta: { total: 100, pages: 5 } }

        renderApplications(data.apps || []); // Fallback falls Array direkt kommt
        updatePagination(data.meta);

    } catch (e) {
        list.innerHTML = '<div class="text-red-500 text-center">Fehler beim Laden.</div>';
    } finally {
        STATE.isLoading = false;
    }
}

// ==================== RENDERING (Performance Optimiert) ====================
function renderApplications(apps) {
    const list = document.getElementById('app-list');

    if (!apps || apps.length === 0) {
        list.innerHTML = '<div class="text-gray-500 text-center py-10">Keine Daten gefunden.</div>';
        return;
    }

    // OPTIMIERUNG: Array.map + join ist viel schneller als innerHTML += in Loop
    const html = apps.map(app => {
        const safeUser = Sanitizer.escape(app.roblox_user);
        const safeId = Sanitizer.escape(app.id);
        const date = new Date(app.timestamp * 1000).toLocaleString(); // Timestamp handling

        let statusBadge = getStatusBadge(app.status);
        let typeColor = getTypeColor(app.applicationType);

        return `
            <div class="app-card bg-Server-card p-4 rounded border-l-4 ${typeColor.border} mb-3 border-white/5 relative group">
                <div class="flex justify-between items-start">
                    <div>
                        <span class="text-[10px] font-bold uppercase tracking-widest ${typeColor.text}">${Sanitizer.escape(app.applicationType)}</span>
                        ${statusBadge}
                        <h4 class="text-lg font-bold text-white mt-1">${safeUser}</h4>
                    </div>
                    <div class="text-right text-xs text-gray-500">
                        <div>${date}</div>
                        <div class="font-mono mt-1">ID: ${safeId}</div>
                    </div>
                </div>
                
                <div class="mt-4 flex gap-2">
                    <button onclick="viewApp('${safeId}')" class="flex-1 py-1.5 bg-white/5 hover:bg-white/10 rounded text-xs font-bold uppercase text-gray-300">
                        <i class="fas fa-eye"></i> Details
                    </button>
                    ${app.status === 'pending' ? `
                    <button onclick="quickAction('${safeId}', 'accepted')" class="px-3 bg-green-900/50 text-green-400 rounded hover:bg-green-800/50"><i class="fas fa-check"></i></button>
                    <button onclick="quickAction('${safeId}', 'rejected')" class="px-3 bg-red-900/50 text-red-400 rounded hover:bg-red-800/50"><i class="fas fa-times"></i></button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');

    list.innerHTML = html;
}

// Helpers für Rendering ausgelagert (sauberer Code)
function getStatusBadge(status) {
    const config = {
        pending: { class: 'text-gray-400 border-gray-600', text: 'Offen' },
        accepted: { class: 'text-green-400 border-green-500/30 bg-green-900/30', text: 'Angenommen' },
        rejected: { class: 'text-red-400 border-red-500/30 bg-red-900/30', text: 'Abgelehnt' }
    };
    const c = config[status] || config.pending;
    return `<span class="ml-2 px-1.5 py-0.5 text-[10px] font-bold uppercase rounded border ${c.class}">${c.text}</span>`;
}

function getTypeColor(type) {
    const colors = {
        staff: { text: 'text-purple-500', border: 'border-purple-500' },
        designer: { text: 'text-pink-500', border: 'border-pink-500' },
        event: { text: 'text-yellow-500', border: 'border-yellow-500' }
    };
    return colors[type] || { text: 'text-gray-400', border: 'border-gray-500' };
}

// ==================== SINGLE RESOURCE LOADING ====================
window.viewApp = async function (id) {
    // OPTIMIERUNG: Nicht alle Apps durchsuchen, sondern gezielt laden
    try {
        const response = await PanelSecurity.apiCall(`/api/applications/${id}`);
        if (!response.ok) throw new Error('Nicht gefunden');

        const app = await response.json();
        // Fallback or explicit call to renderDetailModal if it exists in global scope
        // Assuming renderDetailModal is defined elsewhere or I should define it.
        // The previous code might have had it. Let's assume the user knows it exists or I should check.
        // But for now I'll use the user provided code exactly as requested.
        // Wait, the user provided code says: renderDetailModal(app); // Separate Funktion für Modal-Rendering
        if (typeof renderDetailModal === 'function') {
            renderDetailModal(app);
        } else {
            console.error('renderDetailModal not defined');
            // Simplified fallback
            alert('Detail Modal missing in code. See console for data: ' + JSON.stringify(app));
        }

    } catch (e) {
        showToast('Fehler beim Laden der Details', 'error');
    }
};

// ==================== ACTIONS ====================
window.quickAction = async function (id, status) {
    try {
        await PanelSecurity.apiCall(`/api/applications/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        showToast(`Status auf ${status} gesetzt`);
        loadApplications(); // Liste neu laden
    } catch (e) {
        // Toast handled in apiCall
    }
};

// ==================== PAGINATION ====================
function updatePagination(meta) {
    const container = document.getElementById('pagination');
    if (!container || !meta) return;

    let html = '';
    if (meta.pages > 1) {
        // Prev
        html += `<button onclick="changePage(${STATE.page - 1})" class="px-3 py-1 rounded bg-white/5 hover:bg-white/10 ${STATE.page <= 1 ? 'opacity-50 cursor-not-allowed' : ''}" ${STATE.page <= 1 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i></button>`;

        // Page Info
        html += `<span class="px-3 text-sm text-gray-400">Seite ${meta.current_page} von ${meta.pages}</span>`;

        // Next
        html += `<button onclick="changePage(${STATE.page + 1})" class="px-3 py-1 rounded bg-white/5 hover:bg-white/10 ${STATE.page >= meta.pages ? 'opacity-50 cursor-not-allowed' : ''}" ${STATE.page >= meta.pages ? 'disabled' : ''}><i class="fas fa-chevron-right"></i></button>`;
    }
    container.innerHTML = html;
}

window.changePage = function (newPage) {
    if (newPage < 1) return;
    STATE.page = newPage;
    loadApplications();
}


// ==================== SEARCH & FILTER ====================
// Debounce Search: Verhindert API Spam während Tippen
let debounceTimer;
const searchInput = document.getElementById('search-input');
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            STATE.search = e.target.value.trim();
            STATE.page = 1; // Reset auf Seite 1 bei neuer Suche
            loadApplications();
        }, 400); // 400ms warten
    });
}

window.filterApps = function (filter) {
    STATE.filter = filter;
    STATE.page = 1;

    // UI Update
    document.querySelectorAll('.sidebar-link').forEach(el =>
        el.classList.toggle('active', el.dataset.filter === filter)
    );

    loadApplications();
};


// ==================== MODAL RENDERING ====================
function renderDetailModal(app) {
    const modal = document.getElementById('modal-detail');
    const title = document.getElementById('detail-title');
    const content = document.getElementById('detail-content');
    const actions = document.getElementById('detail-actions');

    if (!modal || !title || !content || !actions) return;

    // Title
    title.textContent = `Bewerbung von ${app.roblox_user}`;

    // Content
    const safeContent = (text) => Sanitizer.escape(text || 'Keine Angabe').replace(/\n/g, '<br>');

    // Combine special fields if they exist
    let extraFields = '';
    if (app.daily_time) extraFields += `<div class="mb-4"><h5 class="text-xs uppercase text-gray-500 mb-1">Tägliche Zeit</h5><p>${safeContent(app.daily_time)}</p></div>`;
    if (app.strengths) extraFields += `<div class="mb-4"><h5 class="text-xs uppercase text-gray-500 mb-1">Stärken</h5><p>${safeContent(app.strengths)}</p></div>`;
    if (app.weaknesses) extraFields += `<div class="mb-4"><h5 class="text-xs uppercase text-gray-500 mb-1">Schwächen</h5><p>${safeContent(app.weaknesses)}</p></div>`;

    content.innerHTML = `
        <div class="grid grid-cols-2 gap-4 mb-6">
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Discord</h5><p class="font-bold text-white">${Sanitizer.escape(app.discord_name)}</p></div>
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Alter</h5><p class="font-bold text-white">${Sanitizer.escape(app.age)}</p></div>
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Typ</h5><p class="text-Server-gold">${Sanitizer.escape(app.applicationType)}</p></div>
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Status</h5><p>${getStatusBadge(app.status)}</p></div>
        </div>
        
        <div class="mb-6">
            <h5 class="text-xs uppercase text-gray-500 mb-1">Über Mich</h5>
            <div class="bg-black/30 p-3 rounded text-sm text-gray-300">${safeContent(app.about_me)}</div>
        </div>

        ${app.motivation ? `
        <div class="mb-6">
            <h5 class="text-xs uppercase text-gray-500 mb-1">Motivation</h5>
            <div class="bg-black/30 p-3 rounded text-sm text-gray-300">${safeContent(app.motivation)}</div>
        </div>` : ''}

        ${extraFields}
    `;


    // Actions
    // Ban Button is always available
    const banBtn = `<button onclick="banUser('${app.id}', '${app.ip_hash}')" class="px-3 py-2 bg-red-950/30 hover:bg-red-900/50 text-red-500 border border-red-500/20 rounded transition-colors" title="IP SPERREN"><i class="fas fa-ban"></i></button>`;

    if (app.status === 'pending') {
        actions.innerHTML = `
            ${banBtn}
            <div class="flex-1"></div>
            <button onclick="quickAction('${app.id}', 'rejected'); closeViewModal();" class="px-4 py-2 bg-red-900/30 text-red-400 border border-red-500/30 rounded hover:bg-red-900/50 mr-2">Ablehnen</button>
            <button onclick="quickAction('${app.id}', 'accepted'); closeViewModal();" class="px-4 py-2 bg-green-900/30 text-green-400 border border-green-500/30 rounded hover:bg-green-900/50">Annehmen</button>
        `;
    } else {
        actions.innerHTML = `
            ${banBtn}
            <div class="flex-1"></div>
            <button onclick="closeViewModal()" class="px-4 py-2 bg-white/10 text-white rounded hover:bg-white/20">Schließen</button>
        `;
    }

    modal.classList.remove('hidden');
}

window.closeViewModal = function () {
    document.getElementById('modal-detail').classList.add('hidden');
};

window.banUser = async function (id, ipHash) {
    if (!confirm('ACHTUNG: Möchtest du diese IP-Adresse wirklich sperren? Der Nutzer kann dann keine Bewerbungen mehr senden.')) return;

    try {
        await PanelSecurity.apiCall('/api/admin/blacklist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip_hash: ipHash, reason: 'Bewerbungspanel Ban' })
        });

        // Optional: Reject app too
        await PanelSecurity.apiCall(`/api/applications/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'rejected' })
        });

        showToast('Nutzer wurde gesperrt.', 'error');
        closeViewModal();
        loadApplications();
    } catch (e) {
        console.error(e);
    }
};

// ==================== INIT ====================
(async () => {
    if (await PanelSecurity.init()) {
        const loginScreen = document.getElementById('login-screen');
        const dashboard = document.getElementById('dashboard');

        if (loginScreen) loginScreen.classList.add('hidden');
        if (dashboard) dashboard.classList.remove('hidden');
        loadApplications();
    }
})();