const faqData = [
    // --- ALLGEMEIN ---
    {
        category: 'general',
        question: 'Was ist Server?',
        answer: 'Server ist ein Roleplay-Projekt, das auf realistischen Szenarien und einer starken Community basiert. Wir bieten verschiedene Fraktionen und Berufe an.'
    },
    {
        category: 'general',
        question: 'Wie trete ich dem Discord bei?',
        answer: 'Du findest den Einladungslink auf unserer Startseite. Stelle sicher, dass du die Regeln im #regelwerk Kanal liest und akzeptierst.'
    },
    {
        category: 'general',
        question: 'Wie lautet der Private Server Code?',
        answer: 'Den aktuellen Code findest du exklusiv auf unserem Discord-Server im Kanal #server-code. Er ändert sich regelmäßig.'
    },
    {
        category: 'general',
        question: 'Wann finden Server Restarts statt?',
        answer: 'Der Server startet automatisch alle 6 Stunden neu (00:00, 06:00, 12:00, 18:00 Uhr), um die Performance zu gewährleisten.'
    },
    
    // --- BEWERBUNGEN ---
    {
        category: 'application',
        question: 'Wie alt muss ich sein, um mich zu bewerben?',
        answer: 'Man muss 13 Jahre alt sein und geistige Reife zeigen.'
    },
    {
        category: 'application',
        question: 'Wie lange dauert die Bearbeitung meiner Bewerbung?',
        answer: 'In der Regel erhältst du innerhalb von 24 bis 48 Stunden eine Rückmeldung. Bitte sieh davon ab, Teammitglieder privat anzuschreiben.'
    },
    {
        category: 'application',
        question: 'Kann ich mich erneut bewerben, wenn ich abgelehnt wurde?',
        answer: 'Ja, allerdings gilt eine Sperrfrist von 2 Wochen, damit du Zeit hast, an deiner Bewerbung zu arbeiten.'
    },
    {
        category: 'application',
        question: 'Brauche ich ein funktionierendes Mikrofon?',
        answer: 'Ja, für alle Fraktionsberufe (Polizei, Rettungsdienst, etc.) ist ein funktionierendes Mikrofon für den Voice-Chat Pflicht.'
    },

    // --- ACCOUNT ---
    {
        category: 'account',
        question: 'Wie ändere ich meinen verknüpften Discord-Account?',
        answer: 'Bitte erstelle ein Ticket im Support-Bereich oder nutze das Kontaktformular hier, um eine Änderung zu beantragen.'
    },
    {
        category: 'account',
        question: 'Ich wurde gebannt. Was kann ich tun?',
        answer: 'Du kannst im Discord einen Entbannungsantrag stellen. Bitte warte mindestens 24 Stunden nach dem Bann und bleibe sachlich.'
    },

    // --- TECHNIK ---
    {
        category: 'technical',
        question: 'Die Seite lädt nicht richtig.',
        answer: 'Versuche deinen Browser-Cache zu leeren (STRG + F5). Wenn das Problem weiterhin besteht, deaktiviere AdBlocker oder versuche einen anderen Browser.'
    },
    {
        category: 'technical',
        question: 'Ich habe Texturfehler im Spiel (Pinke Texturen).',
        answer: 'Das liegt meist an Roblox. Versuche das Spiel neu zu starten oder deine Grafikeinstellungen kurzzeitig zu ändern, um einen Reload zu erzwingen.'
    },

    // --- GAMEPLAY (NEU) ---
    {
        category: 'gameplay',
        question: 'Wie lege ich den Sicherheitsgurt an?',
        answer: 'Drücke die Taste "B", um den Gurt anzulegen. Dies verhindert, dass du bei Unfällen aus dem Fahrzeug geschleudert wirst.'
    },
    {
        category: 'gameplay',
        question: 'Wie benutze ich den Funk?',
        answer: 'Der Funk wird über die Taste "Z" oder das UI-Icon am rechten Bildschirmrand bedient. Stelle sicher, dass du im richtigen Kanal bist.'
    },
    {
        category: 'gameplay',
        question: 'Darf ich als Zivilist Waffen tragen?',
        answer: 'Nur wenn du einen gültigen Waffenschein besitzt (im Rathaus erhältlich) und die Waffe legal erworben wurde. Langwaffen sind für Zivilisten meist verboten.'
    },
    {
        category: 'gameplay',
        question: 'Wie ergebe ich mich der Polizei?',
        answer: 'Nutze das Emote-Menü (.) und wähle "Hands Up" oder "Surrender". Folge danach strikt den Anweisungen der Beamten.'
    }
];

let currentCategory = 'general';

document.addEventListener('DOMContentLoaded', () => {
    renderFAQs();
});

function switchCategory(category) {
    // Update UI Buttons
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active', 'text-white', 'border-Server-red');
        btn.classList.add('text-gray-400');
    });
    
    const activeBtn = document.getElementById(`btn-${category}`);
    if(activeBtn) {
        activeBtn.classList.add('active', 'text-white');
        activeBtn.classList.remove('text-gray-400');
    }

    // Handle View Switching
    currentCategory = category;
    document.getElementById('help-search').value = ''; // Reset search
    renderFAQs();
}

function renderFAQs(filterText = '') {
    const container = document.getElementById('faq-container');
    container.innerHTML = '';

    const filtered = faqData.filter(item => {
        const matchesCategory = item.category === currentCategory;
        const matchesSearch = item.question.toLowerCase().includes(filterText.toLowerCase()) || 
                              item.answer.toLowerCase().includes(filterText.toLowerCase());
        
        // If searching, ignore category, otherwise respect category
        return filterText ? matchesSearch : matchesCategory;
    });

    if (filtered.length === 0) {
        container.innerHTML = `<div class="text-gray-500 text-center py-10 font-tech">Keine Ergebnisse gefunden.</div>`;
        return;
    }

    filtered.forEach(item => {
        const card = document.createElement('div');
        card.className = 'faq-card rounded-lg overflow-hidden cursor-pointer group';
        card.onclick = () => card.classList.toggle('open');

        card.innerHTML = `
            <div class="p-5 flex justify-between items-center">
                <h4 class="font-bold text-white group-hover:text-Server-red transition-colors">${item.question}</h4>
                <i class="fas fa-chevron-down text-gray-500 faq-icon"></i>
            </div>
            <div class="faq-answer px-5 text-gray-400 text-sm leading-relaxed border-t border-white/5 bg-black/20">
                <div class="py-4">${item.answer}</div>
            </div>
        `;
        container.appendChild(card);
    });
}

function filterFAQ() {
    const text = document.getElementById('help-search').value;
    renderFAQs(text);
}