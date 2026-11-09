/**
 * ASCHEN EVENT ORGANIZER - Venue Reservation Wizard Engine
 * Handles step-by-step filling of venue/location reservation form.
 * Links directly with Booking ID and updates status to "Reservasi Tempat Tercatat".
 */

const { Markup } = require('telegraf');
const db = require('../database/db');
const { VENUE_TEMPLATE } = require('../../config/templates');

async function startVenueSession(ctx, bookingId) {
  const booking = db.getBookingById(bookingId);
  if (!booking) {
    return ctx.reply(`⚠️ Booking dengan ID \`${bookingId}\` tidak ditemukan.`, { parse_mode: 'Markdown' });
  }

  // Authorization check: only owner of booking can fill it
  if (booking.telegram_id !== ctx.from.id) {
    return ctx.reply('⚠️ Anda tidak memiliki akses untuk mengisi reservasi pada booking ini.');
  }

  const session = {
    type: 'venue',
    bookingId: bookingId,
    stepIndex: 0,
    answers: {},
    editMode: false
  };

  db.setUserSession(ctx.from.id, session);
  return askCurrentVenueQuestion(ctx, session);
}

async function askCurrentVenueQuestion(ctx, session) {
  const questions = VENUE_TEMPLATE.questions;
  if (session.stepIndex >= questions.length) {
    return showVenuePreview(ctx, session);
  }

  const currentQ = questions[session.stepIndex];
  const buttons = [];

  const navRow = [];
  if (session.stepIndex > 0) {
    navRow.push(Markup.button.callback('⬅️ KEMBALI', 'venue:back'));
  }
  if (currentQ.isOptional) {
    navRow.push(Markup.button.callback('⏩ LEWATI', 'venue:skip'));
  }
  navRow.push(Markup.button.callback('❌ BATALKAN', 'venue:cancel'));

  buttons.push(navRow);

  const text = `${currentQ.prompt}\n\nᵎ!ᵎ Terkait Booking ID: \`${session.bookingId}\``;
  const keyboard = Markup.inlineKeyboard(buttons);

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(text, { parse_mode: 'Markdown', ...keyboard });
    } catch (e) {
      await ctx.reply(text, { parse_mode: 'Markdown', ...keyboard });
    }
  } else {
    await ctx.reply(text, { parse_mode: 'Markdown', ...keyboard });
  }
}

async function handleVenueAnswer(ctx, answerText) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'venue') return false;

  const questions = VENUE_TEMPLATE.questions;
  const currentQ = questions[session.stepIndex];
  if (!currentQ) return false;

  const trimmed = answerText.trim();
  if (typeof currentQ.validate === 'function') {
    const valid = currentQ.validate(trimmed);
    if (valid !== true) {
      await ctx.reply(`⚠️ *Input Tidak Valid*\n\n${valid}\n\nSilakan coba lagi:`, { parse_mode: 'Markdown' });
      return true;
    }
  }

  session.answers[currentQ.id] = trimmed;

  if (session.editMode) {
    session.editMode = false;
    db.setUserSession(telegramId, session);
    await ctx.reply('✅ Perubahan data tempat disimpan.');
    return showVenuePreview(ctx, session);
  }

  session.stepIndex += 1;
  db.setUserSession(telegramId, session);
  return askCurrentVenueQuestion(ctx, session);
}

async function handleVenueBack(ctx) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'venue') return false;

  if (session.stepIndex > 0) {
    session.stepIndex -= 1;
    db.setUserSession(telegramId, session);
    await ctx.answerCbQuery('Kembali ke pertanyaan sebelumnya.');
    return askCurrentVenueQuestion(ctx, session);
  } else {
    await ctx.answerCbQuery('Ini pertanyaan pertama.');
  }
}

async function handleVenueSkip(ctx) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'venue') return false;

  const currentQ = VENUE_TEMPLATE.questions[session.stepIndex];
  if (currentQ && currentQ.isOptional) {
    session.answers[currentQ.id] = '-';
    session.stepIndex += 1;
    db.setUserSession(telegramId, session);
    await ctx.answerCbQuery('Dilewati.');
    return askCurrentVenueQuestion(ctx, session);
  }
}

async function handleVenueCancel(ctx) {
  const telegramId = ctx.from.id;
  db.clearUserSession(telegramId);
  await ctx.answerCbQuery('Pengisian reservasi tempat dibatalkan.');
  await ctx.reply('❌ Pengisian reservasi tempat dibatalkan. Anda dapat mengisinya kembali kapan saja.', {
    ...Markup.inlineKeyboard([[Markup.button.callback('📋 Menu Utama', 'menu:main')]])
  });
}

async function showVenuePreview(ctx, session) {
  const rendered = VENUE_TEMPLATE.renderPreview(session.answers, session.bookingId);
  session.venueRendered = rendered;
  db.setUserSession(ctx.from.id, session);

  const keyboard = Markup.inlineKeyboard([
    [
      Markup.button.callback('📩 KIRIM RESERVASI TEMPAT', 'venue:submit'),
      Markup.button.callback('✏️ PERBAIKI DATA', 'venue:edit')
    ],
    [
      Markup.button.callback('❌ BATALKAN', 'venue:cancel')
    ]
  ]);

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(rendered, { parse_mode: 'Markdown', ...keyboard });
    } catch (e) {
      await ctx.reply(rendered, { parse_mode: 'Markdown', ...keyboard });
    }
  } else {
    await ctx.reply(rendered, { parse_mode: 'Markdown', ...keyboard });
  }
}

async function submitVenueForm(ctx, io) {
  const telegramId = ctx.from.id;
  const session = db.getUserSession(telegramId);
  if (!session || session.type !== 'venue') return;

  const rendered = VENUE_TEMPLATE.renderPreview(session.answers, session.bookingId);

  try {
    const updated = db.updateBookingVenue(session.bookingId, session.answers, rendered);
    db.clearUserSession(telegramId);

    await ctx.answerCbQuery('Reservasi tempat berhasil dicatat!');

    const msg = `𓄲 ASCHEN EVENT ORGANIZER\n` +
      `➤ *RESERVASI TEMPAT BERHASIL DICATAT*\n\n` +
      `ᵎ!ᵎ Data reservasi lokasi dan ruangan Anda telah terhubung dengan Booking ID \`${session.bookingId}\`.\n\n` +
      `• *Status Terkini:* ✅ *Reservasi Tempat Tercatat*\n\n` +
      `Tim ASCHEN akan melakukan koordinasi dan persiapan teknis lokasi sesuai formulir yang Anda kirimkan.`;

    const keyboard = Markup.inlineKeyboard([
      [Markup.button.callback('🔍 Cek Status Booking', `check_status:${session.bookingId}`)],
      [Markup.button.callback('💬 Kirim Pesan ke Admin', `chat_admin:${session.bookingId}`)],
      [Markup.button.callback('📋 Menu Utama', 'menu:main')]
    ]);

    await ctx.editMessageText(msg, { parse_mode: 'Markdown', ...keyboard });

    // Notify WebSocket connected admin dashboard
    if (io) {
      io.emit('venue_submitted', {
        booking_id: session.bookingId,
        venue_name: session.answers.nama_venue,
        updated_at: updated.updated_at
      });
    }

  } catch (err) {
    console.error('[Venue] Error saving venue form:', err);
    await ctx.reply('⚠️ Terjadi kendala saat menyimpan reservasi tempat.');
  }
}

module.exports = {
  startVenueSession,
  handleVenueAnswer,
  handleVenueBack,
  handleVenueSkip,
  handleVenueCancel,
  showVenuePreview,
  submitVenueForm
};
