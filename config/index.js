require('dotenv').config();
const path = require('path');

const isVercel = !!(process.env.VERCEL || process.env.VERCEL_ENV || process.env.NOW_REGION);

// Dedicated Booking Bot Token (@ASCHENBOOKBOT)
const bookingBotToken = process.env.BOOKING_BOT_TOKEN || process.env.BOT_TOKEN || '9136985528:AAHUyI2NMUWWU8JuT3ogDTMFCUNkcW3pdjs';

module.exports = {
  IS_VERCEL: isVercel,
  BOT_TOKEN: bookingBotToken,
  BOOKING_BOT_TOKEN: bookingBotToken,
  MEDIAPATNER_BOT_TOKEN: process.env.MEDIAPATNER_BOT_TOKEN || '9068758227:AAEOuuxsLvDznlEvAqjgQ-H8jafPg15XHv4',
  PORT: parseInt(process.env.PORT, 10) || 3000,
  ADMIN_TELEGRAM_IDS: (process.env.ADMIN_TELEGRAM_IDS || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
    .map(Number),
  ADMIN_DEFAULT_USER: process.env.ADMIN_DEFAULT_USER || 'admin',
  ADMIN_DEFAULT_PASS: process.env.ADMIN_DEFAULT_PASS || 'aschen2026',
  JWT_SECRET: process.env.JWT_SECRET || 'aschen-super-secret-key-2026',
  DB_PATH: process.env.DB_PATH || (isVercel ? '/tmp/aschen_booking.db' : './data/aschen_booking.db'),
  OFFICIAL_GS_URL: 'https://t.me/ASCHENOFFICIAL/7',
  OFFICIAL_JADWAL_URL: 'https://t.me/JadwalAschen/2',
  OFFICIAL_RESERVASI_URL: 'https://t.me/+NHhPUT9PqVw5YzIx',
  OFFICIAL_CHANNEL: '@ASCHENOFFICIAL',
  OFFICIAL_USERNAME: '@ASCHENEO',
  NOTIFICATION_CHANNEL_ID: process.env.NOTIFICATION_CHANNEL_ID || '-1003955381888',
  TIMEZONE: 'Asia/Jakarta' // WIB (UTC+7)
};
