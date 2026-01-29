(function () {
    'use strict';

    const CONFIG = {
        API_ENDPOINT: '/api/applications',
        RATE_LIMIT_MS: 60000,
        REQUEST_TIMEOUT: 10000,
        MAX_PAYLOAD_SIZE: 100 * 1024,
        MIN_TEXT_LENGTH: 30,
        MAX_TEXT_LENGTH: 2000
    };

    const PAGE_LOAD_TIME = Date.now();
    const PASTED_FIELDS = new Set();

    // ==================== UTILS ====================

    function sanitizeInput(value) {
        if (typeof value !== 'string') return '';
        return value.substring(0, CONFIG.MAX_TEXT_LENGTH + 100)
            .replace(/<[^>]*>|javascript:|on\w+\s*=|data:/gi, '')
            .trim()
            .substring(0, CONFIG.MAX_TEXT_LENGTH);
    }

    function showFieldError(input, message) {
        clearFieldError(input);
        input.classList.add('border-red-500', 'focus:border-red-500');
        input.parentNode.insertAdjacentHTML('beforeend',
            `<div class="field-error text-red-400 text-xs mt-1 flex items-center gap-1"><i class="fas fa-exclamation-circle"></i><span>${message}</span></div>`);
    }

    function clearFieldError(input) {
        input.parentNode.querySelector('.field-error')?.remove();
        input.classList.remove('border-red-500', 'focus:border-red-500');
    }

    function clearAllErrors(form) {
        form.querySelectorAll('.field-error').forEach(el => el.remove());
        form.querySelectorAll('.border-red-500').forEach(el => el.classList.remove('border-red-500', 'focus:border-red-500'));
    }

    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return alert(message);

        const isSuccess = type === 'success';
        const toast = document.createElement('div');
        toast.className = `bg-[#111] border-l-4 ${isSuccess ? 'border-green-500 text-green-400' : 'border-red-500 text-red-400'} text-white px-6 py-4 rounded shadow-2xl flex items-center gap-3 transform translate-y-10 opacity-0 transition-all duration-300 font-tech font-bold min-w-[300px]`;
        toast.innerHTML = `<i class="fas ${isSuccess ? 'fa-check-circle' : 'fa-exclamation-circle'} text-xl"></i><span>${message}</span>`;

        container.appendChild(toast);
        requestAnimationFrame(() => toast.classList.remove('translate-y-10', 'opacity-0'));
        setTimeout(() => {
            toast.classList.add('translate-y-10', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ==================== VALIDATION ====================

    function looksLikeSpam(text) {
        if (!text || text.length < 3) return false;
        const lowered = text.toLowerCase().trim();
        if (/(.)\1{4,}/.test(lowered)) return true; // Repeats
        if (lowered.length >= 4 && /^(asdf|qwer|zxcv|hjkl|asd|qwe){2,}$/i.test(lowered)) return true; // Keyboard smash
        if (/^test+$/i.test(lowered)) return true;
        if (/^\d+$/.test(lowered) && lowered.length < 4) return true; // Short numbers

        // Vowel ratio check for longer texts
        if (lowered.length >= 8) {
            const vowels = (lowered.match(/[aeiouäöü]/g) || []).length;
            const total = lowered.replace(/[^a-zäöü]/g, '').length;
            if (total > 0 && vowels / total < 0.15) return true;
        }
        return false;
    }

    const VALIDATORS = {
        age: (age) => {
            const num = parseInt(age, 10);
            return (isNaN(num) || num <= 0 || num >= 100)
                ? { valid: false, message: "Bitte gib ein gültiges Alter ein (1-99)." }
                : { valid: true };
        },
        roblox_user: (name) => {
            const clean = name.trim();
            if (clean.length < 3 || clean.length > 20) return { valid: false, message: "Roblox-Name muss 3-20 Zeichen haben." };
            if (!/^[a-zA-Z0-9_]+$/.test(clean)) return { valid: false, message: "Nur Buchstaben, Zahlen, Unterstriche." };
            return looksLikeSpam(clean) ? { valid: false, message: "Bitte gib einen echten Roblox-Namen ein." } : { valid: true };
        },
        discord_name: (name) => {
            const clean = name.trim();
            if (clean.length < 2 || clean.length > 32) return { valid: false, message: "Discord-Name muss 2-32 Zeichen haben." };
            return looksLikeSpam(clean) ? { valid: false, message: "Bitte gib einen echten Discord-Namen ein." } : { valid: true };
        },
        about_me: (text) => validateTextArea(text, 'Über mich', 30)
    };

    function validateTextArea(text, fieldName, minLength) {
        const clean = text.trim();
        if (clean.length < minLength) return { valid: false, message: `${fieldName} muss mindestens ${minLength} Zeichen haben.` };
        if (clean.length > CONFIG.MAX_TEXT_LENGTH) return { valid: false, message: `${fieldName} darf maximal ${CONFIG.MAX_TEXT_LENGTH} Zeichen haben.` };
        if (looksLikeSpam(clean)) return { valid: false, message: `Bitte schreibe eine ernsthafte Antwort für "${fieldName}".` };

        const words = clean.toLowerCase().split(/\s+/);
        if (words.length > 10 && (new Set(words).size / words.length < 0.3)) {
            return { valid: false, message: `${fieldName} enthält zu viele Wiederholungen.` };
        }
        return { valid: true };
    }

    function checkDuplicateValues(form) {
        const inputs = Array.from(form.querySelectorAll('input[type="text"], textarea'));
        const values = {};
        const duplicates = [];

        inputs.forEach(input => {
            const val = input.value.trim().toLowerCase();
            if (!val || val.length < 5) return;

            if (values[val]) {
                const existing = values[val];
                const isException = (input.name === 'roblox_user' && existing.name === 'discord_name') ||
                    (input.name === 'discord_name' && existing.name === 'roblox_user');

                if (!isException) {
                    if (!duplicates.includes(input)) duplicates.push(input);
                    if (!duplicates.includes(existing)) duplicates.push(existing);
                }
            } else {
                values[val] = input;
            }
        });
        return duplicates;
    }

    function validateForm(form) {
        clearAllErrors(form);
        const duplicates = checkDuplicateValues(form);
        if (duplicates.length > 0) {
            duplicates.forEach(input => showFieldError(input, "Bitte schreibe unterschiedliche Texte!"));
            duplicates[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            duplicates[0].focus();
            return false;
        }

        let firstError = null;
        for (const [name, validator] of Object.entries(VALIDATORS)) {
            const input = form.querySelector(`[name="${name}"]`);
            if (input) {
                const res = validator(input.value);
                if (!res.valid) {
                    showFieldError(input, res.message);
                    if (!firstError) firstError = input;
                }
            }
        }

        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstError.focus();
            return false;
        }
        return true;
    }

    // ==================== SUBMISSION ====================

    async function handleApplicationSubmit(event, type) {
        event.preventDefault();
        const rateLimitKey = `last_app_submit_${type}`;
        const lastSubmit = localStorage.getItem(rateLimitKey);

        if (lastSubmit && (Date.now() - parseInt(lastSubmit)) < CONFIG.RATE_LIMIT_MS) {
            const waitSec = Math.ceil((CONFIG.RATE_LIMIT_MS - (Date.now() - parseInt(lastSubmit))) / 1000);
            return showToast(`Bitte warte noch ${waitSec} Sekunden`, 'error');
        }

        const form = event.target;
        if (!validateForm(form)) return;

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;

        const data = {};
        new FormData(form).forEach((v, k) => data[k] = sanitizeInput(v));

        const payload = {
            applicationType: type,
            roblox_user: data.roblox_user,
            discord_name: data.discord_name,
            age: parseInt(data.age, 10),
            about_me: data.about_me,
            daily_time: data.daily_time,
            motivation: data.motivation,
            load_time: PAGE_LOAD_TIME,
            pasted_fields: Array.from(PASTED_FIELDS),
            website_url: form.querySelector('[name="website_url"]')?.value || ""
        };

        if (new Blob([JSON.stringify(payload)]).size > CONFIG.MAX_PAYLOAD_SIZE) {
            return showToast('Bewerbung zu groß. Bitte kürze deine Texte.', 'error');
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Sende...';

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        try {
            const headers = { 'Content-Type': 'application/json', 'X-Requested-With': 'DRP-Client' };
            if (csrfToken) headers['X-CSRF-Token'] = csrfToken;

            const response = await fetch(CONFIG.API_ENDPOINT, {
                method: 'POST', headers, body: JSON.stringify(payload), signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (response.ok) {
                localStorage.setItem(rateLimitKey, Date.now().toString());
                showToast('Bewerbung erfolgreich gesendet!', 'success');
                window.closeModal(type);
                form.reset();
                clearAllErrors(form);
            } else if (response.status === 429) {
                showToast('Zu viele Anfragen. Bitte später versuchen.', 'error');
            } else {
                const errorData = await response.json().catch(() => ({}));
                showToast(errorData.error || 'Fehler beim Senden.', 'error');
            }
        } catch (error) {
            clearTimeout(timeoutId);
            showToast(error.name === 'AbortError' ? 'Anfrage dauerte zu lange.' : 'Verbindungsfehler.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    }

    // ==================== INIT ====================

    window.openModal = (type) => {
        const m = document.getElementById(`modal-${type}`);
        if (m) { m.classList.remove('hidden'); document.body.style.overflow = 'hidden'; }
    };

    window.closeModal = (type) => {
        const m = document.getElementById(`modal-${type}`);
        if (m) { m.classList.add('hidden'); document.body.style.overflow = ''; }
    };

    document.addEventListener('DOMContentLoaded', () => {
        ['staff', 'designer', 'event'].forEach(type => {
            document.getElementById(`form-${type}`)?.addEventListener('submit', (e) => handleApplicationSubmit(e, type));
        });

        const loader = document.getElementById('loader');
        if (loader) loader.style.display = 'none';

        document.querySelectorAll('textarea, input').forEach(input => {
            input.addEventListener('paste', () => { if (input.name) PASTED_FIELDS.add(input.name); });
        });

        document.getElementById('mobile-menu-btn')?.addEventListener('click', () => {
            const m = document.getElementById('mobile-menu');
            m.classList.toggle('hidden'); m.classList.toggle('flex');
        });

        // Scroll & Reveal
        const nav = document.getElementById('navbar');
        window.addEventListener('scroll', () => {
            if (!nav) return;
            const scroll = window.scrollY > 50;
            nav.classList.toggle('bg-Server-black/95', scroll);
            nav.classList.toggle('shadow-2xl', scroll);
            nav.classList.toggle('py-2', scroll);
            nav.classList.toggle('py-4', !scroll);
            nav.classList.toggle('bg-Server-black/80', !scroll);
        });

        const observer = new IntersectionObserver(entries => {
            entries.forEach(e => e.isIntersecting && e.target.classList.add('active'));
        }, { threshold: 0.1 });
        document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
    });
})();
