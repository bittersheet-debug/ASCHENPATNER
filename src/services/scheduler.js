/**
 * ASCHEN EVENT ORGANIZER - Automated Thank You Scheduler Service
 * Sends automated Thank You message on confirmed event date at 19:00 WIB (UTC+7).
 * Completely restart-safe via SQLite persistence.
 */

const db = require('../database/db');
const { THANK_YOU_MESSAGE, OFFICIAL_USERNAME } = require('../../config/templates');

class SchedulerService {
  constructor() {
    this.bot = null;
    this.intervalId = null;
    this.isRunning = false;
  }

  setBot(botInstance) {
    this.bot = botInstance;
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    console.log('[Scheduler] Background worker started. Checking every 30 seconds for scheduled 19:00 WIB messages...');

    // Run immediate check, then interval
    this.checkDueMessages();
    this.intervalId = setInterval(() => {
      this.checkDueMessages();
    }, 30 * 1000);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
    console.log('[Scheduler] Background worker stopped.');
  }

  async checkDueMessages() {
    const results = [];
    try {
      const dueList = db.getDueScheduledMessages();
      if (!dueList || dueList.length === 0) return results;

      console.log(`[Scheduler] Found ${dueList.length} due scheduled message(s) to send.`);

      for (const item of dueList) {
        const res = await this.sendScheduledMessage(item);
        if (res) results.push(res);
      }
    } catch (err) {
      console.error('[Scheduler] Error checking due messages:', err);
    }
    return results;
  }

  async sendScheduledMessage(item) {
    if (!this.bot) {
      console.warn(`[Scheduler] Bot instance not ready. Skipping message for ${item.booking_id}`);
      return { booking_id: item.booking_id, status: 'skipped', reason: 'bot_not_ready' };
    }

    try {
      const text = item.message_text || THANK_YOU_MESSAGE;
      await this.bot.telegram.sendMessage(item.telegram_id, text, {
        parse_mode: 'Markdown'
      });

      db.markScheduleSent(item.id);
      console.log(`[Scheduler] Successfully sent Thank You message to Telegram ID ${item.telegram_id} for Booking ${item.booking_id}`);

      // Log status history
      db.updateBookingStatus(item.booking_id, 'Booking Selesai', 'Sistem Otomatis', 'Pesan ucapan terima kasih 19:00 WIB telah berhasil dikirimkan.');

      return { booking_id: item.booking_id, status: 'sent' };
    } catch (err) {
      const errorMsg = err.message || String(err);
      console.error(`[Scheduler] Failed to send scheduled message for ${item.booking_id}:`, errorMsg);
      db.markScheduleFailed(item.id, errorMsg);

      // Notify admin about failure
      this.notifyAdminsFailure(item, errorMsg);

      return { booking_id: item.booking_id, status: 'failed', error: errorMsg };
    }
  }

  async notifyAdminsFailure(item, errorMsg) {
    const notice = `⚠️ *PERINGATAN SISTEM — GAGAL MENGIRIM UCAPAN TERIMA KASIH*\n\n` +
      `• Booking ID: \`${item.booking_id}\`\n` +
      `• Telegram ID: \`${item.telegram_id}\`\n` +
      `• Tanggal Acara: ${item.event_date}\n` +
      `• Error: \`${errorMsg}\`\n\n` +
      `Kemungkinan pengguna telah memblokir bot atau akun Telegram tidak aktif.`;

    // Attempt to notify all registered admins
    const admins = db.getAllAdmins();
    for (const adm of admins) {
      if (adm.telegram_id && this.bot) {
        try {
          await this.bot.telegram.sendMessage(adm.telegram_id, notice, { parse_mode: 'Markdown' });
        } catch (e) {
          // ignore admin delivery failures
        }
      }
    }
  }

  // Force send now for testing or manual trigger from dashboard
  async forceSendNow(scheduleId) {
    const item = db.db.prepare('SELECT * FROM scheduled_messages WHERE id = ?').get(scheduleId);
    if (!item) throw new Error('Schedule tidak ditemukan.');
    await this.sendScheduledMessage(item);
    return db.db.prepare('SELECT * FROM scheduled_messages WHERE id = ?').get(scheduleId);
  }
}

module.exports = new SchedulerService();
