/**
 * ASCHEN EVENT ORGANIZER - Bot Commands and Callback Handlers
 * Handles /start, /status, /mybookings, /admin, category selection,
 * status checks, chat mode, and integrates wizard engines.
 */

const { Markup } = require('telegraf');
const db = require('../database/db');
const { CATEGORIES, OFFICIAL_CHANNEL, OFFICIAL_USERNAME, BOOKING_STATUSES, OFFICIAL_RESERVASI_URL } = require('../../config/templates');
const {
  startBookingSession,
  handleUserAnswer,
  handleOptionCallback,
  handleBackStep,
  handleSkipStep,
  handleCancelForm,
  showFormPreview,
  showEditMenu,
  jumpToEditField,
  submitBookingForm
} = require('./conversation');
const {
  startVenueSession,
  handleVenueAnswer,
  handleVenueBack,
  handleVenueSkip,
  handleVenueCancel,
  showVenuePreview,
  submitVenueForm
} = require('./venue_wizard');
const messaging = require('../services/messaging');
const notification = require('../services/notification');

function registerHandlers(bot, io) {

  // Welcome Menu Keyboard (Initial clean landing view)
  function getWelcomeKeyboard() {
    return Markup.inlineKeyboard([
      [
        Markup.button.callback('✨ PILIH FORMAT BOOKING', 'menu:select_format')
      ],
      [
        Markup.button.callback('🔍 Cek Status Booking', 'menu:my_bookings'),
        Markup.button.url('📅 Jadwal Acara', 'https://t.me/JadwalAschen/2')
      ],
      [
        Markup.button.url('🎤 Daftar Guest Star', 'https://t.me/ASCHENOFFICIAL/7'),
        Markup.button.callback('ℹ️ Tentang ASCHEN', 'menu:about')
      ]
    ]);
  }

  // Format Categories Keyboard (Only shown when user clicks "PILIH FORMAT BOOKING")
  function getFormatCategoriesKeyboard() {
    return Markup.inlineKeyboard([
      [
        Markup.button.callback('💍 Wedding Party', 'cat:wedding'),
        Markup.button.callback('🎂 Birthday Party', 'cat:birthday')
      ],
      [
        Markup.button.callback('🥂 Engagement Party', 'cat:engagement'),
        Markup.button.callback('👨‍👩‍👦 Mensive Fam/Couple', 'cat:mensive_family_couple')
      ],
      [
        Markup.button.callback('👑 Mensive Channel VVIP', 'cat:mensive_channel_vvip'),
        Markup.button.callback('🎓 Promnight/Graduation', 'cat:promnight_graduation')
      ],
      [
        Markup.button.callback('🔙 Kembali ke Menu Utama', 'menu:main')
      ]
    ]);
  }

  function getWelcomeText() {
    return `𓄲 ASCHEN EVENT ORGANIZER | BOOKING BOT\n` +
      `ᵎ!ᵎ Selamat datang di sistem pemesanan resmi ASCHEN EVENT ORGANIZER.\n\n` +
      `Wujudkan setiap momen istimewa Anda dengan konsep eksklusif, terorganisir, dan berkelas bersama kami.\n\n` +
      `Silakan tekan tombol *PILIH FORMAT BOOKING* di bawah untuk melihat pilihan formulir pemesanan:`;
  }

  function getFormatSelectionText() {
    return `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *PILIHAN FORMAT BOOKING EVENT*\n\n` +
      `ᵎ!ᵎ Silakan pilih salah satu kategori acara yang ingin Anda pesan untuk memulai pengisian formulir:`;
  }

  // /start command
  bot.command('start', async (ctx) => {
    // Clear any abandoned session
    db.clearUserSession(ctx.from.id);
    await ctx.reply(getWelcomeText(), {
      parse_mode: 'Markdown',
      ...getWelcomeKeyboard()
    });
  });

  // /help command
  bot.command('help', async (ctx) => {
    const text = `𓄲 ASCHEN EVENT ORGANIZER — BANTUAN\n\n` +
      `• /start — Membuka menu utama & daftar kategori booking\n` +
      `• /status — Memeriksa status booking Anda\n` +
      `• /batal — Membatalkan pengisian formulir yang sedang berjalan\n\n` +
      `Butuh bantuan langsung? Hubungi tim kami di ${OFFICIAL_USERNAME} atau saluran resmi ${OFFICIAL_CHANNEL}.`;
    await ctx.reply(text, { parse_mode: 'Markdown' });
  });

  // /status command
  bot.command('status', async (ctx) => {
    const args = ctx.message.text.split(' ').slice(1);
    if (args.length > 0) {
      return sendBookingDetail(ctx, args[0].trim());
    }
    return sendUserBookingsList(ctx);
  });

  // /batal command
  bot.command('batal', async (ctx) => {
    db.clearUserSession(ctx.from.id);
    await ctx.reply('❌ Sesi aktif telah dibatalkan.', {
      ...Markup.inlineKeyboard([[Markup.button.callback('📋 Buka Menu Utama', 'menu:main')]])
    });
  });

  // /admin command (for authorized admins)
  bot.command('admin', async (ctx) => {
    const telegramId = ctx.from.id;
    const admin = db.db.prepare('SELECT * FROM admins WHERE telegram_id = ?').get(telegramId);
    
    // Also check config ADMIN_TELEGRAM_IDS
    const { ADMIN_TELEGRAM_IDS, PORT } = require('../../config');
    const isConfigAdmin = ADMIN_TELEGRAM_IDS.includes(telegramId);

    if (!admin && !isConfigAdmin) {
      return ctx.reply('⚠️ Akses terbatas. Perintah ini hanya untuk Admin resmi ASCHEN.');
    }

    const stats = db.getDashboardStats();
    const text = `𓄲 ASCHEN EVENT ORGANIZER — PANEL ADMIN\n\n` +
      `Halo, *${ctx.from.first_name}*! Berikut ringkasan sistem:\n\n` +
      `• Total Booking Masuk: *${stats.totalBookings}*\n` +
      `• Menunggu Proses: *${stats.pending}*\n` +
      `• Booking Diterima/Dikonfirmasi: *${stats.confirmed}*\n` +
      `• Acara Selesai: *${stats.completed}*\n\n` +
      `Buka Web Dashboard Admin untuk fitur lengkap (balas pesan, kirim reservasi tempat, ubah status, kelola jadwal ucapan otomatis).`;

    const keyboard = Markup.inlineKeyboard([
      [Markup.button.callback('📋 Lihat Booking Terbaru', 'admin:recent_bookings')],
      [Markup.button.callback('🔄 Refresh Data', 'admin:refresh')]
    ]);

    await ctx.reply(text, { parse_mode: 'Markdown', ...keyboard });
  });

  // /setchannel command (can be triggered in channel/group)
  bot.command('setchannel', async (ctx) => {
    const chat = ctx.chat;
    if (chat.type === 'private') {
      return ctx.reply('⚠️ Perintah /setchannel harus dijalankan di dalam Channel atau Group yang ingin dijadikan saluran penerima notifikasi booking.');
    }
    db.addNotificationChannel(chat.id, chat.title, chat.username);
    await ctx.reply(`𓄲 ASCHEN EVENT ORGANIZER\n\n✅ Saluran *"${chat.title || 'Channel'}"* telah resmi didaftarkan sebagai saluran penerima notifikasi booking masuk!`, {
      parse_mode: 'Markdown'
    });
  });

  // When bot is added to a channel or group as admin
  bot.on('my_chat_member', async (ctx) => {
    try {
      const update = ctx.myChatMember;
      const status = update.new_chat_member.status;
      const chat = ctx.chat;

      if (['administrator', 'member'].includes(status) && ['channel', 'supergroup', 'group'].includes(chat.type)) {
        db.addNotificationChannel(chat.id, chat.title, chat.username);
        console.log(`[Bot] Ditambahkan ke channel/group notifikasi: ${chat.title || chat.id} (${chat.id})`);
        await notification.sendChannelWelcome(chat.id, chat.title || 'Saluran ASCHEN');
      } else if (['left', 'kicked'].includes(status)) {
        db.removeNotificationChannel(chat.id);
        console.log(`[Bot] Dikeluarkan dari channel/group notifikasi: ${chat.id}`);
      }
    } catch (err) {
      console.error('[Bot] Error on my_chat_member:', err);
    }
  });

  // Channel post listener (captures channel when any post is published in channel)
  bot.on('channel_post', async (ctx) => {
    try {
      const chat = ctx.chat;
      if (chat && ['channel', 'supergroup', 'group'].includes(chat.type)) {
        db.addNotificationChannel(chat.id, chat.title, chat.username);
        console.log(`[Bot] Saluran terdeteksi dari channel_post: ${chat.title || chat.id} (${chat.id})`);
        const text = (ctx.channelPost && ctx.channelPost.text) ? ctx.channelPost.text.toLowerCase() : '';
        if (text.includes('test') || text.includes('ping') || text.includes('halo') || text.includes('notif')) {
          await notification.sendChannelWelcome(chat.id, chat.title || 'Saluran Notifikasi ASCHEN');
        }
      }
    } catch (e) {
      console.error('[Bot] Error on channel_post:', e.message);
    }
  });

  // Menu Callbacks
  bot.action('menu:main', async (ctx) => {
    db.clearUserSession(ctx.from.id);
    await ctx.answerCbQuery();
    try {
      await ctx.editMessageText(getWelcomeText(), {
        parse_mode: 'Markdown',
        ...getWelcomeKeyboard()
      });
    } catch (e) {
      await ctx.reply(getWelcomeText(), {
        parse_mode: 'Markdown',
        ...getWelcomeKeyboard()
      });
    }
  });

  // Format selection callback (shows 6 category buttons)
  bot.action('menu:select_format', async (ctx) => {
    db.clearUserSession(ctx.from.id);
    await ctx.answerCbQuery();
    try {
      await ctx.editMessageText(getFormatSelectionText(), {
        parse_mode: 'Markdown',
        ...getFormatCategoriesKeyboard()
      });
    } catch (e) {
      await ctx.reply(getFormatSelectionText(), {
        parse_mode: 'Markdown',
        ...getFormatCategoriesKeyboard()
      });
    }
  });

  bot.action('menu:about', async (ctx) => {
    await ctx.answerCbQuery();
    const text = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *TENTANG KAMI*\n\n` +
      `ASCHEN EVENT ORGANIZER adalah layanan perencana dan penyelenggara acara profesional dengan konsep elegan, rapi, dan tak terlupakan di Telegram.\n\n` +
      `• *Channel Resmi:* ${OFFICIAL_CHANNEL}\n` +
      `• *Official Contact:* ${OFFICIAL_USERNAME}\n` +
      `• *Daftar Jadwal Acara:* https://t.me/JadwalAschen/2\n` +
      `• *Daftar Guest Star:* https://t.me/ASCHENOFFICIAL/7\n\n` +
      `With Love,\n` +
      `ASCHEN EVENT ORGANIZER.`;

    const keyboard = Markup.inlineKeyboard([
      [Markup.button.url('📢 Kunjungi Channel Resmi', 'https://t.me/ASCHENOFFICIAL')],
      [Markup.button.url('📅 Cek Jadwal Acara ASCHEN', 'https://t.me/JadwalAschen/2')],
      [Markup.button.callback('🔙 Kembali ke Menu Utama', 'menu:main')]
    ]);

    await ctx.editMessageText(text, { parse_mode: 'Markdown', ...keyboard });
  });

  bot.action('menu:my_bookings', async (ctx) => {
    await ctx.answerCbQuery();
    return sendUserBookingsList(ctx);
  });

  // Category Selection Callbacks
  bot.action(/^cat:(.+)$/, async (ctx) => {
    const categoryKey = ctx.match[1];
    await ctx.answerCbQuery();
    return startBookingSession(ctx, categoryKey);
  });

  // Form Navigation Callbacks
  bot.action('form:back', async (ctx) => {
    return handleBackStep(ctx);
  });

  bot.action('form:skip', async (ctx) => {
    return handleSkipStep(ctx);
  });

  bot.action('form:cancel', async (ctx) => {
    return handleCancelForm(ctx);
  });

  bot.action('form:edit_menu', async (ctx) => {
    return showEditMenu(ctx);
  });

  bot.action('form:preview', async (ctx) => {
    const session = db.getUserSession(ctx.from.id);
    if (!session) return ctx.answerCbQuery('Sesi tidak ditemukan.');
    await ctx.answerCbQuery();
    return showFormPreview(ctx, session);
  });

  bot.action(/^edit_field:(\d+)$/, async (ctx) => {
    const fieldIndex = ctx.match[1];
    return jumpToEditField(ctx, fieldIndex);
  });

  bot.action('form:submit', async (ctx) => {
    return submitBookingForm(ctx, io);
  });

  // Predefined Option selection
  bot.action(/^opt:(.+)$/, async (ctx) => {
    const value = ctx.match[1];
    return handleOptionCallback(ctx, value);
  });

  // Venue Reservation Callbacks
  bot.action(/^start_venue:(.+)$/, async (ctx) => {
    const bookingId = ctx.match[1];
    await ctx.answerCbQuery();
    return ctx.reply(`𓄲 ASCHEN EVENT ORGANIZER\n➤ *RUANG RESERVASI & TEMPAT PERTEMUAN*\n\nSilakan bergabung ke ruang reservasi dan koordinasi pertemuan kami:\n🔗 ${OFFICIAL_RESERVASI_URL}`, {
      parse_mode: 'Markdown',
      ...Markup.inlineKeyboard([
        [Markup.button.url('🏨 GABUNG RUANG PERTEMUAN', OFFICIAL_RESERVASI_URL)],
        [Markup.button.callback('✅ Konfirmasi Sudah Bergabung', `confirm_venue_joined:${bookingId}`)]
      ])
    });
  });

  // Confirm joining meeting room
  bot.action(/^confirm_venue_joined:(.+)$/, async (ctx) => {
    const bookingId = ctx.match[1];
    await ctx.answerCbQuery('Kehadiran Anda telah dicatat!');

    const updated = db.updateBookingStatus(
      bookingId,
      'Reservasi Tempat Tercatat',
      'Pelanggan',
      'Pelanggan telah mengonfirmasi bergabung ke ruang reservasi pertemuan.'
    );

    const text = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *RESERVASI PERTEMUAN TERCATAT*\n\n` +
      `ᵎ!ᵎ Terkait Booking ID: \`${bookingId}\`\n\n` +
      `Terima kasih telah bergabung di ruang pertemuan kami. Tim ASCHEN akan segera berkoordinasi secara langsung dengan Anda mengenai detail dan persiapan acara.\n\n` +
      `• *Status Terkini:* 🌟 *Reservasi Tempat Tercatat*`;

    const keyboard = Markup.inlineKeyboard([
      [Markup.button.url('🏨 Buka Ruang Pertemuan', OFFICIAL_RESERVASI_URL)],
      [Markup.button.callback('🔍 Cek Status Booking', `check_status:${bookingId}`)],
      [Markup.button.callback('📋 Menu Utama', 'menu:main')]
    ]);

    await ctx.reply(text, { parse_mode: 'Markdown', ...keyboard });

    if (io) {
      io.emit('booking_status_updated', {
        booking_id: bookingId,
        status: 'Reservasi Tempat Tercatat',
        updated_at: updated.updated_at
      });
    }
  });

  bot.action('venue:back', async (ctx) => {
    return handleVenueBack(ctx);
  });

  bot.action('venue:skip', async (ctx) => {
    return handleVenueSkip(ctx);
  });

  bot.action('venue:cancel', async (ctx) => {
    return handleVenueCancel(ctx);
  });

  bot.action('venue:edit', async (ctx) => {
    const session = db.getUserSession(ctx.from.id);
    if (session && session.type === 'venue') {
      session.stepIndex = 0;
      session.editMode = true;
      db.setUserSession(ctx.from.id, session);
      await ctx.answerCbQuery('Mulai perbaikan dari awal.');
      return askCurrentVenueQuestion(ctx, session);
    }
  });

  bot.action('venue:submit', async (ctx) => {
    return submitVenueForm(ctx, io);
  });

  // Status check callback
  bot.action(/^check_status:(.+)$/, async (ctx) => {
    const bookingId = ctx.match[1];
    await ctx.answerCbQuery();
    return sendBookingDetail(ctx, bookingId);
  });

  // Two-way chat: customer initiates message to admin
  bot.action(/^chat_admin:(.+)$/, async (ctx) => {
    const bookingId = ctx.match[1];
    const booking = db.getBookingById(bookingId);
    if (!booking) return ctx.answerCbQuery('Booking tidak ditemukan.');

    // Save session in chat mode
    db.setUserSession(ctx.from.id, {
      type: 'chat',
      bookingId: bookingId
    });

    await ctx.answerCbQuery();
    const text = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *KOMUNIKASI DUA ARAH DENGAN ADMIN*\n` +
      `ᵎ!ᵎ Terhubung dengan Booking ID: \`${bookingId}\`\n\n` +
      `Silakan ketik pertanyaan, konfirmasi, atau informasi tambahan yang ingin Anda sampaikan kepada Admin ASCHEN di bawah ini:\n\n` +
      `_(Ketik pesan Anda dan kirim seperti biasa, atau tekan tombol Batal jika tidak jadi)_`;

    await ctx.reply(text, {
      parse_mode: 'Markdown',
      ...Markup.inlineKeyboard([
        [Markup.button.callback('❌ Batal Kirim Pesan', 'chat:cancel')]
      ])
    });
  });

  bot.action('chat:cancel', async (ctx) => {
    db.clearUserSession(ctx.from.id);
    await ctx.answerCbQuery('Pengiriman pesan dibatalkan.');
    await ctx.reply('Pengiriman pesan dibatalkan.', {
      ...Markup.inlineKeyboard([[Markup.button.callback('📋 Menu Utama', 'menu:main')]])
    });
  });

  // Catch-all text messages handler
  bot.on('text', async (ctx) => {
    const telegramId = ctx.from.id;
    const session = db.getUserSession(telegramId);

    if (!session) {
      // If user typed a text without session, check if it matches a Booking ID (e.g. ASC-...)
      const text = ctx.message.text.trim();
      if (text.startsWith('ASC-')) {
        return sendBookingDetail(ctx, text);
      }
      return ctx.reply(`Halo! Silakan gunakan menu di bawah untuk memesan event atau memeriksa status booking:`, {
        ...getWelcomeKeyboard()
      });
    }

    // 1. If in booking form wizard
    if (session.type === 'booking') {
      const handled = await handleUserAnswer(ctx, ctx.message.text);
      if (handled) return;
    }

    // 2. If in venue reservation wizard
    if (session.type === 'venue') {
      const handled = await handleVenueAnswer(ctx, ctx.message.text);
      if (handled) return;
    }

    // 3. If in two-way chat mode
    if (session.type === 'chat') {
      const bookingId = session.bookingId;
      const customerName = [ctx.from.first_name, ctx.from.last_name].filter(Boolean).join(' ') || `@${ctx.from.username}`;
      const msgText = ctx.message.text;

      try {
        await messaging.sendCustomerMessageToAdmin(bookingId, customerName, msgText);
        db.clearUserSession(telegramId);

        await ctx.reply(`✅ *Pesan Berhasil Terkirim ke Admin*\n\nPesan Anda terkait Booking ID \`${bookingId}\` telah diteruskan ke Admin ASCHEN. Admin akan segera membalas melalui bot ini.`, {
          parse_mode: 'Markdown',
          ...Markup.inlineKeyboard([
            [Markup.button.callback('🔍 Cek Status Booking', `check_status:${bookingId}`)],
            [Markup.button.callback('📋 Menu Utama', 'menu:main')]
          ])
        });
      } catch (err) {
        console.error('[Chat] Error sending customer message:', err);
        await ctx.reply('⚠️ Terjadi kendala saat mengirim pesan ke admin. Silakan coba lagi.');
      }
      return;
    }
  });

  // Helper: send user bookings list
  async function sendUserBookingsList(ctx) {
    const list = db.getBookingsByTelegramId(ctx.from.id);
    if (!list || list.length === 0) {
      const text = `𓄲 ASCHEN EVENT ORGANIZER\n` +
        `➤ *RIWAYAT BOOKING ANDA*\n\n` +
        `Anda belum memiliki pemesanan aktif. Silakan pilih salah satu kategori di menu utama untuk melakukan pemesanan.`;
      const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('✨ Buat Booking Baru', 'menu:select_format')],
        [Markup.button.callback('🔙 Kembali ke Menu Utama', 'menu:main')]
      ]);

      if (ctx.callbackQuery) {
        return ctx.editMessageText(text, { parse_mode: 'Markdown', ...keyboard });
      }
      return ctx.reply(text, { parse_mode: 'Markdown', ...keyboard });
    }

    let text = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *DAFTAR PEMESANAN ANDA*\n\n` +
      `Ditemukan *${list.length}* pemesanan atas nama Anda. Klik salah satu tombol di bawah untuk melihat detail lengkap:\n`;

    const buttons = list.map(b => {
      const icon = b.status.includes('Diterima') || b.status.includes('Dikonfirmasi') ? '✅' :
                   b.status.includes('Ditolak') || b.status.includes('Dibatalkan') ? '❌' : '⏳';
      return [Markup.button.callback(`${icon} ${b.booking_id} — ${b.category_name}`, `check_status:${b.booking_id}`)];
    });

    buttons.push([Markup.button.callback('🔙 Kembali ke Menu Utama', 'menu:main')]);

    const keyboard = Markup.inlineKeyboard(buttons);

    if (ctx.callbackQuery) {
      return ctx.editMessageText(text, { parse_mode: 'Markdown', ...keyboard });
    }
    return ctx.reply(text, { parse_mode: 'Markdown', ...keyboard });
  }

  // Helper: send booking detail
  async function sendBookingDetail(ctx, bookingId) {
    const booking = db.getBookingById(bookingId);
    if (!booking) {
      const errText = `⚠️ Booking ID \`${bookingId}\` tidak ditemukan di sistem. Harap periksa kembali penulisan ID Anda.`;
      if (ctx.callbackQuery) return ctx.editMessageText(errText, { parse_mode: 'Markdown' });
      return ctx.reply(errText, { parse_mode: 'Markdown' });
    }

    // Security check: Only customer who booked or registered admin can view
    const isOwner = booking.telegram_id === ctx.from.id;
    const isAdmin = db.db.prepare('SELECT id FROM admins WHERE telegram_id = ?').get(ctx.from.id);
    const { ADMIN_TELEGRAM_IDS } = require('../../config');
    const isConfigAdmin = ADMIN_TELEGRAM_IDS.includes(ctx.from.id);

    if (!isOwner && !isAdmin && !isConfigAdmin) {
      const denyText = '⚠️ Anda tidak memiliki otoritas untuk melihat data booking ini.';
      if (ctx.callbackQuery) return ctx.editMessageText(denyText);
      return ctx.reply(denyText);
    }

    const history = db.getStatusHistory(bookingId);
    let historyText = '';
    if (history && history.length > 0) {
      historyText = '\n\n➤ *RIWAYAT STATUS:*\n' + history.map(h => {
        const time = new Date(h.created_at).toLocaleDateString('id-ID', {
          day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        return `• ${time}: *${h.new_status}* (${h.changed_by})${h.notes ? ' — ' + h.notes : ''}`;
      }).join('\n');
    }

    let venueInfo = '';
    if (booking.venue_rendered) {
      venueInfo = `\n\n${booking.venue_rendered}`;
    }

    const detailText = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *DETAIL BOOKING EVENT*\n\n` +
      `• *Booking ID:* \`${booking.booking_id}\`\n` +
      `• *Kategori:* ${booking.category_name}\n` +
      `• *Tanggal Acara:* ${booking.event_date}\n` +
      `• *Waktu Acara:* ${booking.event_time}\n` +
      `• *Status Terkini:* 🌟 *${booking.status}*${historyText}${venueInfo}`;

    const buttons = [];

    // If booking is accepted or in reservation state: show meeting link button
    if (['Menunggu Reservasi Tempat', 'Booking Diterima', 'Reservasi Tempat Tercatat', 'Booking Dikonfirmasi'].includes(booking.status)) {
      buttons.push([Markup.button.url('🏨 GABUNG RUANG PERTEMUAN', OFFICIAL_RESERVASI_URL)]);
      if (booking.status === 'Menunggu Reservasi Tempat') {
        buttons.push([Markup.button.callback('✅ Konfirmasi Sudah Bergabung', `confirm_venue_joined:${booking.booking_id}`)]);
      }
    }

    buttons.push([
      Markup.button.callback('💬 Hubungi Admin', `chat_admin:${booking.booking_id}`),
      Markup.button.callback('🔙 Daftar Booking', 'menu:my_bookings')
    ]);

    buttons.push([Markup.button.callback('📋 Menu Utama', 'menu:main')]);

    const keyboard = Markup.inlineKeyboard(buttons);

    if (ctx.callbackQuery) {
      try {
        return await ctx.editMessageText(detailText, { parse_mode: 'Markdown', ...keyboard });
      } catch (e) {
        return await ctx.reply(detailText, { parse_mode: 'Markdown', ...keyboard });
      }
    }
    return ctx.reply(detailText, { parse_mode: 'Markdown', ...keyboard });
  }

}

module.exports = { registerHandlers };
