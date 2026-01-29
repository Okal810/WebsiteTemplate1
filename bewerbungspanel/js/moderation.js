// ==================== MODERATION & ACTIONS ====================
window.quickAction = async function (id, status) {
    try {
        await PanelSecurity.apiCall(`/api/applications/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        showToast(`Status auf ${status} gesetzt`);
        if (typeof loadApplications === 'function') loadApplications();
    } catch (e) {
        // Toast handled in apiCall
    }
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
        if (typeof closeViewModal === 'function') closeViewModal();
        if (typeof loadApplications === 'function') loadApplications();
    } catch (e) {
        console.error(e);
    }
};

window.unbanUser = async function (id, ipHash) {
    if (!confirm('Möchtest du diese IP-Adresse wirklich entsperren?')) return;

    try {
        await PanelSecurity.apiCall(`/api/admin/blacklist/${ipHash}`, {
            method: 'DELETE'
        });
        showToast('Nutzer wurde entsperrt.');
        if (typeof viewApp === 'function') viewApp(id); // Reload modal details to update UI
        if (typeof loadApplications === 'function') loadApplications();
    } catch (e) {
        console.error(e);
    }
};

window.warnUser = async function (id, ipHash) {
    const reason = prompt("Bitte gib einen Grund für die Warnung ein:");
    if (!reason) return;

    try {
        const response = await PanelSecurity.apiCall('/api/admin/warn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip_hash: ipHash, reason: reason })
        });

        const data = await response.json();

        if (data.auto_blacklisted) {
            showToast('Warnung hinzugefügt. ACHTUNG: Nutzer wurde automatisch gesperrt (Limit erreicht).', 'error');
        } else {
            showToast('Warnung hinzugefügt.');
        }

        if (typeof viewApp === 'function') viewApp(id); // Reload modal details
    } catch (e) {
        console.error(e);
    }
};
