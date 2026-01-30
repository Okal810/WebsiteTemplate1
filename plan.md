// Kein ModerationAPI-Objekt nötig!
async function blacklistIP(ipHash, reason, hours) {
    try {
        const res = await fetch('/api/moderation/blacklist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip_hash: ipHash, reason, duration_hours: hours })
        });
        
        if (res.status === 401) {
            window.location = '/login';
            return;
        }
        
        if (res.status === 403) {
            alert('Keine Berechtigung');
            return;
        }
        
        const data = await res.json();
        return data;
    } catch (err) {
        console.error(err);
    }
}
```

---

## **Security Layers (Defense in Depth):**
```
┌─────────────────────────────────────┐
│ 1. Frontend: Input-Validierung     │ ← UI/UX
├─────────────────────────────────────┤
│ 2. HTTPS: Verschlüsselung           │ ← Transport
├─────────────────────────────────────┤
│ 3. WAF: Angriffserkennung           │ ← Netzwerk
├─────────────────────────────────────┤
│ 4. Rate Limiting: Spam-Schutz       │ ← Server
├─────────────────────────────────────┤
│ 5. Authentication: Session-Check    │ ← Server
├─────────────────────────────────────┤
│ 6. Authorization: Role-Check        │ ← Server
├─────────────────────────────────────┤
│ 7. Input-Validierung: Sanitize      │ ← Server
├─────────────────────────────────────┤
│ 8. Business Logic: Aktion           │ ← Server
├─────────────────────────────────────┤
│ 9. Audit Log: Wer hat was gemacht?  │ ← Compliance
└─────────────────────────────────────┘


2. **Backend Optimierung (SQLAlchemy):**
   - Indizes auf `timestamp` und `status` setzen für schnelleres Polling.
   - Delta-Polling implementieren (nur neue Daten laden).
3. **Frontend Refactoring (Admin Panel):**
   - Aufsplittung in ES Modules (`auth.js`, `dashboard.js`, `moderation.js`).
   - Lazy Loading für Mod-Tools (werden nur geladen, wenn User = Admin).