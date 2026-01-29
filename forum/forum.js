// Forum State
let allPosts = [];
let currentPostId = null;
let isModMode = false;
let isAdmin = false;
let currentPage = 1;
let currentSearch = '';
let lastUpdateTimestamp = 0;
let pendingPosts = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventDelegation();
    setupSearchDebounce();

    // Check admin first, THEN load posts
    checkAdminStatus().then(() => {
        loadPosts();
    });

    startPolling();
});

function setupEventDelegation() {
    const container = document.getElementById('posts-container');
    if (!container) return;

    container.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        const card = e.target.closest('.post-card');

        // Handle Post Click (Detail View)
        // If clicking button, dont open detail
        if (!btn && card) {
            const postId = card.dataset.id;
            if (postId) openPostDetail(postId);
            return;
        }

        if (!btn) return;
        e.stopPropagation(); // Avoid bubbling to card click

        const action = btn.dataset.action;
        const id = btn.dataset.id;
        const ip = btn.dataset.ip;

        if (action === 'ban') banUser(ip);
        if (action === 'delete-post') deletePost(id);
    });
}

function setupSearchDebounce() {
    let debounceTimer;
    const input = document.getElementById('search-input');
    if (!input) return;

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            loadPosts(1);
        }, 500);
    });
}

let refreshInterval = null;
function startPolling() {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(() => {
        pollPosts();
    }, 30000); // 30 Sekunden
}

async function pollPosts() {
    // Only poll on first page and without search
    if (currentPage !== 1 || currentSearch) return;

    try {
        const response = await fetch(`/api/forum/posts?since=${lastUpdateTimestamp}`);
        if (response.status === 304) return;

        const data = await response.json();
        const newPosts = data.posts || [];

        if (newPosts.length > 0) {
            console.log(`🔄 ${newPosts.length} neue Beiträge.`);

            // Filter duplicates if any
            const actuallyNew = newPosts.filter(np => !allPosts.some(p => p.id === np.id));

            if (actuallyNew.length > 0) {
                pendingPosts = [...actuallyNew, ...pendingPosts];

                // Update Timestamp
                const maxTime = Math.max(...actuallyNew.map(p => p.timestamp));
                if (maxTime > lastUpdateTimestamp) lastUpdateTimestamp = maxTime;

                // Show Notification
                const badge = document.getElementById('new-posts-badge');
                if (badge) {
                    badge.querySelector('span').textContent = `${pendingPosts.length} neue Beiträge - Klicken zum Laden`;
                    badge.classList.remove('hidden');
                }
            }
        }
    } catch (error) {
        console.error('Polling failed:', error);
    }
}

window.mergeNewPosts = function () {
    if (pendingPosts.length === 0) return;

    // Add to allPosts and re-render
    allPosts = [...pendingPosts, ...allPosts];

    // Update pagination meta approx
    const meta = { page: 1, total_pages: Math.ceil(allPosts.length / 20), has_next: true };
    renderPosts(allPosts, meta);

    pendingPosts = [];
    document.getElementById('new-posts-badge').classList.add('hidden');
    showToast('Beiträge aktualisiert', 'success');
};

// Check if user is admin
async function checkAdminStatus() {
    try {
        const response = await fetch('/api/forum/check-admin');
        const data = await response.json();
        isAdmin = data.is_admin || false;

        const modBtn = document.getElementById('mod-toggle-btn');
        if (modBtn) {
            modBtn.style.display = isAdmin ? 'inline-block' : 'none';
        }
    } catch (error) {
        console.error('Failed to check admin status:', error);
        isAdmin = false;
    }
}

// Load all posts
// Load posts with pagination
async function loadPosts(page = 1) {
    showLoading(true);
    try {
        currentSearch = document.getElementById('search-input').value.trim();
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            q: currentSearch
        });

        const response = await fetch(`/api/forum/posts?${params.toString()}`);
        const data = await response.json();

        allPosts = data.posts || [];
        const meta = data.meta || { page: 1, total_pages: 1 };

        // Reset Polling Timestamp on fresh load
        if (allPosts.length > 0) {
            lastUpdateTimestamp = Math.max(...allPosts.map(p => p.timestamp));
        }

        currentPage = meta.page;
        renderPosts(allPosts, meta);

    } catch (error) {
        console.error('Error loading posts:', error);
        showToast('Fehler beim Laden der Beiträge', 'error');
    } finally {
        showLoading(false);
    }
}

window.changePage = (page) => loadPosts(page);

// Render posts
function renderPosts(posts, meta) {
    const container = document.getElementById('posts-container');
    const emptyState = document.getElementById('empty-state');

    if (posts.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    let html = posts.map(post => `
        <div class="post-card rounded-xl p-6 animate-fade-in relative group" data-id="${post.id}">
            ${isModMode ? `
                <div class="absolute top-4 right-4 flex gap-2 z-10">
                    ${post.ip_hash ? `
                    <button data-action="ban" data-ip="${post.ip_hash}" 
                        class="w-8 h-8 bg-gray-800 hover:bg-red-900 hover:text-white rounded-full flex items-center justify-center text-gray-400 text-sm transition-colors border border-white/10" title="Benutzer sperren">
                        <i class="fas fa-ban pointer-events-none"></i>
                    </button>
                    ` : ''}
                    <button data-action="delete-post" data-id="${post.id}" 
                        class="w-8 h-8 bg-red-600 hover:bg-red-500 rounded-full flex items-center justify-center text-white text-sm transition-colors" title="Post löschen">
                        <i class="fas fa-trash pointer-events-none"></i>
                    </button>
                </div>
            ` : ''}
            <div class="cursor-pointer">
                <div class="flex justify-between items-start mb-3 ${isModMode ? 'pr-10' : ''}">
                    <h3 class="font-display text-lg font-bold text-white hover:text-Server-red transition-colors">
                        ${escapeHtml(post.title)}
                    </h3>
                    <span class="text-xs text-gray-500 font-tech whitespace-nowrap ml-4">
                        ${formatTime(post.timestamp)}
                    </span>
                </div>
                <p class="text-gray-400 text-sm mb-4 line-clamp-2">
                    ${escapeHtml(post.content.substring(0, 150))}${post.content.length > 150 ? '...' : ''}
                </p>
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <div class="w-8 h-8 rounded-full bg-Server-red/20 flex items-center justify-center">
                            <i class="fas fa-user text-Server-red text-xs"></i>
                        </div>
                        <span class="text-sm text-gray-300">${escapeHtml(post.author)}</span>
                    </div>
                    <div class="flex items-center gap-2 text-gray-500 text-sm">
                        <i class="fas fa-comments"></i>
                        <span>${post.comments ? post.comments.length : 0}</span>
                    </div>
                </div>
            </div>
        </div>
    `).join('');

    // Pagination Controls
    if (meta && meta.total_pages > 1) {
        html += `
            <div class="flex justify-center items-center gap-4 mt-8 pt-4 border-t border-white/10">
                <button onclick="window.changePage(${meta.page - 1})" ${!meta.has_prev ? 'disabled' : ''} 
                    class="px-4 py-2 bg-white/5 rounded hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-white text-sm font-tech">
                    <i class="fas fa-chevron-left mr-2"></i>Zurück
                </button>
                <span class="text-gray-400 font-tech text-sm">Seite ${meta.page} von ${meta.total_pages}</span>
                <button onclick="window.changePage(${meta.page + 1})" ${!meta.has_next ? 'disabled' : ''} 
                    class="px-4 py-2 bg-white/5 rounded hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-white text-sm font-tech">
                    Weiter<i class="fas fa-chevron-right ml-2"></i>
                </button>
            </div>
        `;
    }

    container.innerHTML = html;
}

// Remove old filterPosts as currentSearch is handled in loadPosts/setupSearchDebounce
// But keep name if anything external calls it (HTML onkeyup is removed)
function filterPosts() {
    loadPosts(1);
}

// Open new post modal
function openNewPostModal() {
    document.getElementById('new-post-modal').classList.remove('hidden');
    document.getElementById('post-title').focus();
}

// Close new post modal
function closeNewPostModal() {
    document.getElementById('new-post-modal').classList.add('hidden');
    document.getElementById('post-author').value = '';
    document.getElementById('post-title').value = '';
    document.getElementById('post-content').value = '';
    document.getElementById('post-error').classList.add('hidden');
}

// Submit new post
async function submitPost() {
    let author = document.getElementById('post-author').value;
    let title = document.getElementById('post-title').value;
    let content = document.getElementById('post-content').value;

    // Truncate IMMEDIATELY to prevent performance issues with large payloads
    author = author.substring(0, 50).trim() || 'Anonym';
    title = title.substring(0, 200).trim();
    content = content.substring(0, 5000).trim();

    const errorDiv = document.getElementById('post-error');
    const submitBtn = document.getElementById('submit-post-btn');

    // Client-side validation
    if (!title || title.length < 5) {
        showError(errorDiv, 'Titel muss mindestens 5 Zeichen haben.');
        return;
    }
    if (!content || content.length < 10) {
        showError(errorDiv, 'Beschreibung muss mindestens 10 Zeichen haben.');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Wird gesendet...';

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'DRP-Client'
        };
        if (csrfToken) headers['X-CSRF-Token'] = csrfToken;

        const response = await fetch('/api/forum/posts', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ author, title, content })
        });

        const data = await response.json();

        if (!response.ok) {
            showError(errorDiv, data.error || 'Ein Fehler ist aufgetreten.');
            return;
        }

        showToast('Beitrag erfolgreich erstellt!', 'success');
        closeNewPostModal();
        loadPosts();
    } catch (error) {
        showError(errorDiv, 'Verbindungsfehler. Bitte versuche es erneut.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Absenden';
    }
}

// Open post detail
async function openPostDetail(postId) {
    currentPostId = postId;
    const post = allPosts.find(p => p.id === postId);
    if (!post) return;

    document.getElementById('detail-title').textContent = post.title;
    document.getElementById('detail-author').textContent = post.author;
    document.getElementById('detail-time').textContent = formatTime(post.timestamp);
    document.getElementById('detail-content').textContent = post.content;

    renderComments(post.comments || []);
    document.getElementById('post-detail-modal').classList.remove('hidden');
}

// Backdrop Click for Modals
document.querySelectorAll('.fixed').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            if (modal.id === 'new-post-modal') closeNewPostModal();
            if (modal.id === 'post-detail-modal') closePostDetailModal();
        }
    });
});

function closePostDetailModal() {
    document.getElementById('post-detail-modal').classList.add('hidden');
    document.getElementById('comment-author').value = '';
    document.getElementById('comment-content').value = '';
    document.getElementById('comment-error').classList.add('hidden');
    currentPostId = null;
}

// Render comments
function renderComments(comments) {
    const container = document.getElementById('comments-container');

    if (comments.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-sm italic">Noch keine Antworten. Sei der Erste!</p>';
        return;
    }

    container.innerHTML = comments.map(comment => `
        <div class="comment-card py-3 relative group">
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                    <span class="font-bold text-white text-sm">${escapeHtml(comment.author)}</span>
                    <span class="text-gray-500 text-xs">${formatTime(comment.timestamp)}</span>
                </div>
                ${isModMode ? `
                    <div class="flex gap-1">
                        ${comment.ip_hash ? `
                        <button onclick="banUser('${comment.ip_hash}')" 
                            class="w-6 h-6 bg-gray-800 hover:bg-red-900 hover:text-white rounded flex items-center justify-center text-gray-400 text-xs transition-all border border-white/10" title="Benutzer sperren">
                            <i class="fas fa-ban"></i>
                        </button>
                        ` : ''}
                        <button onclick="deleteComment('${comment.id}')" 
                            class="w-6 h-6 bg-red-600 hover:bg-red-500 rounded flex items-center justify-center text-white text-xs transition-all" title="Kommentar löschen">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                ` : ''}
            </div>
            <p class="text-gray-300 text-sm">${escapeHtml(comment.content)}</p>
        </div>
    `).join('');
}

// Submit comment
async function submitComment() {
    if (!currentPostId) return;

    let author = document.getElementById('comment-author').value;
    let content = document.getElementById('comment-content').value;

    // Truncate IMMEDIATELY
    author = author.substring(0, 50).trim() || 'Anonym';
    content = content.substring(0, 2000).trim();

    const errorDiv = document.getElementById('comment-error');
    const submitBtn = document.getElementById('submit-comment-btn');

    if (!content || content.length < 3) {
        showError(errorDiv, 'Kommentar muss mindestens 3 Zeichen haben.');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>...';

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'DRP-Client'
        };
        if (csrfToken) headers['X-CSRF-Token'] = csrfToken;

        const response = await fetch(`/api/forum/posts/${currentPostId}/comments`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ author, content })
        });

        const data = await response.json();

        if (!response.ok) {
            showError(errorDiv, data.error || 'Ein Fehler ist aufgetreten.');
            return;
        }

        showToast('Antwort hinzugefügt!', 'success');
        document.getElementById('comment-author').value = '';
        document.getElementById('comment-content').value = '';

        // Update local state and re-render
        const post = allPosts.find(p => p.id === currentPostId);
        if (post) {
            if (!post.comments) post.comments = [];
            post.comments.push(data.comment);
            renderComments(post.comments);
        }
    } catch (error) {
        showError(errorDiv, 'Verbindungsfehler. Bitte versuche es erneut.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-reply mr-2"></i>Antworten';
    }
}

// Helper: Show error
function showError(errorDiv, message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Helper: Show loading
function showLoading(show) {
    document.getElementById('loading-state').classList.toggle('hidden', !show);
    document.getElementById('posts-container').classList.toggle('hidden', show);
}

// Helper: Show toast
function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Helper: Format timestamp
function formatTime(timestamp) {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'Gerade eben';
    if (diff < 3600) return `vor ${Math.floor(diff / 60)} Min`;
    if (diff < 86400) return `vor ${Math.floor(diff / 3600)} Std`;
    if (diff < 604800) return `vor ${Math.floor(diff / 86400)} Tagen`;

    return date.toLocaleDateString('de-DE');
}

// Helper: Escape HTML (Pattern 5)
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Moderation: Toggle Mod Mode
function toggleModMode() {
    // Check if user is admin
    if (!isAdmin) {
        showToast('Keine Berechtigung für Moderationsmodus', 'error');
        return;
    }

    isModMode = !isModMode;
    const btn = document.getElementById('mod-toggle-btn');
    if (isModMode) {
        btn.classList.add('bg-red-600', 'text-white');
        btn.classList.remove('bg-white/5', 'text-gray-400');
        showToast('Moderationsmodus aktiviert', 'success');
    } else {
        btn.classList.remove('bg-red-600', 'text-white');
        btn.classList.add('bg-white/5', 'text-gray-400');
        showToast('Moderationsmodus deaktiviert', 'success');
    }
    renderPosts(allPosts);
    // Re-render comments if modal is open
    if (currentPostId) {
        const post = allPosts.find(p => p.id === currentPostId);
        if (post) renderComments(post.comments || []);
    }
}

// Moderation: Delete Post
async function deletePost(postId) {
    if (!confirm('Möchtest du diesen Beitrag wirklich löschen?')) return;

    try {
        const response = await fetch(`/api/forum/posts/${postId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const data = await response.json();
            showToast(data.error || 'Fehler beim Löschen', 'error');
            return;
        }

        showToast('Beitrag gelöscht!', 'success');
        loadPosts();
    } catch (error) {
        showToast('Verbindungsfehler', 'error');
    }
}

// Moderation: Delete Comment
async function deleteComment(commentId) {
    if (!confirm('Möchtest du diesen Kommentar wirklich löschen?')) return;
    if (!currentPostId) return;

    try {
        const response = await fetch(`/api/forum/posts/${currentPostId}/comments/${commentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const data = await response.json();
            showToast(data.error || 'Fehler beim Löschen', 'error');
            return;
        }

        showToast('Kommentar gelöscht!', 'success');

        // Update local state
        const post = allPosts.find(p => p.id === currentPostId);
        if (post && post.comments) {
            post.comments = post.comments.filter(c => c.id !== commentId);
            renderComments(post.comments);
        }
    } catch (error) {
        showToast('Verbindungsfehler', 'error');
    }
}

// Moderation: Ban User
async function banUser(ipHash) {
    if (!ipHash) return;

    // Simple prompts for quick moderation
    const durationInput = prompt("Sperrdauer in Stunden (z.B. 24, 168=1Woche, leer=Permanent):", "24");
    if (durationInput === null) return; // Cancelled

    const reason = prompt("Grund für die Sperre:", "Verstoß gegen Forum-Regeln");
    if (!reason) return;

    try {
        const response = await fetch('/api/moderation/blacklist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ip_hash: ipHash,
                reason: reason,
                duration_hours: durationInput ? parseInt(durationInput) : null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showToast(data.error || 'Fehler beim Sperren', 'error');
            return;
        }

        showToast(`Benutzer erfolgreich gesperrt!`, 'success');

    } catch (error) {
        console.error("Ban Error:", error);
        showToast('Verbindungsfehler beim Sperren', 'error');
    }
}
