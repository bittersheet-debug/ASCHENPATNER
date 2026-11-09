/**
 * ASCHEN EVENT ORGANIZER - Complete System Verification Test Suite
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

// Ensure isolated test DB
process.env.DB_PATH = './data/test_aschen.db';
process.env.PORT = '3001';

const { CATEGORIES, VENUE_TEMPLATE, BOOKING_STATUSES, THANK_YOU_MESSAGE, OFFICIAL_GS_URL, OFFICIAL_JADWAL_URL, OFFICIAL_RESERVASI_URL } = require('../config/templates');
const db = require('../src/database/db');
const scheduler = require('../src/services/scheduler');

async function runTests() {
  console.log('-------------------------------------------------------------');
  console.log('🧪 RUNNING ASCHEN EVENT ORGANIZER SYSTEM VERIFICATION SUITE');
  console.log('-------------------------------------------------------------');

  // Test 1: Category Count and Structure
  console.log('Test 1: Verifying 6 Official Booking Categories...');
  const catKeys = Object.keys(CATEGORIES);
  assert.strictEqual(catKeys.length, 6, 'Should have exactly 6 categories');
  assert.deepStrictEqual(catKeys, [
    'wedding',
    'birthday',
    'engagement',
    'mensive_family_couple',
    'mensive_channel_vvip',
    'promnight_graduation'
  ]);
  console.log('  ✅ 6 Categories verified.');

  // Test 2: Guest Star Limits
  console.log('Test 2: Verifying Guest Star limits and Official URL...');
  assert.strictEqual(CATEGORIES.wedding.maxGuestStars, 2);
  assert.strictEqual(CATEGORIES.birthday.maxGuestStars, 2);
  assert.strictEqual(CATEGORIES.engagement.maxGuestStars, 2);
  assert.strictEqual(CATEGORIES.mensive_family_couple.maxGuestStars, 2);
  assert.strictEqual(CATEGORIES.mensive_channel_vvip.maxGuestStars, 2);
  assert.strictEqual(CATEGORIES.promnight_graduation.maxGuestStars, 3);
  assert.strictEqual(OFFICIAL_GS_URL, 'https://t.me/ASCHENOFFICIAL/7');
  assert.strictEqual(OFFICIAL_JADWAL_URL, 'https://t.me/JadwalAschen/2');
  assert.strictEqual(OFFICIAL_RESERVASI_URL, 'https://t.me/+NHhPUT9PqVw5YzIx');
  console.log('  ✅ Guest star limits, Official URLs (Guest Star, Jadwal, Reservasi) verified.');

  // Test 3: Official 9 Statuses
  console.log('Test 3: Verifying 9 Official Booking Statuses...');
  assert.strictEqual(BOOKING_STATUSES.length, 9);
  assert.strictEqual(BOOKING_STATUSES[0], 'Formulir Terkirim');
  assert.strictEqual(BOOKING_STATUSES[1], 'Menunggu Balasan Admin');
  assert.strictEqual(BOOKING_STATUSES[2], 'Booking Diterima');
  assert.strictEqual(BOOKING_STATUSES[3], 'Booking Ditolak');
  assert.strictEqual(BOOKING_STATUSES[4], 'Menunggu Reservasi Tempat');
  assert.strictEqual(BOOKING_STATUSES[5], 'Reservasi Tempat Tercatat');
  assert.strictEqual(BOOKING_STATUSES[6], 'Booking Dikonfirmasi');
  assert.strictEqual(BOOKING_STATUSES[7], 'Booking Selesai');
  assert.strictEqual(BOOKING_STATUSES[8], 'Booking Dibatalkan');
  console.log('  ✅ All 9 exact official statuses verified.');

  // Test 4: Thank You Message Content
  console.log('Test 4: Verifying Automated Thank You Message text...');
  assert(THANK_YOU_MESSAGE.includes('𓄲 ASCHEN EVENT ORGANIZER'));
  assert(THANK_YOU_MESSAGE.includes('Terima kasih telah memilih dan mempercayakan momen spesial Anda'));
  assert(THANK_YOU_MESSAGE.includes('With Love,\nASCHEN EVENT ORGANIZER.'));
  console.log('  ✅ Thank You message template verified.');

  // Test 5: Form Rendering for Wedding Party
  console.log('Test 5: Verifying Wedding Party Form Preview Rendering...');
  const weddingAnswers = {
    pemesan_username: '@eliasm',
    pemesan_nama: 'Elias Maurits',
    mempelai_pria: 'Bryan (@bryan)',
    mempelai_wanita: 'Valerie (@valerie)',
    tanggal_acara: '25/12/2026',
    jam_acara: '19:00 WIB',
    konsep_tema: 'Royal White Elegance',
    dress_code: 'Black Tie & White Gown',
    guest_star_count: '2',
    guest_star_1: 'Staridol A',
    lagu_guest_star_1: 'Perfect - Ed Sheeran',
    guest_star_2: 'Staridol B',
    lagu_guest_star_2: 'Until I Found You',
    rundown_request: 'Sesi lempar bunga dan games pasangan',
    catatan_tambahan: 'Harap siapkan backstage khusus'
  };
  const renderedWed = CATEGORIES.wedding.renderPreview(weddingAnswers);
  assert(renderedWed.includes('𓄲 ASCHEN EVENT ORGANIZER'));
  assert(renderedWed.includes('FORMULIR PEMESANAN — WEDDING PARTY'));
  assert(renderedWed.includes('Bryan (@bryan)'));
  assert(renderedWed.includes('Staridol A'));
  assert(renderedWed.includes('Staridol B'));
  assert(renderedWed.includes('@ASCHENEO'));
  console.log('  ✅ Wedding Party preview rendering verified.');

  // Test 6: Form Rendering for Promnight / Graduation (with 3 Guest Stars)
  console.log('Test 6: Verifying Promnight / Graduation with 3 Guest Stars...');
  const promAnswers = {
    pemesan_username: '@ketuapanitia',
    nama_instansi: 'SMA Negeri 1 Jakarta',
    nama_angkatan: 'Asteria Batch 26',
    tanggal_acara: '15/06/2026',
    jam_acara: '18:30 WIB',
    konsep_tema: 'A Night Under The Stars',
    dress_code: 'Glamorous Evening',
    guest_star_count: '3',
    guest_star_1: 'Staridol 1',
    lagu_guest_star_1: 'Song 1',
    guest_star_2: 'Staridol 2',
    lagu_guest_star_2: 'Song 2',
    guest_star_3: 'Staridol 3',
    lagu_guest_star_3: 'Song 3',
    request_penghargaan: 'Penobatan Prom King & Queen',
    catatan_tambahan: '-'
  };
  const renderedProm = CATEGORIES.promnight_graduation.renderPreview(promAnswers);
  assert(renderedProm.includes('Staridol 1'));
  assert(renderedProm.includes('Staridol 2'));
  assert(renderedProm.includes('Staridol 3'));
  assert(!renderedProm.includes('CATATAN TAMBAHAN')); // Optional empty omitted cleanly!
  console.log('  ✅ Promnight 3 guest stars & optional omitted field verified.');

  // Test 7: Database Booking Creation & Booking ID Generation
  console.log('Test 7: Verifying Database booking creation & unique ID...');
  const created = db.createBooking({
    category: 'wedding',
    categoryName: 'Wedding Party',
    categoryCode: 'WED',
    telegramId: 987654321,
    username: '@eliasm',
    fullName: 'Elias Maurits',
    eventDate: '25/12/2026',
    eventTime: '19:00 WIB',
    formData: weddingAnswers,
    renderedPreview: renderedWed
  });

  assert(created.booking_id.startsWith('ASC-WED-'));
  assert.strictEqual(created.status, 'Formulir Terkirim');
  assert.strictEqual(created.telegram_id, 987654321);
  console.log(`  ✅ Booking created with ID: ${created.booking_id}`);

  // Test 8: Status History Audit Trail
  console.log('Test 8: Verifying Status History & Audit Trail...');
  const history1 = db.getStatusHistory(created.booking_id);
  assert.strictEqual(history1.length, 1);
  assert.strictEqual(history1[0].new_status, 'Formulir Terkirim');

  // Update status to 'Booking Diterima'
  const updatedStatus = db.updateBookingStatus(created.booking_id, 'Booking Diterima', 'Admin Elias', 'Pemesanan disetujui');
  assert.strictEqual(updatedStatus.status, 'Booking Diterima');

  const history2 = db.getStatusHistory(created.booking_id);
  assert.strictEqual(history2.length, 2);
  assert.strictEqual(history2[1].old_status, 'Formulir Terkirim');
  assert.strictEqual(history2[1].new_status, 'Booking Diterima');
  assert.strictEqual(history2[1].changed_by, 'Admin Elias');
  console.log('  ✅ Status audit trail logged cleanly.');

  // Test 9: Scheduled Message for 19:00 WIB on Event Date
  console.log('Test 9: Verifying Automated 19:00 WIB Scheduler DB record...');
  const scheduleRow = db.db.prepare('SELECT * FROM scheduled_messages WHERE booking_id = ?').get(created.booking_id);
  assert(scheduleRow, 'Schedule row should exist');
  assert.strictEqual(scheduleRow.status, 'pending');
  assert.strictEqual(scheduleRow.event_date, '25/12/2026');
  // 25 Dec 2026 19:00 WIB is 12:00 UTC
  assert(scheduleRow.scheduled_at.startsWith('2026-12-25T12:00:00'));
  console.log(`  ✅ Scheduled at: ${scheduleRow.scheduled_at} (19:00 WIB).`);

  // Test 10: Venue Reservation Submission
  console.log('Test 10: Verifying Venue Reservation flow...');
  const venueAnswers = {
    nama_venue: 'The Grand Ballroom ASCHEN',
    alamat_lokasi: 'https://t.me/ASCHEN_BALLROOM',
    estimasi_tamu: '150 Undangan',
    konsep_dekorasi_tempat: 'White Floral Luxury with Crystal Chandelier',
    fasilitas_request: 'Sound System 10000W, Bot Music, Backstage VIP',
    pic_venue: 'Mr. David (@david_venue)',
    catatan_venue: 'Akses dibuka 1 jam sebelum acara'
  };
  const venueRendered = VENUE_TEMPLATE.renderPreview(venueAnswers, created.booking_id);
  const updatedVenue = db.updateBookingVenue(created.booking_id, venueAnswers, venueRendered);

  assert.strictEqual(updatedVenue.status, 'Reservasi Tempat Tercatat');
  assert(updatedVenue.venue_data.nama_venue, 'The Grand Ballroom ASCHEN');
  assert(updatedVenue.venue_rendered.includes('The Grand Ballroom ASCHEN'));

  const history3 = db.getStatusHistory(created.booking_id);
  assert.strictEqual(history3[history3.length - 1].new_status, 'Reservasi Tempat Tercatat');
  console.log('  ✅ Venue reservation saved & status updated to "Reservasi Tempat Tercatat".');

  // Test 11: Two-Way Chat Messaging
  console.log('Test 11: Verifying Two-Way Chat between Customer and Admin...');
  const msgFromCustomer = db.addMessage(created.booking_id, 'customer', 'Elias Maurits', 'Halo admin, apakah bisa menambah 1 lagu lagi?');
  assert.strictEqual(msgFromCustomer.sender_type, 'customer');

  const msgFromAdmin = db.addMessage(created.booking_id, 'admin', 'Admin Elias', 'Halo! Tentu bisa, silakan sampaikan judul lagunya.');
  assert.strictEqual(msgFromAdmin.sender_type, 'admin');

  const messages = db.getMessages(created.booking_id);
  assert.strictEqual(messages.length, 2);
  assert.strictEqual(messages[0].message, 'Halo admin, apakah bisa menambah 1 lagu lagi?');
  assert.strictEqual(messages[1].message, 'Halo! Tentu bisa, silakan sampaikan judul lagunya.');
  console.log('  ✅ Two-way chat verified and isolated to booking ID.');

  // Test 12: Admin User Auth & Dashboard Stats
  console.log('Test 12: Verifying Admin Authentication & Dashboard Stats...');
  const admin = db.getAdminByUsername('admin');
  assert(admin);
  assert(db.verifyAdminPassword('aschen2026', admin.password_hash));

  const stats = db.getDashboardStats();
  assert(stats.totalBookings >= 1);
  console.log('  ✅ Admin credentials and stats verified.');

  // Test 13: Notification Channel Management
  console.log('Test 13: Verifying Channel Notification registration & storage...');
  db.addNotificationChannel('-1001987654321', 'ASCHEN Official Channel', 'ASCHENOFFICIAL');
  const channels = db.getNotificationChannels();
  assert(channels.length >= 1);
  assert.strictEqual(channels[0].channel_id, '-1001987654321');
  assert.strictEqual(channels[0].channel_title, 'ASCHEN Official Channel');

  db.removeNotificationChannel('-1001987654321');
  const channelsAfter = db.getNotificationChannels();
  assert.strictEqual(channelsAfter.length, 0);
  console.log('  ✅ Channel notification registration and removal verified.');

  console.log('-------------------------------------------------------------');
  console.log('🎉 ALL SYSTEM TESTS PASSED SUCCESSFULLY! (13/13)');
  console.log('-------------------------------------------------------------');
}

runTests().then(() => {
  // Clean test DB
  try {
    if (fs.existsSync('./data/test_aschen.db')) {
      fs.unlinkSync('./data/test_aschen.db');
    }
  } catch (e) {}
  process.exit(0);
}).catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
