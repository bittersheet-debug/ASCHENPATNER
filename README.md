# 𓄲 MEDIA PARTNER ASCHEN EVENT ORGANIZER
**Official Bot:** [@PATNERASCHENBOT](https://t.me/PATNERASCHENBOT) | **Official Channel:** [@ASCHENEO](https://t.me/ASCHENEO)  
*"Elegant Collaboration, Memorable Celebration"*

Sistem otomasi resmi pengelolaan publikasi poster Media Partner untuk **ASCHEN EVENT ORGANIZER**. Dilengkapi dengan Website Portal, Dashboard Admin Realtime, Sistem Autentikasi MTProto 4-Tahap, Pelaporan Otomatis ke Channel Terverifikasi, dan Penjadwal Publikasi Otomatis Vercel Cron.

---

## 💎 Identitas & Ketentuan Resmi

- **Bot Telegram Media Partner:** [@PATNERASCHENBOT](https://t.me/PATNERASCHENBOT)
- **Channel Siaran Publikasi:** [@ASCHENEO](https://t.me/ASCHENEO)
- **ID Channel Notifikasi Pelaporan:** `-1004479248551` (Permanen)
- **Password Default Admin:** `aschen2026`
- **Simbol & Tipografi Khas:** `𓄲`, `➤`, `ᵎ!ᵎ`, Cinzel & Plus Jakarta Sans

---

## ⏰ Jam Operasional & Jadwal Publikasi

### 1. Jam Operasional Pengajuan Poster
- **Senin – Sabtu:** Aktif mulai pukul **06.00 WIB**.
- **Minggu:** **TUTUP** (Layanan Libur, pengajuan akan diproses hari Senin).

### 2. Jadwal Resmi Publikasi ke Channel @ASCHENEO
| Hari | Waktu | Sesi |
|---|---|---|
| **Selasa** | 09.00 WIB | Sesi Pagi |
| **Rabu** | 12.00 WIB | Sesi Siang |
| **Kamis** | 09.00 WIB | Sesi Pagi |
| **Jumat** | 12.00 WIB | Sesi Siang |
| **Sabtu** | 20.00 WIB | Sesi Malam |
| **Minggu** | **TUTUP** | Libur Layanan |

---

## 🌟 Fitur Utama Sistem

### 1. Sistem Pengajuan Media Partner via Telegram (@PATNERASCHENBOT)
- **Metode Pengajuan Forward Message:** Media Partner meneruskan pesan poster langsung dari channel publik penyelenggara.
- **Validasi Teks 100% Identik:** Sistem memeriksa bahwa teks/caption poster tidak diedit, dimodifikasi, atau dipotong.
- **Perlindungan Anti-Flood Spam:** Mencegah pengiriman beruntun dan menjaga keamanan bot.

### 2. Sistem Autentikasi Admin MTProto 4-Tahap
- **Tahap 1:** Input nomor telepon akun Telegram admin.
- **Tahap 2:** Verifikasi kode OTP resmi Telegram via MTProto.
- **Tahap 3:** Verifikasi Two-Step Verification (2FA password) jika akun admin mengaktifkan 2FA.
- **Tahap 4:** Login Berhasil, menampilkan Device ID, waktu login, dan status aktif.

### 3. Sistem Pelaporan Chat Otomatis
- Setiap pengajuan poster secara otomatis dikirimkan ke Chat Pelaporan Admin (`-1004479248551`).
- Dilengkapi tombol interaktif:
  - `✅ Terima Pengajuan`
  - `❌ Tolak Pengajuan`
  - `📌 Tandai Selesai`

### 4. Website Portal & Dashboard Admin
- **Halaman Depan (Public):** Menampilkan status bot, jam operasional, jadwal publikasi resmi, dan panduan kerja sama media partner.
- **Portal Admin:** Terlindungi password (`aschen2026`), memungkinkan pengelolaan antrean poster, melihat perangkat MTProto aktif, mengganti chat tujuan, dan memeriksa status webhook Telegram.

---

## 🚀 Cara Menjalankan & Deploy

### A. Deploy ke Vercel (Serverless Terpisah)
1. Import repository `bittersheet-debug/ASCHENPATNER` ke Vercel.
2. Tambahkan Environment Variables:
   - `BOT_TOKEN`: `9068758227:AAEOuuxsLvDznlEvAqjgQ-H8jafPg15XHv4`
   - `ADMIN_PASSWORD`: `aschen2026`
   - `CHANNEL_USERNAME`: `@ASCHENEO`
3. Klik **Deploy**.
4. Daftarkan webhook dengan membuka:
   `https://<DOMAIN-VERCEL>/api/mediapatner-setup-webhook`

### B. Menjalankan Server Lokal / VPS
```bash
# Install dependensi
pip install -r requirements.txt
npm install

# Menjalankan bot & website
python main.py
# Atau menjalankan server web Node.js
npm start
```

---

## 📂 Struktur Proyek
```text
├── api/
│   ├── mediapatner_webhook.py      # Vercel Serverless Webhook Handler
│   ├── mediapatner_setup.py        # 1-Click Telegram Webhook Registration
│   ├── mediapatner_api.py          # REST API untuk Website & Telemetry
│   └── mediapatner_cron.py         # Vercel Cron Auto-Publisher
├── mediapatner/
│   ├── bot.py                      # Inisialisasi Bot Telegram aiogram 3
│   ├── config.py                   # Manajemen Konfigurasi & Environment
│   ├── database/                   # SQLite, WAL Mode, Vercel Blob Sync
│   ├── handlers/                   # Handlers User & Admin MTProto
│   ├── keyboards/                  # Inline & Reply Keyboards
│   ├── middlewares/                # Logging & Rate Limiter
│   └── services/                   # Scheduler, Publisher, Report Service
├── public/                         # Website & Admin Portal Media Partner
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── src/public/                     # Mirror Assets untuk Node.js Express
├── main.py                         # Local Bot Polling Daemon
├── server.js                       # Express Web Server
├── vercel.json                     # Konfigurasi Vercel & Cron Jobs
└── DEPLOY_VERCEL.md                # Panduan Deploy Vercel Lengkap
```

---
*With Love, ASCHEN EVENT ORGANIZER.*  
*Telegram: [@ASCHENEO](https://t.me/ASCHENEO) | Bot: [@PATNERASCHENBOT](https://t.me/PATNERASCHENBOT)*
