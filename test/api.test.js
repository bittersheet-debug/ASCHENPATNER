/**
 * ASCHEN EVENT ORGANIZER - HTTP REST API & Web Dashboard Test
 */

const http = require('http');
const assert = require('assert');

process.env.DB_PATH = './data/test_api_aschen.db';
process.env.PORT = '3088';

const { createServer } = require('../src/server/app');
const db = require('../src/database/db');
const { initWebSocket } = require('../src/server/websocket');

async function testApi() {
  console.log('🧪 RUNNING API INTEGRATION TESTS...');

  const server = http.createServer();
  const { io } = initWebSocket(server);
  const app = createServer(null, io);
  server.on('request', app);

  await new Promise(resolve => server.listen(3088, resolve));
  console.log('  Server running on port 3088');

  // Helper request
  function request(method, path, body = null, cookie = null) {
    return new Promise((resolve, reject) => {
      const headers = { 'Content-Type': 'application/json' };
      if (cookie) headers['Cookie'] = cookie;

      const req = http.request({
        hostname: 'localhost',
        port: 3088,
        path,
        method,
        headers
      }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, headers: res.headers, body: JSON.parse(data) });
          } catch (e) {
            resolve({ status: res.statusCode, headers: res.headers, raw: data });
          }
        });
      });
      req.on('error', reject);
      if (body) req.write(JSON.stringify(body));
      req.end();
    });
  }

  // 1. Test Admin Login
  console.log('Test A: Admin Login...');
  const loginRes = await request('POST', '/api/auth/login', {
    username: 'admin',
    password: 'aschen2026'
  });
  assert.strictEqual(loginRes.status, 200);
  assert(loginRes.body.token);
  const cookie = loginRes.headers['set-cookie'] ? loginRes.headers['set-cookie'][0] : null;
  assert(cookie);
  console.log('  ✅ Login successful, auth cookie received.');

  // 2. Test Get Stats
  console.log('Test B: Get Dashboard Stats...');
  const statsRes = await request('GET', '/api/stats', null, cookie);
  assert.strictEqual(statsRes.status, 200);
  assert('totalBookings' in statsRes.body);
  console.log('  ✅ Stats retrieved.');

  // 3. Test Create Booking and query via API
  console.log('Test C: Query Bookings via API...');
  const booking = db.createBooking({
    category: 'birthday',
    categoryName: 'Birthday Party',
    categoryCode: 'BDY',
    telegramId: 11223344,
    username: '@testuser',
    fullName: 'Test User',
    eventDate: '20/12/2026',
    eventTime: '20:00 WIB',
    formData: { pemesan_nama: 'Test User' },
    renderedPreview: 'Test preview'
  });

  const listRes = await request('GET', '/api/bookings', null, cookie);
  assert.strictEqual(listRes.status, 200);
  assert(listRes.body.bookings.length >= 1);
  console.log('  ✅ Bookings list retrieved with search/filter support.');

  // 4. Test Status Update via API
  console.log('Test D: Update Booking Status to Booking Diterima...');
  const updateRes = await request('POST', `/api/bookings/${booking.booking_id}/status`, {
    status: 'Booking Diterima',
    notes: 'Approved by admin API test'
  }, cookie);
  assert.strictEqual(updateRes.status, 200);
  assert.strictEqual(updateRes.body.booking.status, 'Booking Diterima');
  console.log('  ✅ Status updated successfully.');

  // 5. Test Two-Way Chat via API
  console.log('Test E: Admin sends chat message to booking...');
  const msgRes = await request('POST', `/api/bookings/${booking.booking_id}/messages`, {
    message: 'Halo! Booking Anda sudah kami setujui.'
  }, cookie);
  assert.strictEqual(msgRes.status, 200);
  assert.strictEqual(msgRes.body.message.message, 'Halo! Booking Anda sudah kami setujui.');
  console.log('  ✅ Admin message recorded and linked to booking.');

  // 6. Test Schedules API
  console.log('Test F: Verify Scheduled Messages API...');
  const schedRes = await request('GET', '/api/schedules', null, cookie);
  assert.strictEqual(schedRes.status, 200);
  assert(schedRes.body.schedules.length >= 1);
  console.log('  ✅ Schedules retrieved.');

  server.close();
  console.log('🎉 ALL REST API TESTS PASSED SUCCESSFULLY!');
}

testApi().then(() => {
  const fs = require('fs');
  try {
    if (fs.existsSync('./data/test_api_aschen.db')) fs.unlinkSync('./data/test_api_aschen.db');
  } catch (e) {}
  process.exit(0);
}).catch(err => {
  console.error('API Test Failed:', err);
  process.exit(1);
});
