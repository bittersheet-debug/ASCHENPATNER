/**
 * ASCHEN EVENT ORGANIZER - Booking Bot System Templates & Configurations
 * Official Visual Identity: 𓄲, ➤, ᵎ!ᵎ, @ASCHENEO
 */

const { OFFICIAL_GS_URL, OFFICIAL_JADWAL_URL, OFFICIAL_RESERVASI_URL } = require('./index');

const BOOKING_STATUSES = [
  'Formulir Terkirim',
  'Menunggu Balasan Admin',
  'Booking Diterima',
  'Booking Ditolak',
  'Menunggu Reservasi Tempat',
  'Reservasi Tempat Tercatat',
  'Booking Dikonfirmasi',
  'Booking Selesai',
  'Booking Dibatalkan'
];

const THANK_YOU_MESSAGE = 
`𓄲 ASCHEN EVENT ORGANIZER

Terima kasih telah memilih dan mempercayakan momen spesial Anda kepada ASCHEN EVENT ORGANIZER.

Merupakan suatu kehormatan bagi kami untuk menjadi bagian dari hari istimewa Anda.

Semoga kebahagiaan, kenangan indah, dan kesan terbaik selalu menyertai Anda.

With Love,
ASCHEN EVENT ORGANIZER.`;

const CATEGORIES = {
  wedding: {
    id: 'wedding',
    name: 'Wedding Party',
    code: 'WED',
    icon: '💍',
    description: 'Pemesanan perayaan pernikahan sakral dan elegan.',
    maxGuestStars: 2,
    questions: [
      {
        id: 'pemesan_username',
        label: 'Username Pemesan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Username Pemesan*\n\nᵎ!ᵎ Masukkan username Telegram pemesan (contoh: @username):`,
        validate: (val) => {
          if (!val || val.length < 2) return 'Username tidak boleh kosong.';
          return true;
        }
      },
      {
        id: 'pemesan_nama',
        label: 'Nama Pemesan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Lengkap / Panggilan Pemesan*\n\nᵎ!ᵎ Masukkan nama lengkap atau nama panggilan Anda:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama tidak boleh kosong.'
      },
      {
        id: 'mempelai_pria',
        label: 'Mempelai Pria',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Mempelai Pria (Groom)*\n\nᵎ!ᵎ Masukkan nama mempelai pria beserta username Telegram (contoh: Bryan - @bryan):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Data mempelai pria wajib diisi.'
      },
      {
        id: 'mempelai_wanita',
        label: 'Mempelai Wanita',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Mempelai Wanita (Bride)*\n\nᵎ!ᵎ Masukkan nama mempelai wanita beserta username Telegram (contoh: Valerie - @valerie):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Data mempelai wanita wajib diisi.'
      },
      {
        id: 'tanggal_acara',
        label: 'Tanggal Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Tanggal Acara*\n\nᵎ!ᵎ Silakan periksa ketersediaan tanggal pada tautan jadwal resmi ASCHEN melalui tombol di bawah sebelum mengisi.\n\nMasukkan tanggal pelaksanaan acara (Format: DD/MM/YYYY, contoh: 25/12/2026):`,
        validate: (val) => {
          const regex = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
          if (!regex.test(val.trim())) return 'Format tanggal harus DD/MM/YYYY (contoh: 25/12/2026).';
          return true;
        }
      },
      {
        id: 'jam_acara',
        label: 'Waktu / Jam Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Waktu / Jam Acara*\n\nᵎ!ᵎ Masukkan jam mulai dan selesai acara (Format: HH:MM WIB, contoh: 19:30 WIB - Selesai):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Waktu acara wajib diisi.'
      },
      {
        id: 'konsep_tema',
        label: 'Konsep / Tema Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Konsep & Tema Acara*\n\nᵎ!ᵎ Masukkan konsep atau tema pernikahan yang diinginkan (contoh: Royal White Elegance, Fairy Enchanted Garden, Classic Modern):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Konsep tema wajib diisi.'
      },
      {
        id: 'dress_code',
        label: 'Dress Code / Nuansa Warna',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Dress Code / Nuansa Warna*\n\nᵎ!ᵎ Masukkan warna tema atau ketentuan busana untuk para tamu:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Dress code wajib diisi.'
      },
      // GUEST STAR INTRO STEP
      {
        id: 'guest_star_count',
        label: 'Pilihan Guest Star',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Guest Star & Song (Maksimal 2)*\n\nᵎ!ᵎ Anda dapat melihat daftar Guest Star resmi ASCHEN melalui tombol di bawah sebelum memilih.\n\nBerapa jumlah Guest Star yang ingin Anda undang untuk Wedding Party?`,
        isGuestStarIntro: true,
        options: [
          { text: '0 (Tanpa Guest Star)', value: '0' },
          { text: '1 Guest Star', value: '1' },
          { text: '2 Guest Star', value: '2' }
        ]
      },
      // GUEST STAR 1
      {
        id: 'guest_star_1',
        label: 'Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 1*\n\nᵎ!ᵎ Masukkan nama Guest Star pertama yang dipilih:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 1 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_1',
        label: 'Lagu Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu untuk Guest Star 1*\n\nᵎ!ᵎ Masukkan judul lagu yang diminta untuk dinyanyikan oleh Guest Star 1:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      // GUEST STAR 2
      {
        id: 'guest_star_2',
        label: 'Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 2*\n\nᵎ!ᵎ Masukkan nama Guest Star kedua yang dipilih:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 2 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_2',
        label: 'Lagu Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu untuk Guest Star 2*\n\nᵎ!ᵎ Masukkan judul lagu yang diminta untuk dinyanyikan oleh Guest Star 2:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'rundown_request',
        label: 'Request Khusus Rundown',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Request Khusus Rundown / Prosesi*\n\nᵎ!ᵎ Apakah ada request susunan acara tertentu (contoh: Lempar Bunga, Games Pasangan, Sambutan Khusus)? Jika tidak ada ketik: -`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi atau ketik tanda minus (-).'
      },
      {
        id: 'catatan_tambahan',
        label: 'Catatan Tambahan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Catatan Tambahan (Opsional)*\n\nᵎ!ᵎ Masukkan catatan tambahan jika ada. Jika tidak ada, Anda dapat menekan tombol LEWATI.`,
        isOptional: true
      }
    ],
    renderPreview: (answers) => {
      let gsText = '';
      if (answers.guest_star_count === '1') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}`;
      } else if (answers.guest_star_count === '2') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}\n• Guest Star 2: ${answers.guest_star_2 || '-'}\n• Lagu Guest Star 2: ${answers.lagu_guest_star_2 || '-'}`;
      }

      let catatanSection = '';
      if (answers.catatan_tambahan && answers.catatan_tambahan.trim() !== '-' && answers.catatan_tambahan.trim().toLowerCase() !== 'lewati') {
        catatanSection = `\n➤ CATATAN TAMBAHAN\n• ${answers.catatan_tambahan}`;
      }

      return `𓄲 ASCHEN EVENT ORGANIZER
➤ FORMULIR PEMESANAN — WEDDING PARTY
ᵎ!ᵎ Harap periksa kembali detail pemesanan di bawah ini.

➤ DATA PEMESAN
• Username Pemesan: ${answers.pemesan_username}
• Nama Pemesan: ${answers.pemesan_nama}

➤ DATA MEMPELAI
• Mempelai Pria (Groom): ${answers.mempelai_pria}
• Mempelai Wanita (Bride): ${answers.mempelai_wanita}

➤ WAKTU & TEMA
• Tanggal Acara: ${answers.tanggal_acara}
• Jam Acara: ${answers.jam_acara}
• Konsep & Tema: ${answers.konsep_tema}
• Dress Code: ${answers.dress_code}
${gsText ? '\n' + gsText : ''}
➤ RUNDOWN & PROSESI
• Request Khusus: ${answers.rundown_request || '-'}${catatanSection}

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;
    }
  },

  birthday: {
    id: 'birthday',
    name: 'Birthday Party',
    code: 'BDY',
    icon: '🎂',
    description: 'Pemesanan pesta ulang tahun yang meriah dan berkesan.',
    maxGuestStars: 2,
    questions: [
      {
        id: 'pemesan_username',
        label: 'Username Pemesan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Username Pemesan*\n\nᵎ!ᵎ Masukkan username Telegram pemesan (contoh: @username):`,
        validate: (val) => val && val.length >= 2 ? true : 'Username wajib diisi.'
      },
      {
        id: 'pemesan_nama',
        label: 'Nama Pemesan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Pemesan*\n\nᵎ!ᵎ Masukkan nama lengkap atau nama panggilan Anda:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama wajib diisi.'
      },
      {
        id: 'nama_ultah',
        label: 'Nama Yang Berulang Tahun',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Yang Berulang Tahun*\n\nᵎ!ᵎ Masukkan nama orang yang berulang tahun beserta username Telegram:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama yang berulang tahun wajib diisi.'
      },
      {
        id: 'usia_ultah',
        label: 'Perayaan Ulang Tahun Ke-',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Perayaan Ulang Tahun Ke-*\n\nᵎ!ᵎ Masukkan usia yang dirayakan (contoh: Sweet 17th, 20th, 25th):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Usia perayaan wajib diisi.'
      },
      {
        id: 'tanggal_acara',
        label: 'Tanggal Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Tanggal Acara*\n\nᵎ!ᵎ Silakan periksa ketersediaan tanggal pada tautan jadwal resmi ASCHEN melalui tombol di bawah sebelum mengisi.\n\nMasukkan tanggal pelaksanaan acara (Format: DD/MM/YYYY, contoh: 18/11/2026):`,
        validate: (val) => {
          const regex = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
          if (!regex.test(val.trim())) return 'Format tanggal harus DD/MM/YYYY.';
          return true;
        }
      },
      {
        id: 'jam_acara',
        label: 'Waktu / Jam Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Waktu / Jam Acara*\n\nᵎ!ᵎ Masukkan jam pelaksanaan acara (Format: HH:MM WIB, contoh: 20:00 WIB - Selesai):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Waktu acara wajib diisi.'
      },
      {
        id: 'konsep_tema',
        label: 'Konsep / Tema Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Konsep & Tema Acara*\n\nᵎ!ᵎ Masukkan konsep atau tema pesta ulang tahun (contoh: Neon Night Party, Vintage Glam, Pastel Wonderland):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Konsep tema wajib diisi.'
      },
      {
        id: 'dress_code',
        label: 'Dress Code',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Dress Code / Nuansa Warna*\n\nᵎ!ᵎ Masukkan tema pakaian atau warna bagi para hadirin:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Dress code wajib diisi.'
      },
      // GUEST STAR INTRO STEP
      {
        id: 'guest_star_count',
        label: 'Pilihan Guest Star',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Guest Star & Song (Maksimal 2)*\n\nᵎ!ᵎ Anda dapat melihat daftar Guest Star resmi ASCHEN melalui tautan di bawah sebelum memilih.\n\nBerapa jumlah Guest Star yang ingin dihadirkan?`,
        isGuestStarIntro: true,
        options: [
          { text: '0 (Tanpa Guest Star)', value: '0' },
          { text: '1 Guest Star', value: '1' },
          { text: '2 Guest Star', value: '2' }
        ]
      },
      {
        id: 'guest_star_1',
        label: 'Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 1*\n\nᵎ!ᵎ Masukkan nama Guest Star pertama:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 1 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_1',
        label: 'Lagu Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu untuk Guest Star 1*\n\nᵎ!ᵎ Masukkan judul lagu yang ingin dibawakan:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'guest_star_2',
        label: 'Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 2*\n\nᵎ!ᵎ Masukkan nama Guest Star kedua:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 2 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_2',
        label: 'Lagu Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu untuk Guest Star 2*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 2:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'request_tiup_lilin',
        label: 'Momen Tiup Lilin / Games',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Request Momen Tiup Lilin / Games*\n\nᵎ!ᵎ Masukkan request susunan tiup lilin, games, atau doorprize (atau ketik: -):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi atau ketik tanda minus (-).'
      },
      {
        id: 'catatan_tambahan',
        label: 'Catatan Tambahan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Catatan Tambahan (Opsional)*\n\nᵎ!ᵎ Masukkan catatan tambahan jika ada atau tekan tombol LEWATI.`,
        isOptional: true
      }
    ],
    renderPreview: (answers) => {
      let gsText = '';
      if (answers.guest_star_count === '1') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}`;
      } else if (answers.guest_star_count === '2') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}\n• Guest Star 2: ${answers.guest_star_2 || '-'}\n• Lagu Guest Star 2: ${answers.lagu_guest_star_2 || '-'}`;
      }

      let catatanSection = '';
      if (answers.catatan_tambahan && answers.catatan_tambahan.trim() !== '-' && answers.catatan_tambahan.trim().toLowerCase() !== 'lewati') {
        catatanSection = `\n➤ CATATAN TAMBAHAN\n• ${answers.catatan_tambahan}`;
      }

      return `𓄲 ASCHEN EVENT ORGANIZER
➤ FORMULIR PEMESANAN — BIRTHDAY PARTY
ᵎ!ᵎ Harap periksa kembali detail pemesanan di bawah ini.

➤ DATA PEMESAN
• Username Pemesan: ${answers.pemesan_username}
• Nama Pemesan: ${answers.pemesan_nama}

➤ DETAIL ULANG TAHUN
• Nama Yang Berulang Tahun: ${answers.nama_ultah}
• Perayaan Ulang Tahun Ke-: ${answers.usia_ultah}

➤ WAKTU & TEMA
• Tanggal Acara: ${answers.tanggal_acara}
• Jam Acara: ${answers.jam_acara}
• Konsep & Tema: ${answers.konsep_tema}
• Dress Code: ${answers.dress_code}
${gsText ? '\n' + gsText : ''}
➤ RUNDOWN & KEGIATAN
• Tiup Lilin / Games / Doorprize: ${answers.request_tiup_lilin || '-'}${catatanSection}

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;
    }
  },

  engagement: {
    id: 'engagement',
    name: 'Engagement Party',
    code: 'ENG',
    icon: '🥂',
    description: 'Pemesanan pesta pertunangan romantis dan khidmat.',
    maxGuestStars: 2,
    questions: [
      {
        id: 'pemesan_username',
        label: 'Username Pemesan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Username Pemesan*\n\nᵎ!ᵎ Masukkan username Telegram pemesan:`,
        validate: (val) => val && val.length >= 2 ? true : 'Username wajib diisi.'
      },
      {
        id: 'pemesan_nama',
        label: 'Nama Pemesan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Pemesan*\n\nᵎ!ᵎ Masukkan nama Anda:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama wajib diisi.'
      },
      {
        id: 'nama_pasangan_1',
        label: 'Calon Mempelai Pria',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Calon Mempelai Pria*\n\nᵎ!ᵎ Masukkan nama calon mempelai pria + username:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Data calon pria wajib diisi.'
      },
      {
        id: 'nama_pasangan_2',
        label: 'Calon Mempelai Wanita',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Calon Mempelai Wanita*\n\nᵎ!ᵎ Masukkan nama calon mempelai wanita + username:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Data calon wanita wajib diisi.'
      },
      {
        id: 'tanggal_acara',
        label: 'Tanggal Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Tanggal Acara*\n\nᵎ!ᵎ Silakan periksa ketersediaan tanggal pada tautan jadwal resmi ASCHEN melalui tombol di bawah sebelum mengisi.\n\nMasukkan tanggal acara (Format: DD/MM/YYYY, contoh: 20/12/2026):`,
        validate: (val) => /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.test(val.trim()) ? true : 'Format tanggal harus DD/MM/YYYY.'
      },
      {
        id: 'jam_acara',
        label: 'Waktu / Jam Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Waktu / Jam Acara*\n\nᵎ!ᵎ Masukkan jam pelaksanaan acara (contoh: 19:00 WIB):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Jam acara wajib diisi.'
      },
      {
        id: 'konsep_tema',
        label: 'Konsep / Tema Pertunangan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Konsep & Tema Pertunangan*\n\nᵎ!ᵎ Masukkan konsep atau nuansa pertunangan (contoh: Warm Earthy Rustic, Classic Emerald, Floral Pastel):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Konsep tema wajib diisi.'
      },
      {
        id: 'dress_code',
        label: 'Dress Code',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Dress Code / Nuansa Warna*\n\nᵎ!ᵎ Masukkan ketentuan pakaian para undangan:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Dress code wajib diisi.'
      },
      // GUEST STAR INTRO
      {
        id: 'guest_star_count',
        label: 'Pilihan Guest Star',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Guest Star & Song (Maksimal 2)*\n\nᵎ!ᵎ Anda dapat melihat daftar Guest Star resmi ASCHEN melalui tautan di bawah.\n\nBerapa jumlah Guest Star yang ingin diundang?`,
        isGuestStarIntro: true,
        options: [
          { text: '0 (Tanpa Guest Star)', value: '0' },
          { text: '1 Guest Star', value: '1' },
          { text: '2 Guest Star', value: '2' }
        ]
      },
      {
        id: 'guest_star_1',
        label: 'Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 1*\n\nᵎ!ᵎ Masukkan nama Guest Star pertama:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 1 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_1',
        label: 'Lagu Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 1*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 1:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'guest_star_2',
        label: 'Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 2*\n\nᵎ!ᵎ Masukkan nama Guest Star kedua:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 2 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_2',
        label: 'Lagu Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 2*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 2:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'request_tukar_cincin',
        label: 'Request Prosesi Tukar Cincin',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Request Prosesi Tukar Cincin / Sambutan*\n\nᵎ!ᵎ Masukkan request khusus prosesi tukar cincin atau sambutan (atau ketik: -):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi atau ketik minus (-).'
      },
      {
        id: 'catatan_tambahan',
        label: 'Catatan Tambahan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Catatan Tambahan (Opsional)*\n\nᵎ!ᵎ Masukkan catatan tambahan jika ada atau tekan tombol LEWATI.`,
        isOptional: true
      }
    ],
    renderPreview: (answers) => {
      let gsText = '';
      if (answers.guest_star_count === '1') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}`;
      } else if (answers.guest_star_count === '2') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}\n• Guest Star 2: ${answers.guest_star_2 || '-'}\n• Lagu Guest Star 2: ${answers.lagu_guest_star_2 || '-'}`;
      }

      let catatanSection = '';
      if (answers.catatan_tambahan && answers.catatan_tambahan.trim() !== '-' && answers.catatan_tambahan.trim().toLowerCase() !== 'lewati') {
        catatanSection = `\n➤ CATATAN TAMBAHAN\n• ${answers.catatan_tambahan}`;
      }

      return `𓄲 ASCHEN EVENT ORGANIZER
➤ FORMULIR PEMESANAN — ENGAGEMENT PARTY
ᵎ!ᵎ Harap periksa kembali detail pemesanan di bawah ini.

➤ DATA PEMESAN
• Username Pemesan: ${answers.pemesan_username}
• Nama Pemesan: ${answers.pemesan_nama}

➤ DATA PASANGAN TUNANGAN
• Calon Mempelai Pria: ${answers.nama_pasangan_1}
• Calon Mempelai Wanita: ${answers.nama_pasangan_2}

➤ WAKTU & TEMA
• Tanggal Acara: ${answers.tanggal_acara}
• Jam Acara: ${answers.jam_acara}
• Konsep & Tema: ${answers.konsep_tema}
• Dress Code: ${answers.dress_code}
${gsText ? '\n' + gsText : ''}
➤ PROSESI & RUNDOWN
• Prosesi Tukar Cincin / Sambutan: ${answers.request_tukar_cincin || '-'}${catatanSection}

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;
    }
  },

  mensive_family_couple: {
    id: 'mensive_family_couple',
    name: 'Mensive Family / Couple',
    code: 'MFC',
    icon: '👨‍👩‍👦',
    description: 'Pemesanan perayaan mensive/anniversary keluarga atau pasangan.',
    maxGuestStars: 2,
    questions: [
      {
        id: 'pemesan_username',
        label: 'Username Pemesan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Username Pemesan*\n\nᵎ!ᵎ Masukkan username Telegram pemesan:`,
        validate: (val) => val && val.length >= 2 ? true : 'Username wajib diisi.'
      },
      {
        id: 'tipe_mensive',
        label: 'Tipe Mensive',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Tipe Mensive*\n\nᵎ!ᵎ Pilih jenis perayaan mensive yang akan diadakan:`,
        options: [
          { text: '👩‍❤️‍👨 Couple (Pasangan)', value: 'Couple' },
          { text: '👨‍👩‍👧‍👦 Family (Keluarga / Trah)', value: 'Family' }
        ]
      },
      {
        id: 'nama_pihak',
        label: 'Nama Pasangan / Keluarga',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Pasangan atau Nama Keluarga*\n\nᵎ!ᵎ Masukkan nama pasangan (beserta username keduanya) ATAU nama keluarga/trah yang merayakan:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi.'
      },
      {
        id: 'usia_mensive',
        label: 'Peringatan Mensive Ke-',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Peringatan Mensive Ke-*\n\nᵎ!ᵎ Masukkan usia perayaan mensive (contoh: 1st Month, 6th Month, 1st Anniversary):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Usia mensive wajib diisi.'
      },
      {
        id: 'tanggal_acara',
        label: 'Tanggal Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Tanggal Acara*\n\nᵎ!ᵎ Silakan periksa ketersediaan tanggal pada tautan jadwal resmi ASCHEN melalui tombol di bawah sebelum mengisi.\n\nMasukkan tanggal acara (Format: DD/MM/YYYY, contoh: 20/12/2026):`,
        validate: (val) => /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.test(val.trim()) ? true : 'Format tanggal harus DD/MM/YYYY.'
      },
      {
        id: 'jam_acara',
        label: 'Waktu / Jam Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Waktu / Jam Acara*\n\nᵎ!ᵎ Masukkan waktu/jam acara:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Jam acara wajib diisi.'
      },
      {
        id: 'konsep_tema',
        label: 'Konsep / Tema Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Konsep & Tema Acara*\n\nᵎ!ᵎ Masukkan konsep atau tema acara (contoh: Sweet Heart, Warm Family Harmony, Vintage Cozy):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Konsep tema wajib diisi.'
      },
      {
        id: 'dress_code',
        label: 'Dress Code',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Dress Code / Nuansa Warna*\n\nᵎ!ᵎ Masukkan nuansa warna atau ketentuan pakaian:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Dress code wajib diisi.'
      },
      // GUEST STAR INTRO
      {
        id: 'guest_star_count',
        label: 'Pilihan Guest Star',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Guest Star & Song (Maksimal 2)*\n\nᵎ!ᵎ Buka tautan resmi di bawah untuk daftar Guest Star.\n\nBerapa jumlah Guest Star yang ingin dihadirkan?`,
        isGuestStarIntro: true,
        options: [
          { text: '0 (Tanpa Guest Star)', value: '0' },
          { text: '1 Guest Star', value: '1' },
          { text: '2 Guest Star', value: '2' }
        ]
      },
      {
        id: 'guest_star_1',
        label: 'Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 1*\n\nᵎ!ᵎ Masukkan nama Guest Star pertama:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 1 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_1',
        label: 'Lagu Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 1*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 1:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'guest_star_2',
        label: 'Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 2*\n\nᵎ!ᵎ Masukkan nama Guest Star kedua:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 2 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_2',
        label: 'Lagu Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 2*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 2:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'request_kegiatan',
        label: 'Request Kegiatan Spesial',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Request Kegiatan Spesial / Games*\n\nᵎ!ᵎ Masukkan request segmen acara (contoh: Sesi Kesan Pesan, Games Keluarga, Pemutaran Video):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi atau ketik minus (-).'
      },
      {
        id: 'catatan_tambahan',
        label: 'Catatan Tambahan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Catatan Tambahan (Opsional)*\n\nᵎ!ᵎ Masukkan catatan tambahan jika ada atau tekan tombol LEWATI.`,
        isOptional: true
      }
    ],
    renderPreview: (answers) => {
      let gsText = '';
      if (answers.guest_star_count === '1') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}`;
      } else if (answers.guest_star_count === '2') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}\n• Guest Star 2: ${answers.guest_star_2 || '-'}\n• Lagu Guest Star 2: ${answers.lagu_guest_star_2 || '-'}`;
      }

      let catatanSection = '';
      if (answers.catatan_tambahan && answers.catatan_tambahan.trim() !== '-' && answers.catatan_tambahan.trim().toLowerCase() !== 'lewati') {
        catatanSection = `\n➤ CATATAN TAMBAHAN\n• ${answers.catatan_tambahan}`;
      }

      return `𓄲 ASCHEN EVENT ORGANIZER
➤ FORMULIR PEMESANAN — MENSIVE FAMILY / COUPLE
ᵎ!ᵎ Harap periksa kembali detail pemesanan di bawah ini.

➤ DATA PEMESAN
• Username Pemesan: ${answers.pemesan_username}
• Tipe Mensive: ${answers.tipe_mensive}
• Nama ${answers.tipe_mensive === 'Couple' ? 'Pasangan' : 'Keluarga'}: ${answers.nama_pihak}
• Peringatan Ke-: ${answers.usia_mensive}

➤ WAKTU & TEMA
• Tanggal Acara: ${answers.tanggal_acara}
• Jam Acara: ${answers.jam_acara}
• Konsep & Tema: ${answers.konsep_tema}
• Dress Code: ${answers.dress_code}
${gsText ? '\n' + gsText : ''}
➤ RUNDOWN & KEGIATAN
• Request Khusus / Games: ${answers.request_kegiatan || '-'}${catatanSection}

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;
    }
  },

  mensive_channel_vvip: {
    id: 'mensive_channel_vvip',
    name: 'Mensive Channel VVIP',
    code: 'MCV',
    icon: '👑',
    description: 'Pemesanan perayaan mensive channel Telegram eksklusif tingkat VVIP.',
    maxGuestStars: 2,
    questions: [
      {
        id: 'pemesan_username',
        label: 'Username Owner / Admin',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Username Owner / Admin Channel*\n\nᵎ!ᵎ Masukkan username Telegram pemesan (contoh: @username):`,
        validate: (val) => val && val.length >= 2 ? true : 'Username wajib diisi.'
      },
      {
        id: 'nama_channel',
        label: 'Nama Channel Telegram',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Channel Telegram*\n\nᵎ!ᵎ Masukkan nama channel yang merayakan mensive:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama channel wajib diisi.'
      },
      {
        id: 'link_channel',
        label: 'Link / Tautan Channel',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Link / Tautan Channel*\n\nᵎ!ᵎ Masukkan tautan channel (contoh: https://t.me/channel atau @channel):`,
        validate: (val) => {
          if (!val || val.trim().length === 0) return 'Tautan channel wajib diisi.';
          if (!val.includes('t.me/') && !val.startsWith('@')) {
            return 'Format tautan channel tidak valid. Gunakan format @nama_channel atau https://t.me/nama_channel';
          }
          return true;
        }
      },
      {
        id: 'usia_mensive_channel',
        label: 'Peringatan Mensive Ke-',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Peringatan Mensive Ke-*\n\nᵎ!ᵎ Masukkan usia perayaan channel (contoh: 2nd Month, 6th Month, 1st Anniversary):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Usia mensive wajib diisi.'
      },
      {
        id: 'tanggal_acara',
        label: 'Tanggal Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Tanggal Acara*\n\nᵎ!ᵎ Silakan periksa ketersediaan tanggal pada tautan jadwal resmi ASCHEN melalui tombol di bawah sebelum mengisi.\n\nMasukkan tanggal acara (Format: DD/MM/YYYY, contoh: 20/12/2026):`,
        validate: (val) => /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.test(val.trim()) ? true : 'Format tanggal harus DD/MM/YYYY.'
      },
      {
        id: 'jam_acara',
        label: 'Waktu / Jam Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Waktu / Jam Acara*\n\nᵎ!ᵎ Masukkan waktu pelaksanaan acara (HH:MM WIB):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Jam acara wajib diisi.'
      },
      {
        id: 'konsep_tema',
        label: 'Konsep / Tema Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Konsep & Tema Acara*\n\nᵎ!ᵎ Masukkan konsep acara (contoh: VVIP Golden Royal, Cyber Noir Gala, Luxury Minimalist):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Konsep tema wajib diisi.'
      },
      {
        id: 'dress_code',
        label: 'Dress Code',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Dress Code / Nuansa Warna*\n\nᵎ!ᵎ Masukkan nuansa warna atau dress code para member/tamu:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Dress code wajib diisi.'
      },
      // GUEST STAR INTRO
      {
        id: 'guest_star_count',
        label: 'Pilihan Guest Star',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Guest Star & Song (Maksimal 2)*\n\nᵎ!ᵎ Klik tombol di bawah untuk melihat daftar Guest Star resmi ASCHEN.\n\nBerapa jumlah Guest Star yang ingin dihadirkan?`,
        isGuestStarIntro: true,
        options: [
          { text: '0 (Tanpa Guest Star)', value: '0' },
          { text: '1 Guest Star', value: '1' },
          { text: '2 Guest Star', value: '2' }
        ]
      },
      {
        id: 'guest_star_1',
        label: 'Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 1*\n\nᵎ!ᵎ Masukkan nama Guest Star pertama:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 1 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_1',
        label: 'Lagu Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 1*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 1:`,
        condition: (answers) => ['1', '2'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'guest_star_2',
        label: 'Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 2*\n\nᵎ!ᵎ Masukkan nama Guest Star kedua:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 2 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_2',
        label: 'Lagu Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 2*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 2:`,
        condition: (answers) => answers.guest_star_count === '2',
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'request_open_member',
        label: 'Request Kegiatan Channel',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Request Kegiatan / Segmen Channel*\n\nᵎ!ᵎ Masukkan agenda khusus (contoh: Open Member Serentak, Sesi Q&A, Doorprize / Giveaway, Games Member):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi atau ketik minus (-).'
      },
      {
        id: 'catatan_tambahan',
        label: 'Catatan Tambahan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Catatan Tambahan (Opsional)*\n\nᵎ!ᵎ Masukkan catatan tambahan jika ada atau tekan tombol LEWATI.`,
        isOptional: true
      }
    ],
    renderPreview: (answers) => {
      let gsText = '';
      if (answers.guest_star_count === '1') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}`;
      } else if (answers.guest_star_count === '2') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}\n• Guest Star 2: ${answers.guest_star_2 || '-'}\n• Lagu Guest Star 2: ${answers.lagu_guest_star_2 || '-'}`;
      }

      let catatanSection = '';
      if (answers.catatan_tambahan && answers.catatan_tambahan.trim() !== '-' && answers.catatan_tambahan.trim().toLowerCase() !== 'lewati') {
        catatanSection = `\n➤ CATATAN TAMBAHAN\n• ${answers.catatan_tambahan}`;
      }

      return `𓄲 ASCHEN EVENT ORGANIZER
➤ FORMULIR PEMESANAN — MENSIVE CHANNEL VVIP
ᵎ!ᵎ Harap periksa kembali detail pemesanan di bawah ini.

➤ DATA PEMESAN & CHANNEL
• Username Owner/Admin: ${answers.pemesan_username}
• Nama Channel: ${answers.nama_channel}
• Tautan Channel: ${answers.link_channel}
• Peringatan Ke-: ${answers.usia_mensive_channel}

➤ WAKTU & TEMA
• Tanggal Acara: ${answers.tanggal_acara}
• Jam Acara: ${answers.jam_acara}
• Konsep & Tema: ${answers.konsep_tema}
• Dress Code: ${answers.dress_code}
${gsText ? '\n' + gsText : ''}
➤ KEGIATAN CHANNEL
• Agenda / Segmen Acara: ${answers.request_open_member || '-'}${catatanSection}

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;
    }
  },

  promnight_graduation: {
    id: 'promnight_graduation',
    name: 'Promnight / Graduation',
    code: 'PMG',
    icon: '🎓',
    description: 'Pemesanan acara malam kelulusan atau perpisahan angkatan termegah.',
    maxGuestStars: 3, // Special rule: up to 3 guest stars
    questions: [
      {
        id: 'pemesan_username',
        label: 'Username PIC / Ketua Panitia',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Username PIC / Ketua Panitia*\n\nᵎ!ᵎ Masukkan username Telegram pemesan (contoh: @username):`,
        validate: (val) => val && val.length >= 2 ? true : 'Username wajib diisi.'
      },
      {
        id: 'nama_instansi',
        label: 'Nama Sekolah / Institusi / Squad',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Sekolah / Institusi / Squad*\n\nᵎ!ᵎ Masukkan nama sekolah, universitas, atau squad penyelenggara:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama institusi wajib diisi.'
      },
      {
        id: 'nama_angkatan',
        label: 'Nama Angkatan / Batch',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Angkatan / Batch / Kelas*\n\nᵎ!ᵎ Masukkan nama angkatan atau batch (contoh: Generation of 2026 / Asteria Batch 12):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama angkatan wajib diisi.'
      },
      {
        id: 'tanggal_acara',
        label: 'Tanggal Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Tanggal Acara*\n\nᵎ!ᵎ Silakan periksa ketersediaan tanggal pada tautan jadwal resmi ASCHEN melalui tombol di bawah sebelum mengisi.\n\nMasukkan tanggal acara (Format: DD/MM/YYYY, contoh: 20/12/2026):`,
        validate: (val) => /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.test(val.trim()) ? true : 'Format tanggal harus DD/MM/YYYY.'
      },
      {
        id: 'jam_acara',
        label: 'Waktu / Jam Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Waktu / Jam Acara*\n\nᵎ!ᵎ Masukkan jam pelaksanaan acara:`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Jam acara wajib diisi.'
      },
      {
        id: 'konsep_tema',
        label: 'Konsep & Tema Acara',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Konsep & Tema Acara*\n\nᵎ!ᵎ Masukkan tema promnight (contoh: A Night Under the Stars, Hollywood Red Carpet Gala, Golden Glamour):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Konsep tema wajib diisi.'
      },
      {
        id: 'dress_code',
        label: 'Dress Code',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Dress Code / Pakaian*\n\nᵎ!ᵎ Masukkan dress code (contoh: Tuxedo, Evening Gown, Black Tie Glamour):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Dress code wajib diisi.'
      },
      // GUEST STAR INTRO (Maksimal 3 untuk Promnight)
      {
        id: 'guest_star_count',
        label: 'Pilihan Guest Star',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Guest Star & Song (Maksimal 3)*\n\nᵎ!ᵎ Klik tombol di bawah untuk melihat daftar Guest Star resmi ASCHEN.\n\nBerapa jumlah Guest Star yang ingin dihadirkan (Maksimal 3)?`,
        isGuestStarIntro: true,
        options: [
          { text: '0 (Tanpa Guest Star)', value: '0' },
          { text: '1 Guest Star', value: '1' },
          { text: '2 Guest Star', value: '2' },
          { text: '3 Guest Star', value: '3' }
        ]
      },
      {
        id: 'guest_star_1',
        label: 'Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 1*\n\nᵎ!ᵎ Masukkan nama Guest Star pertama:`,
        condition: (answers) => ['1', '2', '3'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 1 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_1',
        label: 'Lagu Guest Star 1',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 1*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 1:`,
        condition: (answers) => ['1', '2', '3'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'guest_star_2',
        label: 'Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 2*\n\nᵎ!ᵎ Masukkan nama Guest Star kedua:`,
        condition: (answers) => ['2', '3'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 2 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_2',
        label: 'Lagu Guest Star 2',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 2*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 2:`,
        condition: (answers) => ['2', '3'].includes(answers.guest_star_count),
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'guest_star_3',
        label: 'Guest Star 3',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Nama Guest Star 3*\n\nᵎ!ᵎ Masukkan nama Guest Star ketiga:`,
        condition: (answers) => answers.guest_star_count === '3',
        validate: (val) => val && val.trim().length > 0 ? true : 'Nama Guest Star 3 wajib diisi.'
      },
      {
        id: 'lagu_guest_star_3',
        label: 'Lagu Guest Star 3',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Lagu Guest Star 3*\n\nᵎ!ᵎ Masukkan judul lagu untuk Guest Star 3:`,
        condition: (answers) => answers.guest_star_count === '3',
        validate: (val) => val && val.trim().length > 0 ? true : 'Judul lagu wajib diisi.'
      },
      {
        id: 'request_penghargaan',
        label: 'Request Momen Penghargaan / Sambutan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Request Momen Khusus / Awarding*\n\nᵎ!ᵎ Masukkan request segmen acara (contoh: Prom King & Queen, Awarding Guru/Siswa, Kilas Balik Video):`,
        validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi atau ketik minus (-).'
      },
      {
        id: 'catatan_tambahan',
        label: 'Catatan Tambahan',
        prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Catatan Tambahan (Opsional)*\n\nᵎ!ᵎ Masukkan catatan tambahan jika ada atau tekan tombol LEWATI.`,
        isOptional: true
      }
    ],
    renderPreview: (answers) => {
      let gsText = '';
      if (answers.guest_star_count === '1') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}`;
      } else if (answers.guest_star_count === '2') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}\n• Guest Star 2: ${answers.guest_star_2 || '-'}\n• Lagu Guest Star 2: ${answers.lagu_guest_star_2 || '-'}`;
      } else if (answers.guest_star_count === '3') {
        gsText = `➤ GUEST STAR & SONG\n• Guest Star 1: ${answers.guest_star_1 || '-'}\n• Lagu Guest Star 1: ${answers.lagu_guest_star_1 || '-'}\n• Guest Star 2: ${answers.guest_star_2 || '-'}\n• Lagu Guest Star 2: ${answers.lagu_guest_star_2 || '-'}\n• Guest Star 3: ${answers.guest_star_3 || '-'}\n• Lagu Guest Star 3: ${answers.lagu_guest_star_3 || '-'}`;
      }

      let catatanSection = '';
      if (answers.catatan_tambahan && answers.catatan_tambahan.trim() !== '-' && answers.catatan_tambahan.trim().toLowerCase() !== 'lewati') {
        catatanSection = `\n➤ CATATAN TAMBAHAN\n• ${answers.catatan_tambahan}`;
      }

      return `𓄲 ASCHEN EVENT ORGANIZER
➤ FORMULIR PEMESANAN — PROMNIGHT / GRADUATION
ᵎ!ᵎ Harap periksa kembali detail pemesanan di bawah ini.

➤ DATA PANITIA & ANGKATAN
• Username PIC / Ketua: ${answers.pemesan_username}
• Institusi / Sekolah: ${answers.nama_instansi}
• Angkatan / Batch: ${answers.nama_angkatan}

➤ WAKTU & TEMA
• Tanggal Acara: ${answers.tanggal_acara}
• Jam Acara: ${answers.jam_acara}
• Konsep & Tema: ${answers.konsep_tema}
• Dress Code: ${answers.dress_code}
${gsText ? '\n' + gsText : ''}
➤ SEGMEN ACARA
• Awarding / Sambutan / Video: ${answers.request_penghargaan || '-'}${catatanSection}

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;
    }
  }
};

const VENUE_TEMPLATE = {
  id: 'venue_reservation',
  name: 'Formulir Reservasi Tempat',
  questions: [
    {
      id: 'nama_venue',
      label: 'Nama Tempat / Venue / Group',
      prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Reservasi Tempat — Nama Tempat / Venue*\n\nᵎ!ᵎ Masukkan nama tempat, gedung, atau tautan group/channel venue acara:`,
      validate: (val) => val && val.trim().length > 0 ? true : 'Nama tempat wajib diisi.'
    },
    {
      id: 'alamat_lokasi',
      label: 'Alamat / Tautan Akses Ruangan',
      prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Alamat Lengkap / Tautan Ruangan*\n\nᵎ!ᵎ Masukkan alamat lokasi atau tautan link ruangan acara:`,
      validate: (val) => val && val.trim().length > 0 ? true : 'Alamat/tautan ruangan wajib diisi.'
    },
    {
      id: 'estimasi_tamu',
      label: 'Estimasi Jumlah Tamu',
      prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Estimasi Jumlah Tamu Undangan*\n\nᵎ!ᵎ Masukkan perkiraan jumlah tamu (contoh: 50 orang, 100 member, dll.):`,
      validate: (val) => val && val.trim().length > 0 ? true : 'Estimasi tamu wajib diisi.'
    },
    {
      id: 'konsep_dekorasi_tempat',
      label: 'Konsep & Penataan Dekorasi',
      prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Konsep & Penataan Dekorasi Ruangan*\n\nᵎ!ᵎ Masukkan detail penataan panggung, meja, dan nuansa visual ruangan:`,
      validate: (val) => val && val.trim().length > 0 ? true : 'Konsep dekorasi tempat wajib diisi.'
    },
    {
      id: 'fasilitas_request',
      label: 'Fasilitas & Kebutuhan Teknis',
      prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Kebutuhan Fasilitas & Teknis*\n\nᵎ!ᵎ Masukkan kebutuhan teknis (contoh: Sound system, Bot Music, Backstage, Bot Security, Mic):`,
      validate: (val) => val && val.trim().length > 0 ? true : 'Wajib diisi atau ketik minus (-).'
    },
    {
      id: 'pic_venue',
      label: 'Kontak / PIC Venue',
      prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Kontak / Username PIC Venue*\n\nᵎ!ᵎ Masukkan nama dan username pihak penanggung jawab tempat:`,
      validate: (val) => val && val.trim().length > 0 ? true : 'PIC Venue wajib diisi.'
    },
    {
      id: 'catatan_venue',
      label: 'Catatan Khusus Tempat',
      prompt: `𓄲 ASCHEN EVENT ORGANIZER\n➤ *Catatan Khusus Tempat (Opsional)*\n\nᵎ!ᵎ Masukkan catatan tambahan jika ada atau tekan tombol LEWATI.`,
      isOptional: true
    }
  ],
  renderPreview: (answers, bookingId) => {
    let catatan = '';
    if (answers.catatan_venue && answers.catatan_venue.trim() !== '-' && answers.catatan_venue.trim().toLowerCase() !== 'lewati') {
      catatan = `\n• Catatan Tambahan: ${answers.catatan_venue}`;
    }

    return `𓄲 ASCHEN EVENT ORGANIZER
➤ FORMULIR RESERVASI TEMPAT
ᵎ!ᵎ Terhubung dengan Booking ID: ${bookingId}

➤ DETAIL TEMPAT & LOKASI
• Nama Tempat / Venue: ${answers.nama_venue}
• Alamat / Tautan Ruangan: ${answers.alamat_lokasi}
• Estimasi Tamu: ${answers.estimasi_tamu}

➤ DEKORASI & FASILITAS
• Konsep & Penataan Ruangan: ${answers.konsep_dekorasi_tempat}
• Kebutuhan Fasilitas: ${answers.fasilitas_request}
• PIC Venue: ${answers.pic_venue}${catatan}

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;
  }
};

const RESERVASI_MESSAGE = (bookingId) => 
`𓄲 ASCHEN EVENT ORGANIZER
➤ RUANG RESERVASI & TEMPAT PERTEMUAN
ᵎ!ᵎ Terkait Booking ID: \`${bookingId}\`

Pemesanan acara Anda telah disetujui oleh tim ASCHEN EVENT ORGANIZER!

Silakan bergabung ke ruang reservasi dan koordinasi pertemuan kami melalui tautan resmi di bawah ini:

🔗 ${OFFICIAL_RESERVASI_URL}

Klik tombol "🏨 GABUNG RUANG PERTEMUAN" di bawah untuk langsung terhubung.

With Love,
ASCHEN EVENT ORGANIZER.
@ASCHENEO`;

module.exports = {
  BOOKING_STATUSES,
  THANK_YOU_MESSAGE,
  RESERVASI_MESSAGE,
  CATEGORIES,
  VENUE_TEMPLATE,
  OFFICIAL_GS_URL,
  OFFICIAL_JADWAL_URL,
  OFFICIAL_RESERVASI_URL
};
