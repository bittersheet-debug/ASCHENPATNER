/**
 * ASCHEN EVENT ORGANIZER - Interactive Step-by-Step Form Filling Engine
 * Implements full conversational state machine, question flows, conditional jumps,
 * Guest Star list URL buttons, back/cancel/skip buttons, edit form flow, and preview.
 */

const { Markup } = require('telegraf');
const db = require('../database/db');
const { CATEGORIES, VENUE_TEMPLATE, OFFICIAL_GS_URL, OFFICIAL_JADWAL_URL } = require('../../config/templates');
const notification = require('../services/notification');

// Helper to determine the active questions for a category given current answers
function getActiveQuestions(categoryKey, answers) {
  const category = CATEGORIES[categoryKey];
  if (!category) return [];

  return category.questions.filter(q => {
    if (typeof q.condition === 'function') {
      return q.condition(answers);
    }
    return true;
  });
}

// Start a new booking form session for a user
async function startBookingSession(ctx, categoryKey) {
  const category = CATEGORIES[categoryKey];
  if (!category) {
    return ctx.reply('Kategori tidak valid.');
  }

  const telegramId = ctx.from.id;
  const username = ctx.from.username ? `@${ctx.from.username}` : '';
  const fullName = [ctx.from.first_name, ctx.from.last_name].filter(Boolean).join(' ');

  const session = {
    type: 'booking',
    categoryKey,
    stepIndex: 0,
    answers: {
      pemesan_username: username,
      pemesan_nama: fullName
    },
    editMode: false,
    editFieldId: null
  };

  db.setUserSession(telegramId, session);
  return askCurrentQuestion(ctx, session);
}

// Ask the question at the current step index
async function askCurrentQuestion(ctx, session) {
  const category = CATEGORIES[session.categoryKey];
  const activeQuestions = getActiveQuestions(session.categoryKey, session.answers);

  if (session.stepIndex >= activeQuestions.length) {
    // All questions finished -> Show preview!
    return showFormPreview(ctx, session);
  }

  const currentQ = activeQuestions[session.stepIndex];
  let promptText = currentQ.prompt;

  // Check if this step is the Guest Star selection step or mentions Guest Star
  const inlineButtons = [];

  // If question has predefined options
  if (currentQ.options && currentQ.options.length > 0) {
    currentQ.options.forEach(opt => {
      inlineButtons.push([Markup.button.callback(opt.text, `opt:${opt.value}`)]);
    });
  }

  // Tanggal Acara: Tombol Cek Jadwal Resmi ASCHEN (https://t.me/JadwalAschen/2)
  if (currentQ.id === 'tanggal_acara') {
    inlineButtons.unshift([
      Markup.button.url('📅 LIHAT JADWAL ASCHEN', OFFICIAL_JADWAL_URL)
    ]);
  }

  // Mandatory Requirement 3: When reaching Guest Star & Song section,
  // bot AUTOMATICALLY displays: 🎤 LIHAT DAFTAR GUEST STAR (URL Button pointing to https://t.me/ASCHENOFFICIAL/7)
  // MUST appear BEFORE user fills Guest Star name!
  if (currentQ.isGuestStarIntro || currentQ.id.startsWith('guest_star_')) {
    inlineButtons.unshift([
      Markup.button.url('🎤 LIHAT DAFTAR GUEST STAR', OFFICIAL_GS_URL)
    ]);
  }

  // Navigation action buttons
  const navRow = [];
  if (session.stepIndex > 0) {
    navRow.push(Markup.button.callback('⬅️ KEMBALI', 'form:back'));
  }
  if (currentQ.isOptional) {
    navRow.push(Markup.button.callback('⏩ LEWATI', 'form:skip'));
  }
  navRow.push(Markup.button.callback('❌ BATALKAN', 'form:cancel'));

  inlineButtons.push(navRow);

  // Auto-fill indicator if user already has a default value (like username or name)
  let extraHint = '';
  if (currentQ.id === 'pemesan_username' && session.answers.pemesan_username) {
    extraHint = `\n\n💡 *Terdeteksi:* \`${session.answers.pemesan_username}\`\nKetik username baru atau klik tombol di bawah untuk menggunakan ini:`;
    inlineButtons.unshift([Markup.button.callback(`Gunakan ${session.answers.pemesan_username}`, `opt:${session.answers.pemesan_username}`)]);
  } else if (currentQ.id === 'pemesan_nama' && session.answers.pemesan_nama) {
    extraHint = `\n\n💡 *Terdeteksi:* \`${session.answers.pemesan_nama}\`\nKetik nama baru atau klik tombol untuk menggunakan ini:`;
    inlineButtons.unshift([Markup.button.callback(`Gunakan ${session.answers.pemesan_nama}`, `opt:${session.answers.pemesan_nama}`)]);
  }

  const keyboard = Markup.inlineKeyboard(inlineButtons);

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(`${promptText}${extraHint}`, {
        parse_mode: 'Markdown',
        ...keyboard
      });
    } catch (e) {
      // If message couldn't be edited (e.g. content identical), send new message
      await ctx.reply(`${promptText}${extraHint}`, {
        parse_mode: 'Markdown',
        ...keyboard
      });
    }
  } else {
    await ctx.reply(`${promptText}${extraHint}`, {
      parse_mode: 'Markdown',
      ...keyboard
    });
  }
}

// Handle text answer from user
async function handleUserAnswer(ctx, answerText) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'booking') return false;

  const category = CATEGORIES[session.categoryKey];
  const activeQuestions = getActiveQuestions(session.categoryKey, session.answers);
  const currentQ = activeQuestions[session.stepIndex];

  if (!currentQ) return false;

  const trimmed = answerText.trim();

  // Validate answer if validator defined
  if (typeof currentQ.validate === 'function') {
    const valid = currentQ.validate(trimmed, session.answers);
    if (valid !== true) {
      await ctx.reply(`⚠️ *Input Tidak Valid*\n\n${valid}\n\nSilakan coba lagi:`, {
        parse_mode: 'Markdown'
      });
      return true;
    }
  }

  // Store answer
  session.answers[currentQ.id] = trimmed;

  // If in editMode, return straight to preview
  if (session.editMode) {
    session.editMode = false;
    session.editFieldId = null;
    db.setUserSession(telegramId, session);
    await ctx.reply('✅ Jawaban berhasil diperbarui.');
    return showFormPreview(ctx, session);
  }

  // Advance to next step
  session.stepIndex += 1;
  db.setUserSession(telegramId, session);

  return askCurrentQuestion(ctx, session);
}

// Handle button callback answers (opt:value)
async function handleOptionCallback(ctx, value) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'booking') return false;

  const activeQuestions = getActiveQuestions(session.categoryKey, session.answers);
  const currentQ = activeQuestions[session.stepIndex];
  if (!currentQ) return false;

  session.answers[currentQ.id] = value;

  if (session.editMode) {
    session.editMode = false;
    session.editFieldId = null;
    db.setUserSession(telegramId, session);
    await ctx.answerCbQuery('Perubahan disimpan.');
    return showFormPreview(ctx, session);
  }

  session.stepIndex += 1;
  db.setUserSession(telegramId, session);
  await ctx.answerCbQuery();
  return askCurrentQuestion(ctx, session);
}

// Handle "⬅️ KEMBALI"
async function handleBackStep(ctx) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'booking') return false;

  if (session.stepIndex > 0) {
    session.stepIndex -= 1;
    db.setUserSession(telegramId, session);
    await ctx.answerCbQuery('Kembali ke pertanyaan sebelumnya.');
    return askCurrentQuestion(ctx, session);
  } else {
    await ctx.answerCbQuery('Ini adalah pertanyaan pertama.');
  }
}

// Handle "⏩ LEWATI"
async function handleSkipStep(ctx) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'booking') return false;

  const activeQuestions = getActiveQuestions(session.categoryKey, session.answers);
  const currentQ = activeQuestions[session.stepIndex];

  if (currentQ && currentQ.isOptional) {
    session.answers[currentQ.id] = '-';
    session.stepIndex += 1;
    db.setUserSession(telegramId, session);
    await ctx.answerCbQuery('Dilewati.');
    return askCurrentQuestion(ctx, session);
  } else {
    await ctx.answerCbQuery('Pertanyaan ini wajib diisi.');
  }
}

// Handle "❌ BATALKAN"
async function handleCancelForm(ctx) {
  const telegramId = ctx.from.id;
  db.clearUserSession(telegramId);
  await ctx.answerCbQuery('Pengisian formulir dibatalkan.');
  
  const text = `❌ *PENGISIAN FORMULIR DIBATALKAN*\n\nData yang telah Anda isi telah dihapus. Anda dapat memulai booking baru kapan saja melalui menu utama.`;
  const keyboard = Markup.inlineKeyboard([
    [Markup.button.callback('📋 Buka Menu Utama', 'menu:main')]
  ]);

  if (ctx.callbackQuery) {
    await ctx.editMessageText(text, { parse_mode: 'Markdown', ...keyboard });
  } else {
    await ctx.reply(text, { parse_mode: 'Markdown', ...keyboard });
  }
}

// Show Form Preview
async function showFormPreview(ctx, session) {
  const category = CATEGORIES[session.categoryKey];
  const rendered = category.renderPreview(session.answers);
  session.renderedPreview = rendered;
  db.setUserSession(ctx.from.id, session);

  const keyboard = Markup.inlineKeyboard([
    [
      Markup.button.callback('📩 KIRIM FORMULIR', 'form:submit'),
      Markup.button.callback('✏️ EDIT FORMULIR', 'form:edit_menu')
    ],
    [
      Markup.button.callback('❌ BATALKAN', 'form:cancel')
    ]
  ]);

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(rendered, {
        parse_mode: 'Markdown',
        ...keyboard
      });
    } catch (e) {
      await ctx.reply(rendered, {
        parse_mode: 'Markdown',
        ...keyboard
      });
    }
  } else {
    await ctx.reply(rendered, {
      parse_mode: 'Markdown',
      ...keyboard
    });
  }
}

// Show Edit Menu (allows user to select which field to edit)
async function showEditMenu(ctx) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'booking') return;

  const category = CATEGORIES[session.categoryKey];
  const activeQuestions = getActiveQuestions(session.categoryKey, session.answers);

  const buttons = [];
  activeQuestions.forEach((q, index) => {
    // Only show editable text questions or choices
    buttons.push([Markup.button.callback(`✏️ ${q.label}`, `edit_field:${index}`)]);
  });

  buttons.push([Markup.button.callback('🔙 Kembali ke Preview', 'form:preview')]);

  const text = `𓄲 ASCHEN EVENT ORGANIZER\n➤ *PILIH BAGIAN YANG INGIN DIUBAH*\n\nSilakan tekan tombol di bawah untuk memilih pertanyaan yang ingin Anda perbaiki:`;

  await ctx.answerCbQuery();
  await ctx.editMessageText(text, {
    parse_mode: 'Markdown',
    ...Markup.inlineKeyboard(buttons)
  });
}

// Jump to specific field for editing
async function jumpToEditField(ctx, fieldIndex) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'booking') return;

  session.editMode = true;
  session.stepIndex = parseInt(fieldIndex, 10);
  db.setUserSession(telegramId, session);

  await ctx.answerCbQuery();
  return askCurrentQuestion(ctx, session);
}

// Submit Form (Generates Booking ID, saves to SQLite, schedules Thank You if confirmed, alerts Admin)
async function submitBookingForm(ctx, io) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'booking') return;

  const category = CATEGORIES[session.categoryKey];
  const answers = session.answers;
  const rendered = category.renderPreview(answers);

  try {
    const booking = db.createBooking({
      category: category.id,
      categoryName: category.name,
      categoryCode: category.code,
      telegramId,
      username: ctx.from.username || answers.pemesan_username || '',
      fullName: [ctx.from.first_name, ctx.from.last_name].filter(Boolean).join(' ') || answers.pemesan_nama,
      eventDate: answers.tanggal_acara,
      eventTime: answers.jam_acara,
      formData: answers,
      renderedPreview: rendered
    });

    // Clear session and persist state to cloud storage
    db.clearUserSession(telegramId);
    if (typeof db.persistToCloud === 'function') {
      await db.persistToCloud();
    }
    await ctx.answerCbQuery('Formulir berhasil dikirimkan!');

    const successMsg = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *PEMESANAN BERHASIL DIKIRIMKAN*\n\n` +
      `ᵎ!ᵎ Formulir Anda telah tercatat secara resmi di sistem ASCHEN.\n\n` +
      `• *Booking ID:* \`${booking.booking_id}\`\n` +
      `• *Kategori:* ${booking.category_name}\n` +
      `• *Tanggal Acara:* ${booking.event_date}\n` +
      `• *Jam Acara:* ${booking.event_time}\n` +
      `• *Status:* ⏳ *${booking.status}*\n\n` +
      `Pihak Admin ASCHEN akan segera memeriksa rincian acara Anda. Anda akan menerima pembaruan status dan pesan langsung dari admin melalui bot ini.\n\n` +
      `Simpan *Booking ID* Anda untuk melacak status dan berkomunikasi dengan pihak kami.`;

    const keyboard = Markup.inlineKeyboard([
      [Markup.button.callback('🔍 Cek Status Booking', `check_status:${booking.booking_id}`)],
      [Markup.button.callback('💬 Kirim Pesan ke Admin', `chat_admin:${booking.booking_id}`)],
      [Markup.button.callback('📋 Menu Utama', 'menu:main')]
    ]);

    await ctx.editMessageText(successMsg, {
      parse_mode: 'Markdown',
      ...keyboard
    });

    // Notify WebSocket connected admin dashboards
    if (io) {
      io.emit('new_booking', {
        booking_id: booking.booking_id,
        category: booking.category_name,
        full_name: booking.full_name,
        username: booking.username,
        event_date: booking.event_date,
        created_at: booking.created_at
      });
    }

    // Broadcast booking alert to all connected Telegram Channels
    notification.broadcastNewBooking(booking).catch(e => {
      console.error('[Notification] Error broadcasting booking to channels:', e);
    });

  } catch (err) {
    console.error('[Booking] Error submitting booking:', err);
    await ctx.reply(`⚠️ Terjadi kesalahan saat memproses booking Anda. Silakan hubungi admin.`);
  }
}

module.exports = {
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
};
