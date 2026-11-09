/**
 * ASCHEN EVENT ORGANIZER - Two-Way Messaging Service
 * Connects Admin and Customer securely linked by Booking ID.
 */

const db = require('../database/db');
const { Markup } = require('telegraf');

class MessagingService {
  constructor() {
    this.bot = null;
    this.io = null;
  }

  init(bot, io) {
    this.bot = bot;
    this.io = io;
  }

  // Admin sends message to customer
  async sendAdminMessageToCustomer(bookingId, adminName, messageText) {
    const booking = db.getBookingById(bookingId);
    if (!booking) throw new Error(`Booking ${bookingId} tidak ditemukan.`);

    // 1. Save to database
    const savedMsg = db.addMessage(bookingId, 'admin', adminName, messageText);

    // 2. Send via Telegram Bot to Customer
    if (this.bot) {
      const formatted = `𓄲 ASCHEN EVENT ORGANIZER\n` +
        `➤ *PESAN BARU DARI ADMIN*\n` +
        `ᵎ!ᵎ Terkait Booking ID: \`${bookingId}\`\n\n` +
        `${messageText}\n\n` +
        `With Love,\n` +
        `ASCHEN EVENT ORGANIZER.\n` +
        `@ASCHENEO`;

      const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('💬 Balas Pesan Admin', `chat_admin:${bookingId}`)],
        [Markup.button.callback('🔍 Cek Status Booking', `check_status:${bookingId}`)]
      ]);

      try {
        await this.bot.telegram.sendMessage(booking.telegram_id, formatted, {
          parse_mode: 'Markdown',
          ...keyboard
        });
      } catch (err) {
        console.error(`[Messaging] Failed to deliver admin message to user ${booking.telegram_id}:`, err);
        throw new Error(`Pesan tersimpan di sistem, namun gagal terkirim ke Telegram pemesan: ${err.message}`);
      }
    }

    // 3. Emit to web sockets
    if (this.io) {
      this.io.emit('chat_message', {
        booking_id: bookingId,
        message: savedMsg
      });
    }

    return savedMsg;
  }

  // Customer sends message to admin
  async sendCustomerMessageToAdmin(bookingId, customerName, messageText) {
    const booking = db.getBookingById(bookingId);
    if (!booking) throw new Error(`Booking ${bookingId} tidak ditemukan.`);

    // 1. Save to database
    const savedMsg = db.addMessage(bookingId, 'customer', customerName, messageText);

    // 2. Emit to WebSocket connected admin dashboard
    if (this.io) {
      this.io.emit('chat_message', {
        booking_id: bookingId,
        message: savedMsg
      });
    }

    // 3. Also notify Telegram Admins if configured
    const admins = db.getAllAdmins();
    for (const adm of admins) {
      if (adm.telegram_id && this.bot) {
        try {
          const alertMsg = `💬 *PESAN BARU DARI PELANGGAN*\n\n` +
            `• Booking ID: \`${bookingId}\`\n` +
            `• Pengirim: ${customerName}\n` +
            `• Pesan: "${messageText}"\n\n` +
            `Buka Dashboard Admin untuk membalas atau klik tombol di bawah.`;

          await this.bot.telegram.sendMessage(adm.telegram_id, alertMsg, {
            parse_mode: 'Markdown',
            ...Markup.inlineKeyboard([
              [Markup.button.callback(`Balas Booking ${bookingId}`, `admin_reply:${bookingId}`)]
            ])
          });
        } catch (e) {
          // ignore notification failure
        }
      }
    }

    return savedMsg;
  }
}

module.exports = new MessagingService();
