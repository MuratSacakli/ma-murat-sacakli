const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'wedding.db');
const db = new Database(DB_PATH);

db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    bride_name TEXT NOT NULL DEFAULT '',
    groom_name TEXT NOT NULL DEFAULT '',
    event_date TEXT NOT NULL DEFAULT '',
    event_time TEXT NOT NULL DEFAULT '',
    venue_name TEXT NOT NULL DEFAULT '',
    venue_address TEXT NOT NULL DEFAULT '',
    host_phone TEXT NOT NULL DEFAULT '',
    message_template TEXT NOT NULL DEFAULT ''
  );

  INSERT OR IGNORE INTO event (id, message_template) VALUES (1,
    '🌹 *Düğün Davetiyesi* 🌹\n\nSayın *{{name}}*,\n\nSizi düğünümüze davet etmekten büyük mutluluk duyuyoruz! 💍\n\n👰 *{{bride}}* & 🤵 *{{groom}}*\n\n📅 *Tarih:* {{date}}\n⏰ *Saat:* {{time}}\n📍 *Mekan:* {{venue}}\n\nLütfen davetiyenizi görmek ve katılım durumunuzu bildirmek için linke tıklayın:\n🔗 {{link}}\n\nSizi aramızda görmekten mutluluk duyarız! 🎊'
  );

  CREATE TABLE IF NOT EXISTS guests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    rsvp TEXT NOT NULL DEFAULT 'pending',
    sent INTEGER NOT NULL DEFAULT 0,
    sent_at TEXT,
    rsvp_at TEXT
  );
`);

const eventStmt = {
  get: db.prepare('SELECT * FROM event WHERE id = 1'),
  update: db.prepare(`
    UPDATE event SET
      bride_name = @bride_name,
      groom_name = @groom_name,
      event_date = @event_date,
      event_time = @event_time,
      venue_name = @venue_name,
      venue_address = @venue_address,
      host_phone = @host_phone,
      message_template = @message_template
    WHERE id = 1
  `)
};

const guestStmt = {
  all: db.prepare('SELECT * FROM guests ORDER BY name ASC'),
  get: db.prepare('SELECT * FROM guests WHERE id = ?'),
  getByToken: db.prepare('SELECT * FROM guests WHERE token = ?'),
  insert: db.prepare('INSERT INTO guests (name, phone, token) VALUES (@name, @phone, @token)'),
  delete: db.prepare('DELETE FROM guests WHERE id = ?'),
  updateRsvp: db.prepare('UPDATE guests SET rsvp = @rsvp, rsvp_at = @rsvp_at WHERE token = @token'),
  markSent: db.prepare('UPDATE guests SET sent = 1, sent_at = @sent_at WHERE id = @id'),
  stats: db.prepare(`
    SELECT
      COUNT(*) as total,
      SUM(CASE WHEN rsvp = 'yes'     THEN 1 ELSE 0 END) as yes,
      SUM(CASE WHEN rsvp = 'no'      THEN 1 ELSE 0 END) as no,
      SUM(CASE WHEN rsvp = 'maybe'   THEN 1 ELSE 0 END) as maybe,
      SUM(CASE WHEN rsvp = 'pending' THEN 1 ELSE 0 END) as pending,
      SUM(CASE WHEN sent = 1         THEN 1 ELSE 0 END) as sent
    FROM guests
  `)
};

module.exports = { eventStmt, guestStmt };
