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
