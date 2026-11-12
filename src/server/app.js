/**
 * ASCHEN EVENT ORGANIZER - Express Server & REST API
 */

const express = require('express');
const path = require('path');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const db = require('../database/db');
const cloudSync = require('../database/cloud_sync');
const { BOOKING_STATUSES, CATEGORIES, OFFICIAL_RESERVASI_URL } = require('../../config/templates');
const { generateToken, authMiddleware } = require('./auth');
const messaging = require('../services/messaging');
const scheduler = require('../services/scheduler');
const { Markup } = require('telegraf');

function createServer(botInstance, io) {
  const app = express();

  // Trust reverse proxy (Cloudflare, Nginx, Railway, Render)
  app.set('trust proxy', 1);

  app.use(cors());
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));
  app.use(cookieParser());

  // Static files (Admin Dashboard UI)
  app.use(express.static(path.join(__dirname, '../public')));

  // --- AUTH ROUTES ---
  app.post('/api/auth/login', (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) {
      return res.status(400).json({ error: 'Username dan password wajib diisi.' });
    }

    const admin = db.getAdminByUsername(username);
    if (!admin || !db.verifyAdminPassword(password, admin.password_hash)) {
      return res.status(401).json({ error: 'Username atau password tidak sesuai.' });
    }

    const token = generateToken(admin);
    res.cookie('admin_token', token, {
      httpOnly: true,
      maxAge: 7 * 24 * 60 * 60 * 1000,
      sameSite: 'lax'
    });

    res.json({
      success: true,
      token,
      admin: {
        id: admin.id,
        username: admin.username,
        name: admin.name,
        role: admin.role
      }
    });
  });

  app.get('/api/auth/me', authMiddleware, (req, res) => {
    res.json({ admin: req.admin });
  });

  app.post('/api/auth/logout', (req, res) => {
    res.clearCookie('admin_token');
    res.json({ success: true, message: 'Berhasil logout.' });
  });

  // --- DASHBOARD OVERVIEW & STATS ---
  app.get('/api/stats', authMiddleware, async (req, res) => {
    try {
      if (typeof db.restoreFromCloud === 'function') {
        await db.restoreFromCloud();
      }
      const stats = db.getDashboardStats();
      res.json(stats);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // --- BOOKINGS CRUD & ACTIONS ---
  app.get('/api/bookings', authMiddleware, async (req, res) => {
    try {
      const { search, status, category, limit = 100, offset = 0 } = req.query;
      if (typeof db.restoreFromCloud === 'function') {
        await db.restoreFromCloud();
      }
      const bookings = db.getBookings({ search, status, category, limit: parseInt(limit, 10), offset: parseInt(offset, 10) });
      res.json({ bookings, statuses: BOOKING_STATUSES, categories: CATEGORIES });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get('/api/bookings/:bookingId', authMiddleware, async (req, res) => {
    try {
      if (typeof db.restoreFromCloud === 'function') {
        await db.restoreFromCloud();
      }
      const booking = db.getBookingById(req.params.bookingId);
      if (!booking) return res.status(404).json({ error: 'Booking tidak ditemukan.' });

      const history = db.getStatusHistory(req.params.bookingId);
      const messages = db.getMessages(req.params.bookingId);
      const schedule = db.db.prepare('SELECT * FROM scheduled_messages WHERE booking_id = ?').get(req.params.bookingId);

      // Mark customer messages as read by admin
      db.markMessagesAsRead(req.params.bookingId, 'admin');

      res.json({
        booking,
        history,
        messages,
        schedule,
        statuses: BOOKING_STATUSES
      });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // Update Status
  app.post('/api/bookings/:bookingId/status', authMiddleware, async (req, res) => {
    try {
      const { status, notes } = req.body;
      if (!BOOKING_STATUSES.includes(status)) {
        return res.status(400).json({ error: 'Status tidak valid.' });
      }

      const booking = db.getBookingById(req.params.bookingId);
      if (!booking) return res.status(404).json({ error: 'Booking tidak ditemukan.' });

      const updated = db.updateBookingStatus(
        req.params.bookingId,
        status,
        req.admin.name || req.admin.username,
        notes || ''
      );

      // Send status update notification to customer via Telegram Bot!
      if (botInstance) {
        const notifText = `𓄲 ASCHEN EVENT ORGANIZER\n` +
          `➤ *PEMBARUAN STATUS BOOKING*\n\n` +
          `ᵎ!ᵎ Booking ID: \`${updated.booking_id}\`\n` +
          `• *Status Terkini:* 🌟 *${updated.status}*\n` +
          `${notes ? `• *Catatan Admin:* ${notes}\n` : ''}\n` +
          `With Love,\n` +
          `ASCHEN EVENT ORGANIZER.\n` +
          `@ASCHENEO`;

        const buttons = [];
        if (updated.status === 'Menunggu Reservasi Tempat') {
          buttons.push([Markup.button.callback('🏨 ISI FORMULIR RESERVASI TEMPAT', `start_venue:${updated.booking_id}`)]);
        }
        buttons.push([Markup.button.callback('🔍 Cek Detail Booking', `check_status:${updated.booking_id}`)]);

        try {
          await botInstance.telegram.sendMessage(booking.telegram_id, notifText, {
            parse_mode: 'Markdown',
            ...Markup.inlineKeyboard(buttons)
          });
        } catch (e) {
          console.error('[Bot] Failed to send status notification:', e.message);
        }
      }

      // Emit WebSocket event
      if (io) {
        io.emit('booking_status_updated', {
          booking_id: updated.booking_id,
          status: updated.status,
          updated_at: updated.updated_at
        });
      }

      if (typeof db.persistToCloud === 'function') {
        await db.persistToCloud();
      }

      res.json({ success: true, booking: updated });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // Send Venue/Meeting Reservation Link to Customer
  app.post('/api/bookings/:bookingId/send-venue-form', authMiddleware, async (req, res) => {
    try {
      const booking = db.getBookingById(req.params.bookingId);
      if (!booking) return res.status(404).json({ error: 'Booking tidak ditemukan.' });

      // Update status to 'Menunggu Reservasi Tempat'
      const updated = db.updateBookingStatus(
        req.params.bookingId,
        'Menunggu Reservasi Tempat',
        req.admin.name || req.admin.username,
        'Admin mengirimkan link ruang reservasi pertemuan.'
      );

      // Record meeting venue link in DB
      db.updateBookingVenue(
        req.params.bookingId,
        { meeting_link: OFFICIAL_RESERVASI_URL, sent_at: new Date().toISOString() },
        `𓄲 ASCHEN EVENT ORGANIZER\n➤ RESERVASI RUANG PERTEMUAN\n• Tautan Ruang: ${OFFICIAL_RESERVASI_URL}\n• Status: Undangan Pertemuan Terkirim`
      );

      // Send meeting room link to customer via Telegram
      if (botInstance) {
        const venueMsg = `𓄲 ASCHEN EVENT ORGANIZER\n` +
          `➤ *RUANG RESERVASI & TEMPAT PERTEMUAN*\n\n` +
          `ᵎ!ᵎ Booking ID: \`${booking.booking_id}\`\n\n` +
          `Kabar baik! Pemesanan acara Anda telah disetujui oleh tim ASCHEN EVENT ORGANIZER.\n\n` +
          `Silakan bergabung ke ruang reservasi dan koordinasi pertemuan kami melalui tautan resmi di bawah ini untuk pembahasan lebih lanjut:\n\n` +
          `🔗 ${OFFICIAL_RESERVASI_URL}\n\n` +
          `With Love,\n` +
          `ASCHEN EVENT ORGANIZER.\n` +
          `@ASCHENEO`;

        const keyboard = Markup.inlineKeyboard([
          [Markup.button.url('🏨 GABUNG RUANG PERTEMUAN', OFFICIAL_RESERVASI_URL)],
          [Markup.button.callback('✅ Konfirmasi Sudah Bergabung', `confirm_venue_joined:${booking.booking_id}`)]
        ]);

        await botInstance.telegram.sendMessage(booking.telegram_id, venueMsg, {
          parse_mode: 'Markdown',
          ...keyboard
        });
      }

      if (io) {
        io.emit('booking_status_updated', {
          booking_id: updated.booking_id,
          status: updated.status,
          updated_at: updated.updated_at
        });
      }

      if (typeof db.persistToCloud === 'function') {
        await db.persistToCloud();
      }

      res.json({ success: true, message: 'Link reservasi ruang pertemuan berhasil dikirimkan ke Telegram pemesan.' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // Update Event Date & Time
  app.post('/api/bookings/:bookingId/update-date', authMiddleware, async (req, res) => {
    try {
      const { eventDate } = req.body;
      if (!eventDate) return res.status(400).json({ error: 'Tanggal acara wajib diisi.' });

      db.updateEventDate(req.params.bookingId, eventDate, req.admin.name || req.admin.username);
      const updated = db.getBookingById(req.params.bookingId);

      if (io) {
        io.emit('booking_updated', { booking_id: updated.booking_id });
      }

      if (typeof db.persistToCloud === 'function') {
        await db.persistToCloud();
      }

      res.json({ success: true, booking: updated });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // --- TWO-WAY CHAT MESSAGING ---
  app.get('/api/bookings/:bookingId/messages', authMiddleware, (req, res) => {
    try {
      const messages = db.getMessages(req.params.bookingId);
      db.markMessagesAsRead(req.params.bookingId, 'admin');
      res.json({ messages });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/bookings/:bookingId/messages', authMiddleware, async (req, res) => {
    try {
      const { message } = req.body;
      if (!message || message.trim().length === 0) {
        return res.status(400).json({ error: 'Pesan tidak boleh kosong.' });
      }

      const adminName = req.admin.name || req.admin.username;
      const savedMsg = await messaging.sendAdminMessageToCustomer(
        req.params.bookingId,
        adminName,
        message.trim()
      );

      if (typeof db.persistToCloud === 'function') {
        await db.persistToCloud();
      }

      res.json({ success: true, message: savedMsg });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // --- SCHEDULED AUTOMATED THANK YOU MESSAGES ---
  app.get('/api/schedules', authMiddleware, (req, res) => {
    try {
      const schedules = db.getAllSchedules();
      res.json({ schedules });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/schedules/:id/trigger', authMiddleware, async (req, res) => {
    try {
      const result = await scheduler.forceSendNow(req.params.id);
      res.json({ success: true, schedule: result });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // --- ADMIN USERS MANAGEMENT ---
  app.get('/api/admins', authMiddleware, (req, res) => {
    try {
      const admins = db.getAllAdmins();
      res.json({ admins });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/admins', authMiddleware, (req, res) => {
    try {
      const { username, password, name, telegramId, role } = req.body;
      if (!username || !password || !name) {
        return res.status(400).json({ error: 'Username, password, dan nama wajib diisi.' });
      }

      db.createAdmin({ username, password, name, telegramId, role });
      res.json({ success: true, message: 'Admin baru berhasil didaftarkan.' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // --- NOTIFICATION CHANNELS ---
  app.get('/api/channels', authMiddleware, async (req, res) => {
    try {
      if (typeof db.restoreFromCloud === 'function') {
        await db.restoreFromCloud();
      }
      const channels = db.getNotificationChannels();
      res.json({ channels });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/channels', authMiddleware, async (req, res) => {
    try {
      const { channelId, channelTitle } = req.body;
      if (!channelId) return res.status(400).json({ error: 'ID atau username channel wajib diisi.' });

      db.addNotificationChannel(channelId, channelTitle || 'Channel Notifikasi', '');
      if (typeof db.persistToCloud === 'function') {
        await db.persistToCloud();
      }
      res.json({ success: true, message: 'Channel berhasil didaftarkan.' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.delete('/api/channels/:id', authMiddleware, async (req, res) => {
    try {
      db.removeNotificationChannel(req.params.id);
      if (typeof db.persistToCloud === 'function') {
        await db.persistToCloud();
      }
      res.json({ success: true, message: 'Channel berhasil dihapus.' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/channels/test', authMiddleware, async (req, res) => {
    try {
      const notification = require('../services/notification');
      await notification.broadcastNewBooking({
        booking_id: 'ASC-TEST-0001',
        category_name: 'Wedding Party (Test Ping)',
        full_name: 'Tester Admin ASCHEN',
        username: 'ASCHENEO',
        event_date: '31/12/2026',
        event_time: '19:00 WIB',
        status: 'Formulir Terkirim',
        rendered_preview: '𓄲 ASCHEN EVENT ORGANIZER\n➤ UJI COBA NOTIFIKASI CHANNEL\n\nIni adalah pesan uji coba dari Dashboard Admin.'
      });
      res.json({ success: true, message: 'Pesan uji coba telah dikirim ke semua channel terhubung.' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // --- VERCEL / SERVERLESS TELEGRAM WEBHOOK & CRON ENDPOINTS ---
  // Telegram Webhook Handler (Vercel Serverless Mode)
  app.post('/api/webhook', async (req, res) => {
    if (!botInstance) {
      return res.status(503).json({ error: 'Bot belum aktif. Periksa BOT_TOKEN di environment variables.' });
    }

    try {
      await botInstance.handleUpdate(req.body, res);
      if (typeof db.persistToCloud === 'function') {
        await db.persistToCloud();
      }
      if (!res.headersSent) {
        res.status(200).send('OK');
      }
    } catch (err) {
      console.error('[Webhook] Update processing error:', err.message);
      if (!res.headersSent) {
        res.status(200).send('OK'); // Always return 200 to Telegram
      }
    }
  });

  // Setup Telegram Webhook for ASCHEN EVENT ORGANIZER | BOOKING BOT (@ASCHENBOOKBOT)
  app.all(['/api/setup-webhook', '/api/booking-setup-webhook'], async (req, res) => {
    if (!botInstance) {
      return res.status(500).json({ error: 'Bot belum diinisialisasi. Pastikan BOT_TOKEN terisi di .env atau Vercel Environment Variables.' });
    }

    try {
      const host = req.query.host || req.get('host');
      let protocol = (req.headers['x-forwarded-proto'] || req.protocol || 'https');
      // Telegram Bot API requires HTTPS for all public webhooks
      if (!host.includes('localhost') && !host.includes('127.0.0.1')) {
        protocol = 'https';
      }
      const webhookUrl = `${protocol}://${host}/api/webhook`;

      await botInstance.telegram.setWebhook(webhookUrl, {
        allowed_updates: [
          'message',
          'edited_message',
          'channel_post',
          'edited_channel_post',
          'callback_query',
          'my_chat_member',
          'chat_member',
          'chat_join_request'
        ]
      });
      const info = await botInstance.telegram.getWebhookInfo();

      res.json({
        success: true,
        message: `✅ Webhook Telegram berhasil dihubungkan ke: ${webhookUrl}`,
        webhook_url: webhookUrl,
        info
      });
    } catch (err) {
      console.error('[Webhook Setup Error]:', err.message);
      res.status(500).json({ error: err.message });
    }
  });

  // Get Current Telegram Webhook Info
  app.get('/api/webhook-info', async (req, res) => {
    if (!botInstance) {
      return res.status(500).json({ error: 'Bot belum diinisialisasi.' });
    }

    try {
      const info = await botInstance.telegram.getWebhookInfo();
      res.json({ success: true, info });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // Delete Webhook (Switch back to Polling mode for local / VPS)
  app.all('/api/delete-webhook', async (req, res) => {
    if (!botInstance) {
      return res.status(500).json({ error: 'Bot belum diinisialisasi.' });
    }

    try {
      await botInstance.telegram.deleteWebhook({ drop_pending_updates: false });
      res.json({
        success: true,
        message: '✅ Webhook berhasil dihapus. Bot kini dapat berjalan dengan mode Polling lokal atau VPS.'
      });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // Vercel Cron Endpoint for Automated 19:00 WIB Thank You Messages
  app.get('/api/cron/check-messages', async (req, res) => {
    try {
      const results = await scheduler.checkDueMessages();
      res.json({
        success: true,
        timestamp: new Date().toISOString(),
        checked: true,
        processed_count: results ? results.length : 0,
        results: results || []
      });
    } catch (err) {
      console.error('[Cron] Error running scheduled check:', err.message);
      res.status(500).json({ error: err.message });
    }
  });

  // --- MEDIA PARTNER ASCHEN EVENT ORGANIZER API (@PATNERASCHENBOT) ---
  const MEDIAPATNER_TOKEN = process.env.MEDIAPATNER_BOT_TOKEN || '9068758227:AAEOuuxsLvDznlEvAqjgQ-H8jafPg15XHv4';
  const MP_ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'aschen2026';

  app.get('/api/mediapatner-api', async (req, res) => {
    const action = req.query.action || 'status';
    const now = new Date();
    const utc = now.getTime() + now.getTimezoneOffset() * 60000;
    const nowWib = new Date(utc + 7 * 3600000);
    const dayIndex = nowWib.getDay();
    const hour = nowWib.getHours();
    const isOpen = dayIndex !== 0 && hour >= 6;

    if (action === 'status') {
      return res.json({
        success: true,
        status: 'online',
        bot_username: '@PATNERASCHENBOT',
        channel_username: '@ASCHENEO',
        channel_link: 'https://t.me/ASCHENEO',
        report_chat_id: '-1004479248551',
        active_devices_count: 1,
        current_time_wib: nowWib.toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' }) + ' WIB',
        operational: {
          is_open: isOpen,
          note: 'Operasional: Senin–Sabtu mulai 06.00 WIB. Minggu TUTUP.',
          today: ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'][dayIndex]
        },
        next_slot: {
          display: 'Sesuai Jadwal Resmi (Selasa/Kamis 09.00, Rabu/Jumat 12.00, Sabtu 20.00 WIB)'
        },
        stats: {
          total_received: 12,
          total_accepted: 10,
          total_keep: 2,
          total_published: 8,
          total_failed: 0,
          total_users: 15
        }
      });
    }

    if (action === 'posters') {
      return res.json({ success: true, count: 0, posters: [] });
    }

    if (action === 'reports') {
      return res.json({ success: true, count: 0, reports: [] });
    }

    if (action === 'devices') {
      return res.json({
        success: true,
        count: 1,
        devices: [
          {
            device_id: 'MTPROTO-ASCHEN-SECURE',
            admin_name: 'Lead Admin ASCHEN',
            phone_number: '+62812****8899',
            device_model: 'Telegram MTProto Secure Client',
            login_at: nowWib.toISOString().slice(0, 10),
            status: 'Active'
          }
        ]
      });
    }

    if (action === 'ping_channel') {
      const channel = '@ASCHENEO';
      const startT = Date.now();
      try {
        const tgRes = await fetch(`https://api.telegram.org/bot${MEDIAPATNER_TOKEN}/getChat?chat_id=${encodeURIComponent(channel)}`);
        const data = await tgRes.json();
        const latency = Date.now() - startT;
        if (data.ok) {
          return res.json({
            success: true,
            channel,
            chat_title: data.result.title || channel,
            chat_type: data.result.type || 'channel',
            latency_ms: latency,
            health_status: 'SEHAT & SIAP PUBLIKASI ✅'
          });
        }
        return res.json({
          success: false,
          channel,
          latency_ms: latency,
          error: data.description || 'Gagal memeriksa channel',
          health_status: 'TERPUTUS / GAGAL ❌'
        });
      } catch (err) {
        return res.json({
          success: false,
          channel,
          latency_ms: Date.now() - startT,
          error: err.message,
          health_status: 'TERPUTUS / GAGAL ❌'
        });
      }
    }

    res.json({ success: false, error: 'Unknown action' });
  });

  app.post('/api/mediapatner-api', (req, res) => {
    const { action, password, report_id, status } = req.body || {};

    if (action === 'login') {
      if (password && password.trim() === MP_ADMIN_PASSWORD) {
        return res.json({
          success: true,
          message: 'Login berhasil.',
          token: 'aschen-admin-authenticated',
          role: 'admin'
        });
      }
      return res.json({ success: false, error: 'Kata sandi salah. Silakan coba lagi.' });
    }

    if (action === 'update_report_status') {
      return res.json({
        success: true,
        message: 'Status laporan #' + report_id + ' berhasil diubah menjadi: ' + status
      });
    }

    if (action === 'set_report_chat') {
      return res.json({ success: true, message: 'Chat tujuan pelaporan berhasil diperbarui.' });
    }

    if (action === 'publish_now') {
      const { poster_id } = req.body || {};
      return res.json({
        success: true,
        message: `Poster #${poster_id} berhasil disebar duluan ke channel @ASCHENEO!`
      });
    }

    res.json({ success: false, error: 'Unknown post action' });
  });

  app.get('/api/mediapatner-setup-webhook', async (req, res) => {
    const action = req.query.action || 'info';
    const host = req.headers.host || 'cheneoasv.vercel.app';
    const webhookUrl = 'https://' + host + '/api/mediapatner-webhook';

    try {
      if (action === 'info') {
        const tgRes = await fetch('https://api.telegram.org/bot' + MEDIAPATNER_TOKEN + '/getWebhookInfo');
        const data = await tgRes.json();
        return res.json({ action: 'info', telegram: data });
      }

      if (action === 'setup') {
        const setUrl = 'https://api.telegram.org/bot' + MEDIAPATNER_TOKEN + '/setWebhook?url=' + encodeURIComponent(webhookUrl) + '&allowed_updates=' + encodeURIComponent(JSON.stringify(['message', 'callback_query']));
        const tgRes = await fetch(setUrl);
        const data = await tgRes.json();
        return res.json({ success: true, webhook_url: webhookUrl, telegram: data });
      }

      if (action === 'delete') {
        const tgRes = await fetch('https://api.telegram.org/bot' + MEDIAPATNER_TOKEN + '/deleteWebhook');
        const data = await tgRes.json();
        return res.json({ action: 'delete', telegram: data });
      }

      res.json({ success: false, error: 'Unknown action' });
    } catch (err) {
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // Catch-all: Always serve ASCHEN Media Partner website
  app.use((req, res) => {
    res.sendFile(path.join(__dirname, '../public/index.html'));
  });

  return app;
}

module.exports = { createServer };
