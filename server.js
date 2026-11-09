/**
 * ASCHEN EVENT ORGANIZER - MAIN APPLICATION ENTRY POINT
 * Combines Telegram Bot, Express REST API, WebSockets, and Automated Scheduler.
 */

const http = require('http');
const { PORT } = require('./config');
const { initBot } = require('./src/bot/bot');
const { initWebSocket } = require('./src/server/websocket');
const { createServer } = require('./src/server/app');
const scheduler = require('./src/services/scheduler');
const db = require('./src/database/db');

async function bootstrap() {
  console.log('----------------------------------------------------');
  console.log('  𓄲 ASCHEN EVENT ORGANIZER — BOOKING BOT SYSTEM');
  console.log('----------------------------------------------------');

  // 1. Create HTTP server dummy first for WebSockets
  const tempApp = require('express')();
  const server = http.createServer(tempApp);

  // 2. Initialize WebSocket Server
  const { io } = initWebSocket(server);

  // 3. Initialize Telegram Bot
  const bot = initBot(io);

  // 4. Mount full Express application with Bot & IO injected
  const app = createServer(bot, io);
  server.removeAllListeners('request');
  server.on('request', app);

  // 5. Start Automated Scheduler
  scheduler.start();

  // 6. Listen on specified PORT
  server.listen(PORT, () => {
    console.log(`✨ [Server] Admin Dashboard berjalan di: http://localhost:${PORT}`);
    console.log(`👑 [Auth] Akun default admin: username=admin, password=aschen2026`);
    console.log(`💎 [Brand] Identitas ASCHEN: 𓄲, ➤, ᵎ!ᵎ, @ASCHENEO`);
    console.log(`🎤 [Guest Star] Link resmi: https://t.me/ASCHENOFFICIAL/7`);
    console.log('----------------------------------------------------');
  });

  // Handle graceful shutdowns
  const shutdown = () => {
    console.log('\n[System] Menghentikan sistem ASCHEN...');
    scheduler.stop();
    server.close(() => {
      console.log('[System] Server ditutup.');
      process.exit(0);
    });
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

bootstrap().catch(err => {
  console.error('Fatal initialization error:', err);
  process.exit(1);
});
