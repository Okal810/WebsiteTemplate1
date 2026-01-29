function formatUptime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    // Pad with zeros
    const hh = h.toString().padStart(2, '0');
    const mm = m.toString().padStart(2, '0');
    const ss = s.toString().padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
}

async function fetchStatus() {
    const start = Date.now();
    try {
        const response = await fetch('/api/status');
        const end = Date.now();
        const ping = end - start;

        if (!response.ok) throw new Error('Netzwerkfehler');

        const data = await response.json();

        // Update UI Elements
        const hero = document.querySelector('.status-hero');
        const statusText = document.getElementById('server-status-text');
        const icon = document.getElementById('main-status-icon');

        // Status Logic
        hero.classList.remove('offline');
        hero.classList.add('online');
        statusText.textContent = 'SYSTEM ONLINE';
        // statusText style is handled by CSS now (gradient text)
        // statusText.style.color = '#00ff88'; 

        icon.innerHTML = '<i class="fas fa-check"></i>';

        // Stats
        document.getElementById('uptime').textContent = formatUptime(data.uptime);
        document.getElementById('version').textContent = 'v' + data.version;
        document.getElementById('ping').textContent = ping + ' ms';

        // New Stat: Application Count
        if (data.applications !== undefined) {
            document.getElementById('app-count').textContent = data.applications;
        }

    } catch (error) {
        // Offline State
        const hero = document.querySelector('.status-hero');
        const statusText = document.getElementById('server-status-text');
        const icon = document.getElementById('main-status-icon');

        hero.classList.remove('online');
        hero.classList.add('offline');
        statusText.textContent = 'SYSTEM OFFLINE';
        // statusText.style.color = '#00CED1';
        icon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';

        document.getElementById('ping').textContent = '---';
        console.error("Status fetch failed:", error);
    }
}

// Initial fetch
document.addEventListener('DOMContentLoaded', () => {
    fetchStatus();
    // Poll every 2 seconds
    setInterval(fetchStatus, 2000);
    // Fetch updates on load
    fetchUpdates();
});

async function fetchUpdates() {
    const container = document.getElementById('update-container');
    try {
        const response = await fetch('/api/updates');
        if (!response.ok) throw new Error('Update fetch failed');

        const updates = await response.json();

        if (updates.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">Keine Updates vorhanden.</div>';
            return;
        }

        container.innerHTML = updates.map(update => `
            <div class="update-entry" style="border-left: 3px solid ${update.color}; padding-left: 1rem; margin-bottom: 1rem;">
                <div class="update-meta" style="font-size: 0.8rem; color: #888; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.25rem;">
                    <span class="update-date">${update.date}</span> • 
                    <span class="update-tag" style="background: ${hexToRgba(update.color, 0.2)}; color: ${update.color}; padding: 2px 6px; border-radius: 4px; font-weight: bold;">${update.tag}</span>
                </div>
                <div class="update-content" style="color: #ddd; font-family: 'Inter', sans-serif;">
                    ${update.content}
                </div>
            </div>
        `).join('');

    } catch (e) {
        console.error(e);
        container.innerHTML = '<div style="text-align: center; color: #ff5555; padding: 20px;">Fehler beim Laden der Updates.</div>';
    }
}

function hexToRgba(hex, alpha) {
    let r = 0, g = 0, b = 0;
    if (hex.length === 4) {
        r = parseInt(hex[1] + hex[1], 16);
        g = parseInt(hex[2] + hex[2], 16);
        b = parseInt(hex[3] + hex[3], 16);
    } else if (hex.length === 7) {
        r = parseInt(hex[1] + hex[2], 16);
        g = parseInt(hex[3] + hex[4], 16);
        b = parseInt(hex[5] + hex[6], 16);
    }
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}