/**
 * ASCHEN EVENT ORGANIZER - Channel Notification Service
 * Broadcasts new booking submissions and updates to connected Telegram channels/groups.
 */

const db = require('../database/db');
const { Markup } = require('telegraf');

class NotificationService {
  constructor() {
    this.bot = null;
  }

  setBot(bot) {
    this.bot = bot;
  }

  async broadcastNewBooking(booking) {
    if (!this.bot) {
      console.warn('[Notification] Bot instance not set. Skipping channel broadcast.');
      return;
    }

    // 1. Gather all target channels
    const channels = db.getNotificationChannels();
    const targetChannelIds = new Set();

    // From DB
    channels.forEach(c => targetChannelIds.add(c.channel_id));

    // From environment variable if set
    if (process.env.NOTIFICATION_CHANNEL_ID) {
      process.env.NOTIFICATION_CHANNEL_ID.split(',').forEach(id => {
        const trimmed = id.trim();
        if (trimmed) targetChannelIds.add(trimmed);
      });
    }

    if (targetChannelIds.size === 0) {
      console.log('[Notification] Belum ada channel notifikasi yang terdaftar.');
      return;
    }

    // 2. Compose notification message
    const alertText = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *NOTIFIKASI PEMESANAN BARU MASUK!*\n\n` +
      `ᵎ!ᵎ Telah masuk formulir booking baru ke sistem ASCHEN:\n\n` +
      `• *Booking ID:* \`${booking.booking_id}\`\n` +
      `• *Kategori:* ${booking.category_name}\n` +
      `• *Pemesan:* ${booking.full_name} (@${booking.username || 'user'})\n` +
      `• *Tanggal Acara:* ${booking.event_date}\n` +
      `• *Waktu Acara:* ${booking.event_time}\n` +
      `• *Status:* ⏳ *${booking.status}*\n\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `➤ *DETAIL FORMULIR LENGKAP:*\n\n` +
      `${booking.rendered_preview}\n` +
      `━━━━━━━━━━━━━━━━━━━━\n\n` +
      `With Love,\n` +
      `ASCHEN EVENT ORGANIZER.\n` +
      `@ASCHENEO`;

    const buttons = [];
    if (booking.username) {
      buttons.push([Markup.button.url('💬 Hubungi Pemesan di Telegram', `https://t.me/${booking.username.replace('@', '')}`)]);
    } else if (booking.telegram_id) {
      buttons.push([Markup.button.url('💬 Hubungi Pemesan', `tg://user?id=${booking.telegram_id}`)]);
    }

    const keyboard = Markup.inlineKeyboard(buttons);

    // 3. Send to each channel
    for (const channelId of targetChannelIds) {
      try {
        await this.bot.telegram.sendMessage(channelId, alertText, {
          parse_mode: 'Markdown',
          ...keyboard
        });
        console.log(`[Notification] Notifikasi booking ${booking.booking_id} terkirim ke channel ${channelId}`);
      } catch (err) {
        console.error(`[Notification] Gagal mengirim ke channel ${channelId}:`, err.message);
      }
    }
  }

  // Confirmation when bot is added to a new channel
  async sendChannelWelcome(channelId, channelTitle) {
    if (!this.bot) return;

    const welcomeMsg = `𓄲 ASCHEN EVENT ORGANIZER | NOTIFIKASI BOT\n\n` +
      `ᵎ!ᵎ Saluran *"${channelTitle}"* telah berhasil terhubung ke sistem ASCHEN BOOKING BOT.\n\n` +
      `Setiap ada pemesanan acara baru dari pelanggan, formulir dan rincian acara akan otomatis diteruskan ke saluran ini secara *real-time*.\n\n` +
      `With Love,\n` +
      `ASCHEN EVENT ORGANIZER.\n` +
      `@ASCHENEO`;

    try {
      await this.bot.telegram.sendMessage(channelId, welcomeMsg, {
        parse_mode: 'Markdown'
      });
    } catch (e) {
      console.error(`[Notification] Gagal mengirim pesan sambutan ke channel ${channelId}:`, e.message);
    }
  }
}

module.exports = new NotificationService();
