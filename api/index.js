/**
 * Vercel Serverless Handler
 * ASCHEN EVENT ORGANIZER — BOOKING BOT & ADMIN DASHBOARD
 */

const { initBot } = require('../src/bot/bot');
const { createServer } = require('../src/server/app');

// In serverless, WebSockets are disabled; Bot is handled via /api/webhook
const bot = initBot(null);
const app = createServer(bot, null);

module.exports = app;
