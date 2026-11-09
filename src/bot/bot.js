/**
 * ASCHEN EVENT ORGANIZER - Telegraf Bot Instance
 */

const { Telegraf } = require('telegraf');
const { BOT_TOKEN, IS_VERCEL } = require('../../config');
const { registerHandlers } = require('./handlers');
const scheduler = require('../services/scheduler');
const messaging = require('../services/messaging');
const notification = require('../services/notification');

let bot = null;

function initBot(io) {
  if (!BOT_TOKEN || BOT_TOKEN.trim() === '' || BOT_TOKEN === 'YOUR_TELEGRAM_BOT_TOKEN_HERE') {
    console.warn('⚠️ [Bot] BOT_TOKEN belum diset di file .env.');
    console.warn('ℹ️ [Bot] Sistem berjalan dalam mode server & web dashboard. Silakan masukkan BOT_TOKEN valid di .env untuk mengaktifkan bot Telegram.');
    return null;
  }

  try {
    bot = new Telegraf(BOT_TOKEN);

    // Register all event organizer bot handlers
    registerHandlers(bot, io);

    // Provide bot instance to scheduler, messaging, and notification services
    scheduler.setBot(bot);
    messaging.init(bot, io);
    notification.setBot(bot);

    if (IS_VERCEL) {
      console.log('⚡ [Bot] Berjalan di lingkungan VERCEL Serverless (mode Webhook aktif).');
      return bot;
    }

    // Launch bot via polling for local/VPS
    bot.launch().then(() => {
      console.log('🤖 [Bot] Telegram Bot ASCHEN EVENT ORGANIZER | BOOKING BOT berhasil online! (Polling Mode)');
    }).catch(err => {
      console.error('❌ [Bot] Gagal menghubungkan ke Telegram Bot API:', err.message);
    });

    // Graceful stop
    process.once('SIGINT', () => bot && bot.stop('SIGINT'));
    process.once('SIGTERM', () => bot && bot.stop('SIGTERM'));

    return bot;
  } catch (err) {
    console.error('❌ [Bot] Error inisialisasi Telegraf:', err);
    return null;
  }
}

function getBot() {
  return bot;
}

module.exports = { initBot, getBot };
