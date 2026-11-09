const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcryptjs');
const { DB_PATH, ADMIN_DEFAULT_USER, ADMIN_DEFAULT_PASS } = require('../../config');
const { THANK_YOU_MESSAGE } = require('../../config/templates');
const cloudSync = require('./cloud_sync');

const resolvedDbPath = path.resolve(DB_PATH);
const dir = path.dirname(resolvedDbPath);
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

// On Vercel (/tmp/), seed existing database file if present
if ((resolvedDbPath.startsWith('/tmp') || resolvedDbPath.includes('tmp')) && !fs.existsSync(resolvedDbPath)) {
  const seedCandidates = [
    path.resolve(__dirname, '../../data/aschen_booking.db'),
    path.resolve(process.cwd(), 'data/aschen_booking.db')
  ];
  for (const seedPath of seedCandidates) {
    if (fs.existsSync(seedPath)) {
      try {
        fs.copyFileSync(seedPath, resolvedDbPath);
        console.log(`[Database] Database seeded to ${resolvedDbPath} from ${seedPath}`);
        break;
      } catch (err) {
        console.warn('[Database] Seed copy warning:', err.message);
      }
    }
  }
}

// Try restoring newer cloud database snapshot from Vercel Blob if available
cloudSync.syncFromCloud(resolvedDbPath).catch(() => {});

const db = new Database(resolvedDbPath);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// Initialize schema
db.exec(`
  CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT UNIQUE NOT NULL,
    telegram_id INTEGER NOT NULL,
    username TEXT,
    full_name TEXT,
    category TEXT NOT NULL,
    category_name TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Formulir Terkirim',
    form_data TEXT NOT NULL,
    rendered_preview TEXT NOT NULL,
    venue_data TEXT,
    venue_rendered TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_bookings_booking_id ON bookings(booking_id);
  CREATE INDEX IF NOT EXISTS idx_bookings_telegram_id ON bookings(telegram_id);
  CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

  CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT NOT NULL,
    sender_type TEXT NOT NULL, -- 'customer' or 'admin'
    sender_name TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    FOREIGN KEY(booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
  );

  CREATE INDEX IF NOT EXISTS idx_messages_booking_id ON messages(booking_id);

  CREATE TABLE IF NOT EXISTS scheduled_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT NOT NULL,
    telegram_id INTEGER NOT NULL,
    event_date TEXT NOT NULL,
    scheduled_at TEXT NOT NULL, -- ISO timestamp for 19:00 WIB
    message_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'cancelled'
    error_log TEXT,
    sent_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
  );

  CREATE INDEX IF NOT EXISTS idx_scheduled_status ON scheduled_messages(status);

  CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    telegram_id INTEGER,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS user_sessions (
    telegram_id INTEGER PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS notification_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT UNIQUE NOT NULL,
    channel_title TEXT,
    channel_username TEXT,
    added_at TEXT NOT NULL
  );
`);

// Seed default admin if not exists
const checkAdmin = db.prepare('SELECT id FROM admins WHERE username = ?').get(ADMIN_DEFAULT_USER);
if (!checkAdmin) {
  const salt = bcrypt.genSaltSync(10);
  const hash = bcrypt.hashSync(ADMIN_DEFAULT_PASS, salt);
  db.prepare(`
    INSERT INTO admins (username, password_hash, name, role, created_at)
    VALUES (?, ?, ?, 'superadmin', datetime('now'))
  `).run(ADMIN_DEFAULT_USER, hash, 'ASCHEN Lead Admin');
  console.log(`[DB] Created default admin account: ${ADMIN_DEFAULT_USER}`);
}

// Generate unique Booking ID: e.g. ASC-WED-9482
function generateBookingId(categoryCode) {
  const code = (categoryCode || 'EVT').toUpperCase();
  const now = new Date();
  const year = now.getFullYear().toString().slice(-2);
  const month = String(now.getMonth() + 1).padStart(2, '0');
  
  // Try generating an ID and ensure uniqueness
  let id = '';
  let exists = true;
  while (exists) {
    const random = Math.floor(1000 + Math.random() * 9000); // 4 digit random
    id = `ASC-${code}-${year}${month}-${random}`;
    const row = db.prepare('SELECT id FROM bookings WHERE booking_id = ?').get(id);
    if (!row) exists = false;
  }
  return id;
}

// Session state storage (ensures form progress survives restarts)
function getUserSession(telegramId) {
  const row = db.prepare('SELECT state_json FROM user_sessions WHERE telegram_id = ?').get(telegramId);
  return row ? JSON.parse(row.state_json) : null;
}

function setUserSession(telegramId, state) {
  const stateJson = JSON.stringify(state);
  const now = new Date().toISOString();
  db.prepare(`
    INSERT INTO user_sessions (telegram_id, state_json, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(telegram_id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
  `).run(telegramId, stateJson, now);
}

function clearUserSession(telegramId) {
  db.prepare('DELETE FROM user_sessions WHERE telegram_id = ?').run(telegramId);
}

// Bookings methods
function createBooking({ category, categoryName, categoryCode, telegramId, username, fullName, eventDate, eventTime, formData, renderedPreview }) {
  const bookingId = generateBookingId(categoryCode);
  const now = new Date().toISOString();
  const initialStatus = 'Formulir Terkirim';

  const insertBooking = db.prepare(`
    INSERT INTO bookings (
      booking_id, telegram_id, username, full_name, category, category_name,
      event_date, event_time, status, form_data, rendered_preview,
      created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertHistory = db.prepare(`
    INSERT INTO status_history (booking_id, old_status, new_status, changed_by, notes, created_at)
    VALUES (?, NULL, ?, 'Pelanggan', 'Formulir booking berhasil dikirimkan.', ?)
  `);

  const transaction = db.transaction(() => {
    insertBooking.run(
      bookingId,
      telegramId,
      username || '',
      fullName || '',
      category,
      categoryName,
      eventDate,
      eventTime,
      initialStatus,
      JSON.stringify(formData),
      renderedPreview,
      now,
      now
    );

    insertHistory.run(bookingId, initialStatus, now);
  });

  transaction();
  const created = getBookingById(bookingId);
  cloudSync.syncToCloud(resolvedDbPath).catch(() => {});
  return created;
}

function getBookingById(bookingId) {
  const row = db.prepare('SELECT * FROM bookings WHERE booking_id = ?').get(bookingId);
  if (!row) return null;
  return {
    ...row,
    form_data: JSON.parse(row.form_data || '{}'),
    venue_data: row.venue_data ? JSON.parse(row.venue_data) : null
  };
}

function getBookings({ search, status, category, limit = 50, offset = 0 } = {}) {
  let query = 'SELECT * FROM bookings WHERE 1=1';
  const params = [];

  if (search) {
    query += ' AND (booking_id LIKE ? OR username LIKE ? OR full_name LIKE ?)';
    const term = `%${search}%`;
    params.push(term, term, term);
  }

  if (status) {
    query += ' AND status = ?';
    params.push(status);
  }

  if (category) {
    query += ' AND category = ?';
    params.push(category);
  }

  query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
  params.push(limit, offset);

  const rows = db.prepare(query).all(...params);
  return rows.map(r => ({
    ...r,
    form_data: JSON.parse(r.form_data || '{}'),
    venue_data: r.venue_data ? JSON.parse(r.venue_data) : null
  }));
}

function getBookingsByTelegramId(telegramId) {
  const rows = db.prepare('SELECT * FROM bookings WHERE telegram_id = ? ORDER BY created_at DESC').all(telegramId);
  return rows.map(r => ({
    ...r,
    form_data: JSON.parse(r.form_data || '{}'),
    venue_data: r.venue_data ? JSON.parse(r.venue_data) : null
  }));
}

function updateBookingStatus(bookingId, newStatus, changedBy = 'Admin', notes = '') {
  const current = getBookingById(bookingId);
  if (!current) throw new Error(`Booking ${bookingId} tidak ditemukan.`);

  const now = new Date().toISOString();

  const updateBooking = db.prepare(`
    UPDATE bookings SET status = ?, updated_at = ? WHERE booking_id = ?
  `);

  const insertHistory = db.prepare(`
    INSERT INTO status_history (booking_id, old_status, new_status, changed_by, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  const transaction = db.transaction(() => {
    updateBooking.run(newStatus, now, bookingId);
    insertHistory.run(bookingId, current.status, newStatus, changedBy, notes, now);

    // If status became "Booking Diterima" or "Booking Dikonfirmasi", schedule or update the Thank You message!
    if (newStatus === 'Booking Diterima' || newStatus === 'Booking Dikonfirmasi') {
      scheduleThankYouMessage(bookingId, current.telegram_id, current.event_date);
    } else if (newStatus === 'Booking Dibatalkan' || newStatus === 'Booking Ditolak') {
      cancelScheduledThankYou(bookingId);
    }
  });

  transaction();
  const updated = getBookingById(bookingId);
  cloudSync.syncToCloud(resolvedDbPath).catch(() => {});
  return updated;
}

function updateBookingVenue(bookingId, venueData, venueRendered) {
  const current = getBookingById(bookingId);
  if (!current) throw new Error(`Booking ${bookingId} tidak ditemukan.`);

  const now = new Date().toISOString();
  const newStatus = 'Reservasi Tempat Tercatat';

  const update = db.prepare(`
    UPDATE bookings 
    SET venue_data = ?, venue_rendered = ?, status = ?, updated_at = ?
    WHERE booking_id = ?
  `);

  const insertHistory = db.prepare(`
    INSERT INTO status_history (booking_id, old_status, new_status, changed_by, notes, created_at)
    VALUES (?, ?, ?, 'Pelanggan', 'Formulir reservasi tempat telah diisi.', ?)
  `);

  const transaction = db.transaction(() => {
    update.run(JSON.stringify(venueData), venueRendered, newStatus, now, bookingId);
    insertHistory.run(bookingId, current.status, newStatus, now);
  });

  transaction();
  return getBookingById(bookingId);
}

function updateEventDate(bookingId, newDate, changedBy = 'Admin') {
  const current = getBookingById(bookingId);
  if (!current) throw new Error(`Booking ${bookingId} tidak ditemukan.`);

  const now = new Date().toISOString();
  db.prepare(`UPDATE bookings SET event_date = ?, updated_at = ? WHERE booking_id = ?`).run(newDate, now, bookingId);
  
  db.prepare(`
    INSERT INTO status_history (booking_id, old_status, new_status, changed_by, notes, created_at)
    VALUES (?, ?, ?, ?, 'Perubahan tanggal acara menjadi: ' || ?, ?)
  `).run(bookingId, current.status, current.status, changedBy, newDate, now);

  // Re-schedule thank you message if scheduled
  scheduleThankYouMessage(bookingId, current.telegram_id, newDate);
}

// Status History
function getStatusHistory(bookingId) {
  return db.prepare('SELECT * FROM status_history WHERE booking_id = ? ORDER BY created_at ASC').all(bookingId);
}

// Messages (Two-way communication)
function addMessage(bookingId, senderType, senderName, message) {
  const now = new Date().toISOString();
  const res = db.prepare(`
    INSERT INTO messages (booking_id, sender_type, sender_name, message, created_at, is_read)
    VALUES (?, ?, ?, ?, ?, 0)
  `).run(bookingId, senderType, senderName, message, now);

  const saved = db.prepare('SELECT * FROM messages WHERE id = ?').get(res.lastInsertRowid);
  cloudSync.syncToCloud(resolvedDbPath).catch(() => {});
  return saved;
}

function getMessages(bookingId) {
  return db.prepare('SELECT * FROM messages WHERE booking_id = ? ORDER BY created_at ASC').all(bookingId);
}

function markMessagesAsRead(bookingId, readerType) {
  // If reader is admin, mark customer messages as read
  // If reader is customer, mark admin messages as read
  const targetSender = readerType === 'admin' ? 'customer' : 'admin';
  db.prepare(`
    UPDATE messages SET is_read = 1 WHERE booking_id = ? AND sender_type = ?
  `).run(bookingId, targetSender);
}

// Scheduled Messages (Thank You message scheduled at 19:00 WIB)
function parseWibDateToIso(dateStr) {
  // Expected dateStr: DD/MM/YYYY or YYYY-MM-DD
  let day, month, year;
  if (dateStr.includes('/')) {
    const parts = dateStr.split('/');
    day = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10) - 1;
    year = parseInt(parts[2], 10);
  } else if (dateStr.includes('-')) {
    const parts = dateStr.split('-');
    year = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10) - 1;
    day = parseInt(parts[2], 10);
  } else {
    return null;
  }

  // 19:00 WIB = 12:00 UTC (WIB is UTC+7)
  const utcDate = new Date(Date.UTC(year, month, day, 12, 0, 0, 0));
  return utcDate.toISOString();
}

function scheduleThankYouMessage(bookingId, telegramId, eventDate) {
  const scheduledAt = parseWibDateToIso(eventDate);
  if (!scheduledAt) {
    console.warn(`[Scheduler] Could not parse event date ${eventDate} for booking ${bookingId}`);
    return;
  }

  const now = new Date().toISOString();
  const existing = db.prepare('SELECT id, status FROM scheduled_messages WHERE booking_id = ?').get(bookingId);

  if (existing) {
    // Only update if not already sent
    if (existing.status !== 'sent') {
      db.prepare(`
        UPDATE scheduled_messages 
        SET event_date = ?, scheduled_at = ?, status = 'pending', updated_at = ?
        WHERE id = ?
      `).run(eventDate, scheduledAt, now, existing.id);
      console.log(`[Scheduler] Rescheduled thank you message for ${bookingId} to ${scheduledAt} (19:00 WIB)`);
    }
  } else {
    db.prepare(`
      INSERT INTO scheduled_messages (
        booking_id, telegram_id, event_date, scheduled_at, message_text,
        status, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
    `).run(bookingId, telegramId, eventDate, scheduledAt, THANK_YOU_MESSAGE, now, now);
    console.log(`[Scheduler] Scheduled thank you message for ${bookingId} at ${scheduledAt} (19:00 WIB)`);
  }
}

function cancelScheduledThankYou(bookingId) {
  db.prepare(`
    UPDATE scheduled_messages SET status = 'cancelled', updated_at = datetime('now')
    WHERE booking_id = ? AND status = 'pending'
  `).run(bookingId);
}

function getDueScheduledMessages() {
  const nowIso = new Date().toISOString();
  return db.prepare(`
    SELECT * FROM scheduled_messages 
    WHERE status = 'pending' AND scheduled_at <= ?
  `).all(nowIso);
}

function markScheduleSent(id) {
  const now = new Date().toISOString();
  db.prepare(`
    UPDATE scheduled_messages 
    SET status = 'sent', sent_at = ?, updated_at = ?
    WHERE id = ?
  `).run(now, now, id);
}

function markScheduleFailed(id, errorMessage) {
  const now = new Date().toISOString();
  db.prepare(`
    UPDATE scheduled_messages 
    SET status = 'failed', error_log = ?, updated_at = ?
    WHERE id = ?
  `).run(errorMessage, now, id);
}

function getAllSchedules() {
  return db.prepare(`
    SELECT sm.*, b.full_name, b.username, b.category_name 
    FROM scheduled_messages sm
    LEFT JOIN bookings b ON sm.booking_id = b.booking_id
    ORDER BY sm.scheduled_at ASC
  `).all();
}

// Admins management
function getAdminByUsername(username) {
  return db.prepare('SELECT * FROM admins WHERE username = ?').get(username);
}

function getAllAdmins() {
  return db.prepare('SELECT id, username, telegram_id, name, role, created_at FROM admins').all();
}

function createAdmin({ username, password, name, telegramId, role = 'admin' }) {
  const salt = bcrypt.genSaltSync(10);
  const hash = bcrypt.hashSync(password, salt);
  const now = new Date().toISOString();

  return db.prepare(`
    INSERT INTO admins (username, password_hash, telegram_id, name, role, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(username, hash, telegramId || null, name, role, now);
}

function verifyAdminPassword(candidatePassword, passwordHash) {
  return bcrypt.compareSync(candidatePassword, passwordHash);
}

// Statistics for Dashboard
function getDashboardStats() {
  const totalBookings = db.prepare('SELECT COUNT(*) as count FROM bookings').get().count;
  const pending = db.prepare("SELECT COUNT(*) as count FROM bookings WHERE status IN ('Formulir Terkirim', 'Menunggu Balasan Admin')").get().count;
  const confirmed = db.prepare("SELECT COUNT(*) as count FROM bookings WHERE status IN ('Booking Diterima', 'Booking Dikonfirmasi', 'Reservasi Tempat Tercatat')").get().count;
  const completed = db.prepare("SELECT COUNT(*) as count FROM bookings WHERE status = 'Booking Selesai'").get().count;

  const categoryStats = db.prepare(`
    SELECT category_name, COUNT(*) as count 
    FROM bookings 
    GROUP BY category_name
  `).all();

  const statusStats = db.prepare(`
    SELECT status, COUNT(*) as count 
    FROM bookings 
    GROUP BY status
  `).all();

  const recentBookings = getBookings({ limit: 10 });

  return {
    totalBookings,
    pending,
    confirmed,
    completed,
    categoryStats,
    statusStats,
    recentBookings
  };
}

// Notification Channels (Channels/Groups where bot is added)
function addNotificationChannel(channelId, title, username) {
  const now = new Date().toISOString();
  db.prepare(`
    INSERT INTO notification_channels (channel_id, channel_title, channel_username, added_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(channel_id) DO UPDATE SET 
      channel_title = excluded.channel_title,
      channel_username = excluded.channel_username,
      added_at = excluded.added_at
  `).run(String(channelId), title || '', username || '', now);
}

function removeNotificationChannel(channelId) {
  db.prepare('DELETE FROM notification_channels WHERE channel_id = ?').run(String(channelId));
}

function getNotificationChannels() {
  return db.prepare('SELECT * FROM notification_channels ORDER BY added_at DESC').all();
}

module.exports = {
  db,
  createBooking,
  getBookingById,
  getBookings,
  getBookingsByTelegramId,
  updateBookingStatus,
  updateBookingVenue,
  updateEventDate,
  getStatusHistory,
  addMessage,
  getMessages,
  markMessagesAsRead,
  scheduleThankYouMessage,
  cancelScheduledThankYou,
  getDueScheduledMessages,
  markScheduleSent,
  markScheduleFailed,
  getAllSchedules,
  getUserSession,
  setUserSession,
  clearUserSession,
  getAdminByUsername,
  getAllAdmins,
  createAdmin,
  verifyAdminPassword,
  getDashboardStats,
  addNotificationChannel,
  removeNotificationChannel,
  getNotificationChannels
};
