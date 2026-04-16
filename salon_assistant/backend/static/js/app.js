const API = '';
let currentSalonId = null;
let currentUser = null;

// ─── Auth ─────────────────────────────────────────────────────────────────────
function getToken() { return localStorage.getItem('token'); }
function setToken(t) { localStorage.setItem('token', t); }
function clearToken() { localStorage.removeItem('token'); }

async function doLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    errEl.style.display = 'none';

    try {
        const body = new URLSearchParams({ username, password });
        const res = await fetch('/auth/login', { method: 'POST', body });
        if (!res.ok) {
            const err = await res.json();
            errEl.textContent = err.detail || 'Anmeldung fehlgeschlagen';
            errEl.style.display = 'block';
            return;
        }
        const data = await res.json();
        setToken(data.access_token);
        currentUser = data.user;
        showApp();
    } catch(e) {
        errEl.textContent = 'Server nicht erreichbar';
        errEl.style.display = 'block';
    }
}

function doLogout() {
    clearToken();
    currentUser = null;
    currentSalonId = null;
    document.getElementById('main-app').style.display = 'none';
    document.getElementById('login-screen').style.display = 'flex';
}

function showApp() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('main-app').style.display = 'flex';
    // Benutzername in Sidebar anzeigen
    const info = document.getElementById('sidebar-user');
    if (info && currentUser) {
        info.textContent = `👤 ${currentUser.full_name || currentUser.username}` +
            (currentUser.is_superadmin ? ' (Admin)' : '');
    }
    loadSalons();
}

async function checkAuth() {
    const token = getToken();
    if (!token) return;
    try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
            currentUser = await res.json();
            showApp();
        } else {
            clearToken();
        }
    } catch(e) {
        clearToken();
    }
}

// ─── Navigation ───────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
        e.preventDefault();
        const page = item.dataset.page;
        switchPage(page);
    });
});

function switchPage(page) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`)?.classList.add('active');
    document.getElementById('page-title').textContent = {
        config: 'System-Konfiguration',
        dashboard: 'Dashboard',
        appointments: 'Termine',
        hairdressers: 'Friseure',
        services: 'Dienstleistungen',
        salon: 'Salon-Einstellungen',
        customers: 'Kunden',
        calls: 'Anruf-Protokoll'
    }[page] || page;

    if (page === 'dashboard') loadDashboard();
    else if (page === 'appointments') { loadAppointments(); loadHairdressersForFilter(); }
    else if (page === 'hairdressers') loadHairdressers();
    else if (page === 'services') loadServices();
    else if (page === 'salon') loadSalonSettings();
    else if (page === 'customers') loadCustomers();
    else if (page === 'config') loadConfig();
    else if (page === 'calls') loadCallLog();
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3500);
}

// ─── Modals ───────────────────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
function closeModalOnOverlay(e) { if (e.target === e.currentTarget) e.currentTarget.classList.remove('open'); }

// ─── API Helpers ──────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
    const token = getToken();
    const res = await fetch(API + path, {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...options.headers
        },
        ...options
    });
    if (res.status === 401) { doLogout(); return; }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Fehler ${res.status}`);
    }
    return res.json();
}

// ─── Salon Selector ───────────────────────────────────────────────────────────
async function loadSalons() {
    try {
        const salons = await apiFetch('/api/salons/');
        const select = document.getElementById('salon-select');
        select.innerHTML = salons.length
            ? salons.map(s => `<option value="${s.id}">${s.name}</option>`).join('')
            : '<option value="">Kein Salon vorhanden</option>';

        if (salons.length) {
            currentSalonId = salons[0].id;
            select.value = currentSalonId;
        }
        select.addEventListener('change', () => {
            currentSalonId = parseInt(select.value);
            switchPage(document.querySelector('.nav-item.active').dataset.page);
        });

        if (salons.length) loadDashboard();
    } catch(e) {
        showToast('Salons konnten nicht geladen werden', 'error');
    }
}

async function createSalon(e) {
    e.preventDefault();
    const form = e.target;
    const data = Object.fromEntries(new FormData(form));
    try {
        const salon = await apiFetch('/api/salons/', { method: 'POST', body: JSON.stringify(data) });
        showToast(`Salon "${salon.name}" erstellt`);
        closeModal('modal-create-salon');
        form.reset();
        await loadSalons();
        currentSalonId = salon.id;
        document.getElementById('salon-select').value = salon.id;
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
async function loadDashboard() {
    if (!currentSalonId) return;
    const today = new Date().toISOString().split('T')[0];
    const weekEnd = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];

    try {
        const [todayAppts, weekAppts, hairdressers, calls] = await Promise.all([
            apiFetch(`/api/appointments/?salon_id=${currentSalonId}&date_from=${today}T00:00:00&date_to=${today}T23:59:59`),
            apiFetch(`/api/appointments/?salon_id=${currentSalonId}&date_from=${today}T00:00:00&date_to=${weekEnd}T23:59:59`),
            apiFetch(`/api/salons/${currentSalonId}/hairdressers`),
            apiFetch(`/calls/sessions?salon_id=${currentSalonId}`)
        ]);

        document.getElementById('stat-today').textContent = todayAppts.length;
        document.getElementById('stat-week').textContent = weekAppts.length;
        document.getElementById('stat-hairdressers').textContent = hairdressers.length;
        const todayCalls = calls.filter(c => c.created_at?.startsWith(today));
        document.getElementById('stat-calls').textContent = todayCalls.length;

        const apptContainer = document.getElementById('today-appointments');
        if (todayAppts.length === 0) {
            apptContainer.innerHTML = '<p class="empty-state">Keine Termine für heute</p>';
        } else {
            apptContainer.innerHTML = todayAppts.map(a => {
                const time = new Date(a.start_time).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
                const hd = hairdressers.find(h => h.id === a.hairdresser_id);
                return `<div class="appointment-item">
                    <div class="appointment-time">${time}</div>
                    <div class="appointment-detail">
                        <div class="appointment-name">${escHtml(a.customer_name)}</div>
                        <div class="appointment-service">${escHtml(a.services)} ${hd ? '· ' + escHtml(hd.name) : ''}</div>
                    </div>
                    <span class="badge badge-${a.status}">${statusLabel(a.status)}</span>
                </div>`;
            }).join('');
        }

        const callsContainer = document.getElementById('recent-calls');
        const recentCalls = calls.slice(0, 8);
        if (recentCalls.length === 0) {
            callsContainer.innerHTML = '<p class="empty-state">Keine Anrufe</p>';
        } else {
            callsContainer.innerHTML = recentCalls.map(c => {
                const time = new Date(c.created_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
                return `<div class="appointment-item">
                    <div class="appointment-time" style="min-width:80px;font-size:12px">${time}</div>
                    <div class="appointment-detail">
                        <div class="appointment-name">${escHtml(c.caller_phone || 'Unbekannt')}</div>
                    </div>
                    <span class="badge badge-${c.status === 'completed' ? 'confirmed' : 'pending'}">${c.status === 'completed' ? 'Gebucht' : 'Aktiv'}</span>
                </div>`;
            }).join('');
        }
    } catch(e) {
        showToast('Dashboard konnte nicht geladen werden', 'error');
    }
}

// ─── Appointments ─────────────────────────────────────────────────────────────
async function loadAppointments() {
    if (!currentSalonId) return;
    const dateFilter = document.getElementById('filter-date')?.value;
    const hairdresserFilter = document.getElementById('filter-hairdresser')?.value;

    let url = `/api/appointments/?salon_id=${currentSalonId}`;
    if (dateFilter) {
        url += `&date_from=${dateFilter}T00:00:00&date_to=${dateFilter}T23:59:59`;
    }
    if (hairdresserFilter) url += `&hairdresser_id=${hairdresserFilter}`;

    try {
        const [appointments, hairdressers] = await Promise.all([
            apiFetch(url),
            apiFetch(`/api/salons/${currentSalonId}/hairdressers`)
        ]);
        const hdMap = Object.fromEntries(hairdressers.map(h => [h.id, h.name]));

        const tbody = document.getElementById('appointments-tbody');
        if (appointments.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Keine Termine gefunden</td></tr>';
            return;
        }
        tbody.innerHTML = appointments.map(a => {
            const start = new Date(a.start_time);
            const dateStr = start.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' });
            const timeStr = start.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
            return `<tr>
                <td><strong>${dateStr}</strong><br><span style="color:var(--text-light)">${timeStr} Uhr</span></td>
                <td>${escHtml(a.customer_name)}<br><span style="color:var(--text-light);font-size:12px">${escHtml(a.customer_phone)}</span></td>
                <td>${escHtml(hdMap[a.hairdresser_id] || '—')}</td>
                <td>${escHtml(a.services)}</td>
                <td>${a.total_price ? a.total_price.toFixed(2) + ' €' : '—'}</td>
                <td><span class="badge badge-${a.status}">${statusLabel(a.status)}</span></td>
                <td>
                    ${a.status !== 'cancelled' ? `<button class="btn btn-sm btn-danger" onclick="cancelAppointment(${a.id})">Stornieren</button>` : ''}
                </td>
            </tr>`;
        }).join('');
    } catch(e) {
        showToast('Termine konnten nicht geladen werden', 'error');
    }
}

async function loadHairdressersForFilter() {
    if (!currentSalonId) return;
    const hairdressers = await apiFetch(`/api/salons/${currentSalonId}/hairdressers`).catch(() => []);
    const select = document.getElementById('filter-hairdresser');
    if (select) {
        select.innerHTML = '<option value="">Alle Friseure</option>' +
            hairdressers.map(h => `<option value="${h.id}">${escHtml(h.name)}</option>`).join('');
    }
    const apptSelect = document.getElementById('appointment-hairdresser-select');
    if (apptSelect) {
        apptSelect.innerHTML = hairdressers.map(h => `<option value="${h.id}">${escHtml(h.name)}</option>`).join('');
    }
}

async function createAppointment(e) {
    e.preventDefault();
    if (!currentSalonId) return showToast('Bitte wählen Sie einen Salon', 'error');
    const form = e.target;
    const data = Object.fromEntries(new FormData(form));
    const payload = {
        salon_id: currentSalonId,
        hairdresser_id: parseInt(data.hairdresser_id),
        customer_name: data.customer_name,
        customer_phone: data.customer_phone,
        services: data.services,
        start_time: data.start_time,
        end_time: data.end_time
    };
    try {
        await apiFetch('/api/appointments/', { method: 'POST', body: JSON.stringify(payload) });
        showToast('Termin erfolgreich erstellt');
        closeModal('modal-create-appointment');
        form.reset();
        loadAppointments();
        loadDashboard();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

async function cancelAppointment(id) {
    if (!confirm('Termin wirklich stornieren?')) return;
    try {
        await apiFetch(`/api/appointments/${id}`, { method: 'DELETE' });
        showToast('Termin storniert');
        loadAppointments();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// ─── Hairdressers ─────────────────────────────────────────────────────────────
async function loadHairdressers() {
    if (!currentSalonId) return;
    try {
        const hairdressers = await apiFetch(`/api/salons/${currentSalonId}/hairdressers`);
        const grid = document.getElementById('hairdressers-grid');
        if (hairdressers.length === 0) {
            grid.innerHTML = '<p class="empty-state">Noch keine Friseure angelegt</p>';
            return;
        }
        grid.innerHTML = hairdressers.map(h => `
            <div class="hairdresser-card">
                <div class="hairdresser-avatar">${h.name.charAt(0)}</div>
                <div class="hairdresser-name">${escHtml(h.name)}</div>
                <div class="hairdresser-spec">${escHtml(h.specialization || 'Alle Dienstleistungen')}</div>
                <button class="btn btn-sm btn-danger" onclick="deactivateHairdresser(${h.id})">Entfernen</button>
            </div>`).join('');
    } catch(e) {
        showToast('Friseure konnten nicht geladen werden', 'error');
    }
}

async function createHairdresser(e) {
    e.preventDefault();
    if (!currentSalonId) return showToast('Bitte wählen Sie einen Salon', 'error');
    const form = e.target;
    const data = Object.fromEntries(new FormData(form));
    try {
        await apiFetch('/api/hairdressers/', {
            method: 'POST',
            body: JSON.stringify({ ...data, salon_id: currentSalonId })
        });
        showToast('Friseur hinzugefügt');
        closeModal('modal-create-hairdresser');
        form.reset();
        loadHairdressers();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

async function deactivateHairdresser(id) {
    if (!confirm('Friseur wirklich entfernen?')) return;
    try {
        await apiFetch(`/api/hairdressers/${id}`, { method: 'DELETE' });
        showToast('Friseur entfernt');
        loadHairdressers();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// ─── Services ─────────────────────────────────────────────────────────────────
async function loadServices() {
    if (!currentSalonId) return;
    try {
        const services = await apiFetch(`/api/salons/${currentSalonId}/services`);
        const tbody = document.getElementById('services-tbody');
        if (services.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Noch keine Dienstleistungen</td></tr>';
            return;
        }
        tbody.innerHTML = services.map(s => `<tr>
            <td><strong>${escHtml(s.name)}</strong></td>
            <td>${escHtml(s.description || '—')}</td>
            <td>${s.duration_minutes} Min.</td>
            <td>${s.price.toFixed(2)} €</td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteService(${s.id})">Löschen</button></td>
        </tr>`).join('');
    } catch(e) {
        showToast('Dienstleistungen konnten nicht geladen werden', 'error');
    }
}

async function createService(e) {
    e.preventDefault();
    if (!currentSalonId) return showToast('Bitte wählen Sie einen Salon', 'error');
    const form = e.target;
    const data = Object.fromEntries(new FormData(form));
    try {
        await apiFetch('/api/services/', {
            method: 'POST',
            body: JSON.stringify({
                ...data,
                salon_id: currentSalonId,
                duration_minutes: parseInt(data.duration_minutes),
                price: parseFloat(data.price)
            })
        });
        showToast('Dienstleistung hinzugefügt');
        closeModal('modal-create-service');
        form.reset();
        loadServices();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

async function deleteService(id) {
    if (!confirm('Dienstleistung wirklich löschen?')) return;
    try {
        await apiFetch(`/api/services/${id}`, { method: 'DELETE' });
        showToast('Dienstleistung gelöscht');
        loadServices();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// ─── Salon Settings ───────────────────────────────────────────────────────────
async function loadSalonSettings() {
    if (!currentSalonId) return;
    try {
        const salon = await apiFetch(`/api/salons/${currentSalonId}`);
        document.getElementById('salon-name').value = salon.name || '';
        document.getElementById('salon-phone').value = salon.phone || '';
        document.getElementById('salon-email').value = salon.email || '';
        document.getElementById('salon-address').value = salon.address || '';
        document.getElementById('salon-twilio').value = salon.twilio_phone_number || '';
        document.getElementById('salon-opening').value = salon.opening_time || '09:00';
        document.getElementById('salon-closing').value = salon.closing_time || '18:00';
        document.getElementById('salon-slot-duration').value = salon.slot_duration_minutes || 30;
        document.getElementById('webhook-url').textContent =
            `${window.location.origin}/calls/incoming`;
    } catch(e) {
        showToast('Einstellungen konnten nicht geladen werden', 'error');
    }
}

async function saveSalon(e) {
    e.preventDefault();
    if (!currentSalonId) return showToast('Kein Salon ausgewählt', 'error');
    const payload = {
        name: document.getElementById('salon-name').value,
        phone: document.getElementById('salon-phone').value,
        email: document.getElementById('salon-email').value,
        address: document.getElementById('salon-address').value,
        twilio_phone_number: document.getElementById('salon-twilio').value,
        opening_time: document.getElementById('salon-opening').value,
        closing_time: document.getElementById('salon-closing').value,
        slot_duration_minutes: parseInt(document.getElementById('salon-slot-duration').value)
    };
    try {
        await apiFetch(`/api/salons/${currentSalonId}`, { method: 'PUT', body: JSON.stringify(payload) });
        showToast('Einstellungen gespeichert');
        loadSalons();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// ─── System Config ────────────────────────────────────────────────────────────
async function loadConfig() {
    try {
        const [cfg, models] = await Promise.all([
            apiFetch('/api/settings/'),
            apiFetch('/api/settings/models')
        ]);

        // Modell-Dropdown füllen
        const sel = document.getElementById('cfg-claude-model');
        sel.innerHTML = models.map(m =>
            `<option value="${m.id}" ${m.id === cfg.claude_model ? 'selected' : ''}>${escHtml(m.label)}</option>`
        ).join('');

        // Felder befüllen — API-Keys nur als Hinweis anzeigen, nie im Klartext
        document.getElementById('cfg-anthropic-key').placeholder = cfg.anthropic_api_key_set
            ? `Gesetzt: ${cfg.anthropic_api_key_preview}` : 'sk-ant-...';
        document.getElementById('cfg-anthropic-key-preview').textContent = cfg.anthropic_api_key_set
            ? `✅ API-Key hinterlegt (${cfg.anthropic_api_key_preview})` : '❌ Noch kein API-Key';

        document.getElementById('cfg-twilio-sid').value = cfg.twilio_account_sid || '';
        document.getElementById('cfg-twilio-phone').value = cfg.twilio_phone_number || '';
        document.getElementById('cfg-base-url').value = cfg.base_url || window.location.origin;

        // Webhook-URL aktualisieren
        const baseUrl = cfg.base_url || window.location.origin;
        document.getElementById('webhook-display').textContent = `${baseUrl}/calls/incoming`;

        if (cfg.updated_at) {
            const bar = document.getElementById('config-status-bar');
            bar.className = 'config-status-bar ok';
            bar.textContent = `✅ Zuletzt gespeichert: ${new Date(cfg.updated_at).toLocaleString('de-DE')}`;
            bar.style.display = 'block';
        }
    } catch(e) {
        showToast('Konfiguration konnte nicht geladen werden', 'error');
    }
}

async function saveConfig() {
    const payload = {};

    const key = document.getElementById('cfg-anthropic-key').value.trim();
    if (key) payload.anthropic_api_key = key;

    const model = document.getElementById('cfg-claude-model').value;
    if (model) payload.claude_model = model;

    const sid = document.getElementById('cfg-twilio-sid').value.trim();
    if (sid) payload.twilio_account_sid = sid;

    const token = document.getElementById('cfg-twilio-token').value.trim();
    if (token) payload.twilio_auth_token = token;

    const phone = document.getElementById('cfg-twilio-phone').value.trim();
    if (phone) payload.twilio_phone_number = phone;

    const url = document.getElementById('cfg-base-url').value.trim();
    if (url) payload.base_url = url;

    if (Object.keys(payload).length === 0) {
        showToast('Keine Änderungen zum Speichern', 'info');
        return;
    }

    try {
        await apiFetch('/api/settings/', { method: 'PUT', body: JSON.stringify(payload) });
        showToast('Konfiguration gespeichert ✅');
        // Auth-Token-Feld leeren (Sicherheit)
        document.getElementById('cfg-twilio-token').value = '';
        document.getElementById('cfg-anthropic-key').value = '';
        await loadConfig();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

async function testConnection(service) {
    const resultEl = document.getElementById(`test-${service}-result`);
    resultEl.className = 'test-result';
    resultEl.textContent = '⏳ Teste...';
    try {
        const results = await apiFetch('/api/settings/test-connection', { method: 'POST' });
        const r = results[service];
        resultEl.className = `test-result ${r.ok ? 'ok' : 'err'}`;
        resultEl.textContent = r.ok ? `✅ ${r.message}` : `❌ ${r.message}`;
    } catch(e) {
        resultEl.className = 'test-result err';
        resultEl.textContent = `❌ ${e.message}`;
    }
}

function toggleVisibility(inputId) {
    const input = document.getElementById(inputId);
    input.type = input.type === 'password' ? 'text' : 'password';
}

// ─── Customers ───────────────────────────────────────────────────────────────
const LANG_LABELS = { de: 'Deutsch 🇩🇪', en: 'Englisch 🇬🇧', tr: 'Türkçe 🇹🇷' };

async function loadCustomers(search = '') {
    if (!currentSalonId) return;
    const url = `/api/customers/?salon_id=${currentSalonId}` + (search ? `&search=${encodeURIComponent(search)}` : '');
    try {
        const customers = await apiFetch(url);
        const tbody = document.getElementById('customers-tbody');
        if (customers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Keine Kunden gefunden</td></tr>';
            return;
        }
        tbody.innerHTML = customers.map(c => {
            const lastVisit = c.last_visit ? new Date(c.last_visit).toLocaleDateString('de-DE') : '—';
            return `<tr>
                <td><strong>${escHtml(c.name)}</strong></td>
                <td>${escHtml(c.phone)}</td>
                <td>${LANG_LABELS[c.preferred_language] || c.preferred_language}</td>
                <td>${c.visit_count}</td>
                <td>${lastVisit}</td>
                <td>${escHtml(c.notes || '—')}</td>
                <td style="display:flex;gap:6px">
                    <button class="btn btn-sm btn-secondary" onclick="openEditCustomer(${JSON.stringify(c).replace(/"/g,'&quot;')})">Bearbeiten</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${c.id})">Löschen</button>
                </td>
            </tr>`;
        }).join('');
    } catch(e) {
        showToast('Kunden konnten nicht geladen werden', 'error');
    }
}

function searchCustomers() {
    const val = document.getElementById('customer-search').value;
    loadCustomers(val);
}

async function createCustomer(e) {
    e.preventDefault();
    if (!currentSalonId) return showToast('Bitte wählen Sie einen Salon', 'error');
    const form = e.target;
    const data = Object.fromEntries(new FormData(form));
    try {
        await apiFetch('/api/customers/', {
            method: 'POST',
            body: JSON.stringify({ ...data, salon_id: currentSalonId })
        });
        showToast('Kunde angelegt');
        closeModal('modal-create-customer');
        form.reset();
        loadCustomers();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

function openEditCustomer(customer) {
    document.getElementById('edit-customer-id').value = customer.id;
    document.getElementById('edit-customer-name').value = customer.name;
    document.getElementById('edit-customer-phone').value = customer.phone;
    document.getElementById('edit-customer-email').value = customer.email || '';
    document.getElementById('edit-customer-lang').value = customer.preferred_language || 'de';
    document.getElementById('edit-customer-notes').value = customer.notes || '';
    openModal('modal-edit-customer');
}

async function saveCustomer(e) {
    e.preventDefault();
    const id = document.getElementById('edit-customer-id').value;
    const payload = {
        name: document.getElementById('edit-customer-name').value,
        phone: document.getElementById('edit-customer-phone').value,
        email: document.getElementById('edit-customer-email').value || null,
        preferred_language: document.getElementById('edit-customer-lang').value,
        notes: document.getElementById('edit-customer-notes').value || null,
    };
    try {
        await apiFetch(`/api/customers/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        showToast('Kunde gespeichert');
        closeModal('modal-edit-customer');
        loadCustomers();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

async function deleteCustomer(id) {
    if (!confirm('Kunden wirklich löschen?')) return;
    try {
        await apiFetch(`/api/customers/${id}`, { method: 'DELETE' });
        showToast('Kunde gelöscht');
        loadCustomers();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// ─── Call Log ─────────────────────────────────────────────────────────────────
async function loadCallLog() {
    if (!currentSalonId) return;
    try {
        const calls = await apiFetch(`/calls/sessions?salon_id=${currentSalonId}`);
        const tbody = document.getElementById('calls-tbody');
        if (calls.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Noch keine Anrufe</td></tr>';
            return;
        }
        tbody.innerHTML = calls.map(c => {
            const dt = new Date(c.created_at).toLocaleString('de-DE');
            return `<tr>
                <td>${dt}</td>
                <td>${escHtml(c.caller_phone || 'Unbekannt')}</td>
                <td><span class="badge badge-${c.status === 'completed' ? 'confirmed' : 'pending'}">${c.status === 'completed' ? 'Gebucht' : c.status === 'active' ? 'Aktiv' : 'Abgebrochen'}</span></td>
                <td><button class="btn btn-sm btn-secondary" onclick="showConversation('${escHtml(c.conversation_history || '[]')}')">Gespräch</button></td>
            </tr>`;
        }).join('');
    } catch(e) {
        showToast('Anruf-Protokoll konnte nicht geladen werden', 'error');
    }
}

function showConversation(historyJson) {
    let history;
    try { history = JSON.parse(historyJson); } catch { history = []; }

    const content = document.getElementById('conversation-content');
    if (!history.length) {
        content.innerHTML = '<p class="empty-state">Kein Gesprächsprotokoll vorhanden</p>';
    } else {
        content.innerHTML = history.map(msg => `
            <div class="message message-${msg.role}">
                <div class="message-role">${msg.role === 'user' ? 'Kunde' : 'Assistent'}</div>
                ${escHtml(msg.content)}
            </div>`).join('');
    }
    openModal('modal-conversation');
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function statusLabel(status) {
    return { confirmed: 'Bestätigt', cancelled: 'Storniert', pending: 'Ausstehend', completed: 'Abgeschlossen' }[status] || status;
}

function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Init ─────────────────────────────────────────────────────────────────────
const today = new Date().toISOString().split('T')[0];
const filterDate = document.getElementById('filter-date');
if (filterDate) filterDate.value = today;

checkAuth();
