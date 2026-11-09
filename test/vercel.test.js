/**
 * ASCHEN EVENT ORGANIZER - Vercel Serverless & Webhook Verification Suite
 */

const assert = require('assert');
const http = require('http');

// Set test environment
process.env.DB_PATH = './data/test_vercel.db';
process.env.PORT = '3002';

const { createServer } = require('../src/server/app');
const db = require('../src/database/db');

// Mock bot for serverless test
const mockBot = {
  telegram: {
    webhookInfo: { url: '', pending_update_count: 0 },
    async getWebhookInfo() {
      return this.webhookInfo;
    },
    async setWebhook(url) {
      this.webhookInfo.url = url;
      return true;
    },
    async deleteWebhook() {
      this.webhookInfo.url = '';
      return true;
    },
    async sendMessage(chatId, text, opts) {
      return { message_id: 999, chat: { id: chatId }, text };
    }
  },
  async handleUpdate(update, res) {
    if (!res.headersSent) {
      res.status(200).send('MOCK_UPDATE_OK');
    }
  }
};

async function runVercelTests() {
  console.log('-------------------------------------------------------------');
  console.log('⚡ TESTING VERCEL SERVERLESS ENDPOINTS & WEBHOOK INTEGRATION');
  console.log('-------------------------------------------------------------');

  const app = createServer(mockBot, null);
  const server = http.createServer(app);

  await new Promise(resolve => server.listen(3002, resolve));

  try {
    // Test 1: Cron Check Messages
    console.log('Test 1: GET /api/cron/check-messages (Vercel Cron)...');
    const cronRes = await fetch('http://localhost:3002/api/cron/check-messages');
    assert.strictEqual(cronRes.status, 200);
    const cronData = await cronRes.json();
    assert.strictEqual(cronData.success, true);
    assert.strictEqual(cronData.checked, true);
    console.log('  ✅ Vercel Cron endpoint verified.');

    // Test 2: Webhook Info before setup
    console.log('Test 2: GET /api/webhook-info (Initial state)...');
    const infoRes = await fetch('http://localhost:3002/api/webhook-info');
    assert.strictEqual(infoRes.status, 200);
    const infoData = await infoRes.json();
    assert.strictEqual(infoData.success, true);
    assert.strictEqual(infoData.info.url, '');
    console.log('  ✅ Webhook Info verified.');

    // Test 3: Setup Webhook with custom host
    console.log('Test 3: GET /api/setup-webhook?host=aschenbooking.my.id...');
    const setupRes = await fetch('http://localhost:3002/api/setup-webhook?host=aschenbooking.my.id');
    assert.strictEqual(setupRes.status, 200);
    const setupData = await setupRes.json();
    assert.strictEqual(setupData.success, true);
    assert(setupData.webhook_url.includes('aschenbooking.my.id/api/webhook'));
    console.log('  ✅ Setup Webhook registered custom domain: ' + setupData.webhook_url);

    // Test 4: Webhook Info after setup
    console.log('Test 4: Verify Webhook Info reflects custom domain...');
    const infoRes2 = await fetch('http://localhost:3002/api/webhook-info');
    const infoData2 = await infoRes2.json();
    assert.strictEqual(infoData2.info.url, 'https://aschenbooking.my.id/api/webhook');
    console.log('  ✅ Webhook Info reflects new custom domain.');

    // Test 5: Post Telegram Update to Webhook
    console.log('Test 5: POST /api/webhook incoming telegram payload...');
    const hookRes = await fetch('http://localhost:3002/api/webhook', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ update_id: 123456, message: { text: '/start' } })
    });
    assert.strictEqual(hookRes.status, 200);
    const hookText = await hookRes.text();
    assert.strictEqual(hookText, 'MOCK_UPDATE_OK');
    console.log('  ✅ Webhook successfully accepted update and returned 200 OK.');

    // Test 6: Delete Webhook
    console.log('Test 6: GET /api/delete-webhook (switching to polling)...');
    const delRes = await fetch('http://localhost:3002/api/delete-webhook');
    assert.strictEqual(delRes.status, 200);
    const delData = await delRes.json();
    assert.strictEqual(delData.success, true);

    const infoRes3 = await fetch('http://localhost:3002/api/webhook-info');
    const infoData3 = await infoRes3.json();
    assert.strictEqual(infoData3.info.url, '');
    console.log('  ✅ Webhook deleted cleanly.');

    console.log('-------------------------------------------------------------');
    console.log('🎉 ALL VERCEL & WEBHOOK TESTS PASSED! (6/6)');
    console.log('-------------------------------------------------------------');
  } finally {
    server.close();
  }
}

runVercelTests().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
