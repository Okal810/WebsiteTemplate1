// ==================== APPLICATIONS LOGIC ====================
// CSP-Compliant Version - Uses Event Delegation instead of inline onclick

// Explicitly attach to window to ensure global access for other scripts
window.loadApplications = async function () {
    if (STATE.isLoading) return;
    STATE.isLoading = true;

    const list = document.getElementById('app-list');
    list.innerHTML = '<div class="text-center py-10"><i class="fas fa-spinner fa-spin text-2xl"></i></div>';

    try {
        const params = new URLSearchParams({
            page: STATE.page,
            limit: STATE.limit,
            status: STATE.filter === 'all' ? '' : STATE.filter,
            q: STATE.search
        });

        const response = await PanelSecurity.apiCall(`/api/applications?${params}`);
        const data = await response.json();

        renderApplications(data.apps || []);
        updatePagination(data.meta);

    } catch (e) {
        list.innerHTML = '<div class="text-red-500 text-center">Fehler beim Laden.</div>';
    } finally {
        STATE.isLoading = false;
    }
}

function renderApplications(apps) {
    const list = document.getElementById('app-list');

    if (!apps || apps.length === 0) {
        list.innerHTML = '<div class="text-gray-500 text-center py-10">Keine Daten gefunden.</div>';
        return;
    }

    const html = apps.map(app => {
        const safeUser = Sanitizer.escape(app.roblox_user);
        const safeId = Sanitizer.escape(app.id);
        const date = new Date(app.timestamp * 1000).toLocaleString();

        let statusBadge = getStatusBadge(app.status);
        let typeColor = getTypeColor(app.applicationType);

        // CSP-Compliant: Use data-* attributes instead of inline onclick
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
                    <button data-action="view" data-id="${safeId}" class="flex-1 py-1.5 bg-white/5 hover:bg-white/10 rounded text-xs font-bold uppercase text-gray-300">
                        <i class="fas fa-eye pointer-events-none"></i> Details
                    </button>
                    ${app.status === 'pending' ? `
                    <button data-action="quick" data-id="${safeId}" data-status="accepted" class="px-3 bg-green-900/50 text-green-400 rounded hover:bg-green-800/50"><i class="fas fa-check pointer-events-none"></i></button>
                    <button data-action="quick" data-id="${safeId}" data-status="rejected" class="px-3 bg-red-900/50 text-red-400 rounded hover:bg-red-800/50"><i class="fas fa-times pointer-events-none"></i></button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');

    list.innerHTML = html;
}

window.viewApp = async function (id) {
    try {
        const response = await PanelSecurity.apiCall(`/api/applications/${id}`);
        if (!response.ok) throw new Error('Nicht gefunden');

        const app = await response.json();
        if (typeof renderDetailModal === 'function') {
            renderDetailModal(app);
        } else {
            console.error('renderDetailModal not defined');
            alert('Detail Modal missing in code.');
        }

    } catch (e) {
        showToast('Fehler beim Laden der Details', 'error');
    }
};

window.renderDetailModal = function (app) {
    const modal = document.getElementById('modal-detail');
    const title = document.getElementById('detail-title');
    const content = document.getElementById('detail-content');
    const actions = document.getElementById('detail-actions');

    if (!modal || !title || !content || !actions) return;

    // Store current app data for event delegation
    modal.dataset.appId = app.id;
    modal.dataset.ipHash = app.ip_hash || '';
    modal.dataset.isBanned = app.is_banned ? 'true' : 'false';
    modal.dataset.status = app.status;

    title.textContent = `Bewerbung von ${app.roblox_user}`;

    const safeContent = (text) => Sanitizer.escape(text || 'Keine Angabe').replace(/\n/g, '<br>');

    let extraFields = '';
    if (app.daily_time) extraFields += `<div class="mb-4"><h5 class="text-xs uppercase text-gray-500 mb-1">Tägliche Zeit</h5><p>${safeContent(app.daily_time)}</p></div>`;
    if (app.strengths) extraFields += `<div class="mb-4"><h5 class="text-xs uppercase text-gray-500 mb-1">Stärken</h5><p>${safeContent(app.strengths)}</p></div>`;
    if (app.weaknesses) extraFields += `<div class="mb-4"><h5 class="text-xs uppercase text-gray-500 mb-1">Schwächen</h5><p>${safeContent(app.weaknesses)}</p></div>`;

    // Warnings Logic
    const warningsList = (app.warnings || []).map(w => `
        <div class="text-xs bg-red-900/20 border border-red-500/20 p-2 rounded text-red-200 mb-2">
            <div class="flex justify-between opacity-50 mb-0.5 font-mono text-[10px]">
                <span>${new Date(w.timestamp * 1000).toLocaleString()}</span>
                <span>${Sanitizer.escape(w.moderator || 'Auto')}</span>
            </div>
            ${Sanitizer.escape(w.reason)}
        </div>
    `).join('');

    const warningsHtml = `
        <div class="mb-6 border-t border-white/10 pt-4">
            <h5 class="text-xs uppercase text-red-500 mb-2 font-bold flex items-center gap-2">
                <i class="fas fa-exclamation-triangle"></i> Verwarnungen (${app.warnings ? app.warnings.length : 0})
            </h5>
            ${warningsList ? `<div class="max-h-40 overflow-y-auto pr-2 custom-scrollbar">${warningsList}</div>` : '<p class="text-gray-600 text-xs italic">Keine Verwarnungen</p>'}
        </div>
    `;

    // Ban Badge
    const banBadge = app.is_banned ? '<span class="ml-2 bg-red-600 text-white text-[10px] px-2 py-0.5 rounded font-bold animate-pulse">BANNED</span>' : '';

    content.innerHTML = `
        <div class="grid grid-cols-2 gap-4 mb-6">
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Discord</h5><p class="font-bold text-white">${Sanitizer.escape(app.discord_name)}</p></div>
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Alter</h5><p class="font-bold text-white">${Sanitizer.escape(app.age)}</p></div>
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Typ</h5><p class="text-Server-gold">${Sanitizer.escape(app.applicationType)}</p></div>
            <div><h5 class="text-xs uppercase text-gray-500 mb-1">Status</h5><div class="flex items-center">${getStatusBadge(app.status)} ${banBadge}</div></div>
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
        ${warningsHtml}
    `;

    // CSP-Compliant Buttons - use data-action instead of onclick
    const warnBtn = `<button data-action="warn" class="px-3 py-2 bg-yellow-900/30 hover:bg-yellow-800/50 text-yellow-500 border border-yellow-500/20 rounded transition-colors mr-2" title="WARNEN"><i class="fas fa-exclamation-triangle"></i></button>`;

    const banActionBtn = app.is_banned
        ? `<button data-action="unban" class="px-3 py-2 bg-green-950/30 hover:bg-green-900/50 text-green-500 border border-green-500/20 rounded transition-colors" title="IP ENTSPERREN"><i class="fas fa-unlock"></i></button>`
        : `<button data-action="ban" class="px-3 py-2 bg-red-950/30 hover:bg-red-900/50 text-red-500 border border-red-500/20 rounded transition-colors" title="IP SPERREN"><i class="fas fa-ban"></i></button>`;

    if (app.status === 'pending') {
        actions.innerHTML = `
            <div class="flex items-center">
                ${warnBtn}
                ${banActionBtn}
            </div>
            <div class="flex-1"></div>
            <button data-action="reject-close" class="px-4 py-2 bg-red-900/30 text-red-400 border border-red-500/30 rounded hover:bg-red-900/50 mr-2">Ablehnen</button>
            <button data-action="accept-close" class="px-4 py-2 bg-green-900/30 text-green-400 border border-green-500/30 rounded hover:bg-green-900/50">Annehmen</button>
        `;
    } else {
        actions.innerHTML = `
            <div class="flex items-center">
                ${warnBtn}
                ${banActionBtn}
            </div>
            <div class="flex-1"></div>
            <button data-action="close-modal" class="px-4 py-2 bg-white/10 text-white rounded hover:bg-white/20">Schließen</button>
        `;
    }

    modal.classList.remove('hidden');
};

window.closeViewModal = function () {
    document.getElementById('modal-detail').classList.add('hidden');
};

function updatePagination(meta) {
    const container = document.getElementById('pagination');
    if (!container || !meta) return;

    let html = '';
    if (meta.pages > 1) {
        // CSP-Compliant: Use data-action instead of onclick
        html += `<button data-action="page" data-page="${STATE.page - 1}" class="px-3 py-1 rounded bg-white/5 hover:bg-white/10 ${STATE.page <= 1 ? 'opacity-50 cursor-not-allowed' : ''}" ${STATE.page <= 1 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i></button>`;
        html += `<span class="px-3 text-sm text-gray-400">Seite ${meta.current_page} von ${meta.pages}</span>`;
        html += `<button data-action="page" data-page="${STATE.page + 1}" class="px-3 py-1 rounded bg-white/5 hover:bg-white/10 ${STATE.page >= meta.pages ? 'opacity-50 cursor-not-allowed' : ''}" ${STATE.page >= meta.pages ? 'disabled' : ''}><i class="fas fa-chevron-right"></i></button>`;
    }
    container.innerHTML = html;
}

window.changePage = function (newPage) {
    if (newPage < 1) return;
    STATE.page = newPage;
    loadApplications();
}

window.filterApps = function (filter) {
    STATE.filter = filter;
    STATE.page = 1;

    document.querySelectorAll('.sidebar-link').forEach(el =>
        el.classList.toggle('active', el.dataset.filter === filter)
    );

    loadApplications();
};

// ==================== EVENT DELEGATION ====================
// CSP-Compliant: Single event listener handles all button clicks
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔧 [CSP] Event delegation setup starting...');

    const appList = document.getElementById('app-list');
    if (appList) {
        console.log('✅ [CSP] app-list found, attaching listener');
        appList.addEventListener('click', (e) => {
            console.log('🖱️ [CSP] Click in app-list:', e.target);
            const btn = e.target.closest('[data-action]');
            if (!btn) {
                console.log('⚠️ [CSP] No data-action button found');
                return;
            }

            const action = btn.dataset.action;
            const id = btn.dataset.id;
            const status = btn.dataset.status;
            console.log(`📌 [CSP] Action: ${action}, ID: ${id}, Status: ${status}`);

            switch (action) {
                case 'view':
                    console.log('👁️ [CSP] Calling viewApp...');
                    viewApp(id);
                    break;
                case 'quick':
                    console.log('⚡ [CSP] Calling quickAction...');
                    if (typeof quickAction === 'function') quickAction(id, status);
                    break;
            }
        });
    } else {
        console.error('❌ [CSP] app-list not found!');
    }

    // Delegate clicks for modal buttons
    document.getElementById('modal-detail')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const modal = document.getElementById('modal-detail');
        const appId = modal?.dataset.appId;
        const ipHash = modal?.dataset.ipHash;
        const action = btn.dataset.action;

        switch (action) {
            case 'warn':
                if (typeof warnUser === 'function') warnUser(appId, ipHash);
                break;
            case 'ban':
                if (typeof banUser === 'function') banUser(appId, ipHash);
                break;
            case 'unban':
                if (typeof unbanUser === 'function') unbanUser(appId, ipHash);
                break;
            case 'reject-close':
                if (typeof quickAction === 'function') quickAction(appId, 'rejected');
                closeViewModal();
                break;
            case 'accept-close':
                if (typeof quickAction === 'function') quickAction(appId, 'accepted');
                closeViewModal();
                break;
            case 'close-modal':
                closeViewModal();
                break;
        }
    });

    // Delegate clicks for pagination
    document.getElementById('pagination')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action="page"]');
        if (!btn || btn.disabled) return;

        const page = parseInt(btn.dataset.page, 10);
        if (!isNaN(page)) changePage(page);
    });
});
