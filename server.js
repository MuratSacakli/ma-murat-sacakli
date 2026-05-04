require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const { eventStmt, guestStmt } = require('./db');
const wa = require('./whatsapp-service');

const app = express();
const PORT = process.env.PORT || 3000;
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ─── Event ────────────────────────────────────────────────────────────────────

app.get('/api/event', (req, res) => {
  res.json(eventStmt.get.get());
});

app.put('/api/event', (req, res) => {
  const {
    bride_name = '', groom_name = '',
    event_date = '', event_time = '',
    venue_name = '', venue_address = '',
    host_phone = '', message_template = ''
  } = req.body;

  eventStmt.update.run({
    bride_name, groom_name, event_date, event_time,
    venue_name, venue_address, host_phone, message_template
  });
  res.json(eventStmt.get.get());
});

// ─── Guests ───────────────────────────────────────────────────────────────────

app.get('/api/guests', (req, res) => {
  res.json(guestStmt.all.all());
});

app.get('/api/guests/stats', (req, res) => {
  res.json(guestStmt.stats.get());
});

app.post('/api/guests', (req, res) => {
  const { name, phone } = req.body;
  if (!name || !phone) return res.status(400).json({ error: 'Name und Telefonnummer erforderlich' });

  const token = uuidv4();
  try {
    guestStmt.insert.run({ name: name.trim(), phone: phone.trim(), token });
    const guest = guestStmt.getByToken.get(token);
    res.status(201).json(guest);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/guests/:id', (req, res) => {
  guestStmt.delete.run(req.params.id);
  res.json({ ok: true });
});

// ─── WhatsApp ─────────────────────────────────────────────────────────────────

app.get('/api/whatsapp', (req, res) => {
  res.json(wa.getStatus());
});

app.post('/api/whatsapp/init', async (req, res) => {
  try {
    wa.initialize().catch(console.error);
    res.json({ ok: true, message: 'WhatsApp-Initialisierung gestartet' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ─── Send invitations ─────────────────────────────────────────────────────────

const ALLOWED_TEMPLATES = ['invite.html', 'invite-islamic.html', 'invite-oriental.html'];

function buildMessage(template, guest, event, inviteUrl) {
  return template
    .replace(/{{name}}/g, guest.name)
    .replace(/{{bride}}/g, event.bride_name)
    .replace(/{{groom}}/g, event.groom_name)
    .replace(/{{date}}/g, event.event_date)
    .replace(/{{time}}/g, event.event_time)
    .replace(/{{venue}}/g, event.venue_name)
    .replace(/{{link}}/g, inviteUrl);
}

function resolveTemplate(raw) {
  const tpl = raw && ALLOWED_TEMPLATES.includes(raw) ? raw : 'invite.html';
  return tpl;
}

app.post('/api/send/:id', async (req, res) => {
  const guest = guestStmt.get.get(req.params.id);
  if (!guest) return res.status(404).json({ error: 'Gast nicht gefunden' });

  const event     = eventStmt.get.get();
  const tpl       = resolveTemplate(req.body.template);
  const inviteUrl = `${BASE_URL}/${tpl}?token=${guest.token}`;
  const message   = buildMessage(event.message_template, guest, event, inviteUrl);

  try {
    await wa.sendMessage(guest.phone, message);
    guestStmt.markSent.run({ id: guest.id, sent_at: new Date().toISOString() });
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/send-all', async (req, res) => {
  const { status: waStatus } = wa.getStatus();
  if (waStatus !== 'ready') {
    return res.status(400).json({ error: 'WhatsApp nicht verbunden' });
  }

  const guests  = guestStmt.all.all();
  const event   = eventStmt.get.get();
  const tpl     = resolveTemplate(req.body.template);
  const results = { sent: 0, failed: 0, errors: [] };

  for (const guest of guests) {
    const inviteUrl = `${BASE_URL}/${tpl}?token=${guest.token}`;
    const message   = buildMessage(event.message_template, guest, event, inviteUrl);
    try {
      await wa.sendMessage(guest.phone, message);
      guestStmt.markSent.run({ id: guest.id, sent_at: new Date().toISOString() });
      results.sent++;
      // small delay to avoid WhatsApp rate-limiting
      await new Promise(r => setTimeout(r, 1200));
    } catch (e) {
      results.failed++;
      results.errors.push({ name: guest.name, error: e.message });
    }
  }

  res.json(results);
});

// ─── RSVP (guest-facing) ──────────────────────────────────────────────────────

app.get('/api/invite/:token', (req, res) => {
  const guest = guestStmt.getByToken.get(req.params.token);
  if (!guest) return res.status(404).json({ error: 'Einladung nicht gefunden' });

  const event = eventStmt.get.get();
  const inviteUrl = `${BASE_URL}/invite.html?token=${guest.token}`;
  res.json({ guest, event, inviteUrl });
});

app.post('/api/rsvp/:token', (req, res) => {
  const { status } = req.body;
  if (!['yes', 'no', 'maybe'].includes(status)) {
    return res.status(400).json({ error: 'Ungültiger Status' });
  }

  const guest = guestStmt.getByToken.get(req.params.token);
  if (!guest) return res.status(404).json({ error: 'Einladung nicht gefunden' });

  guestStmt.updateRsvp.run({ token: req.params.token, rsvp: status, rsvp_at: new Date().toISOString() });

  const event = eventStmt.get.get();
  res.json({ ok: true, hostPhone: event.host_phone, guestName: guest.name });
});

// ─── Start ────────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`Server läuft auf http://localhost:${PORT}`);
  console.log('WhatsApp-Integration: POST /api/whatsapp/init zum Starten');
});
