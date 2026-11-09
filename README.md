# 𓄲 ASCHEN EVENT ORGANIZER — BOOKING BOT SYSTEM

Sistem Pemesanan Event & Dashboard Operasional Terpadu untuk Telegram Bot **ASCHEN EVENT ORGANIZER | BOOKING BOT**.

---

## 💎 Identitas Visual & Branding
* **Nama Sistem:** ASCHEN EVENT ORGANIZER | BOOKING BOT
* **Identitas Visual:** `𓄲`, `➤`, `ᵎ!ᵎ`, dan `@ASCHENEO`
* **Channel Resmi:** `@ASCHENOFFICIAL`
* **Jadwal Acara Resmi:** [https://t.me/JadwalAschen/2](https://t.me/JadwalAschen/2)
* **Daftar Guest Star Resmi:** [https://t.me/ASCHENOFFICIAL/7](https://t.me/ASCHENOFFICIAL/7)
* **Link Ruang Reservasi & Pertemuan:** [https://t.me/+NHhPUT9PqVw5YzIx](https://t.me/+NHhPUT9PqVw5YzIx)

---

## 🌟 Fitur Utama Sistem

### 1. 6 Kategori Formulir Booking Resmi
1. 💍 **Wedding Party** (Maksimal 2 Guest Star)
2. 🎂 **Birthday Party** (Maksimal 2 Guest Star)
3. 🥂 **Engagement Party** (Maksimal 2 Guest Star)
4. 👨‍👩‍👦 **Mensive Family / Couple** (Maksimal 2 Guest Star)
5. 👑 **Mensive Channel VVIP** (Maksimal 2 Guest Star)
6. 🎓 **Promnight / Graduation** (Maksimal 3 Guest Star)

### 2. Sistem Percakapan Bertahap (Conversational Wizard)
* Bot menanyakan satu pertanyaan pada satu waktu.
* Dilengkapi tombol navigasi di setiap pertanyaan:
  * `⬅️ KEMBALI` — Mengubah jawaban pada pertanyaan sebelumnya.
  * `⏩ LEWATI` — Untuk pertanyaan opsional/catatan.
  * `❌ BATALKAN` — Membatalkan pengisian formulir secara aman.
* Validasi otomatis (format tanggal `DD/MM/YYYY`, username `@username`, tautan channel Telegram, dll.).
* Penyimpanan sesi sementara yang tahan restart/gangguan.

### 3. Fitur Otomatis Guest Star & Song
* Tombol **`🎤 LIHAT DAFTAR GUEST STAR`** muncul secara otomatis sebelum mengisi nama Guest Star.
* Berupa **Inline Keyboard URL Button** langsung ke `https://t.me/ASCHENOFFICIAL/7`.
* Mematuhi batasan kuota:
  * Maksimal 2 Guest Star untuk Wedding, Birthday, Engagement, Mensive Family/Couple, dan Mensive Channel VVIP.
  * Maksimal 3 Guest Star untuk Promnight / Graduation.
* Pertanyaan Guest Star kedua dan ketiga bersifat kondisional dan hanya muncul sesuai pilihan jumlah Guest Star pengguna.

### 4. Preview Formulir & Mode Koreksi
* Menampilkan pratinjau lengkap dengan dekorasi resmi ASCHEN sebelum data dikirimkan.
* Pilihan tindakan:
  * `📩 KIRIM FORMULIR` — Menerbitkan Booking ID dan mencatat data permanen ke database.
  * `✏️ EDIT FORMULIR` — Memilih bagian spesifik pertanyaan untuk diperbaiki langsung.
  * `❌ BATALKAN` — Menghapus draft pemesanan.
* Pilihan dan kolom opsional yang tidak terisi dihapus secara otomatis dari pratinjau agar hasil tetap rapi dan aesthetic.

### 5. Booking ID & Database Permanen
* Pembuatan ID unik otomatis (contoh: `ASC-WED-2611-1981`, `ASC-BDY-2611-3605`).
* Database permanen **SQLite** dengan Write-Ahead Logging (WAL mode).
* Menjaga integritas data saat server atau bot restart.
* Audit trail lengkap pada setiap perubahan status.

### 6. Sembilan (9) Status Resmi Booking
1. `Formulir Terkirim`
2. `Menunggu Balasan Admin`
3. `Booking Diterima`
4. `Booking Ditolak`
5. `Menunggu Reservasi Tempat`
6. `Reservasi Tempat Tercatat`
7. `Booking Dikonfirmasi`
8. `Booking Selesai`
9. `Booking Dibatalkan`

### 7. Dashboard Khusus Admin (Web UI + Real-Time WebSocket)
* **URL:** `http://localhost:3000`
* **Akun Default:** Username `admin` | Password `aschen2026`
* **Fitur Dashboard:**
  * 📊 **Ringkasan:** Total booking, pending, dikonfirmasi, selesai, dan statistik per kategori.
  * 📋 **Daftar Booking:** Filter status, kategori, dan pencarian cepat (Booking ID, nama, @username).
  * 🔍 **Detail Booking:** Melihat format resmi ASCHEN, menyalin teks format, mengubah status, memperbarui tanggal acara.
  * 🏨 **Kirim Formulir Reservasi Tempat:** Mengirimkan formulir interaktif langsung ke Telegram pemesan dengan sekali klik.
  * 💬 **Komunikasi Dua Arah:** Chat interaktif langsung antara Admin dan Pemesan dari dashboard.
  * 📅 **Jadwal Acara:** Agenda timeline acara yang telah disetujui.
  * ⏰ **Pesan Otomatis:** Pemantau status pengiriman ucapan terima kasih 19:00 WIB + tombol uji coba kirim instan.
  * 👥 **Kelola Admin:** Menambah admin baru dan mengatur hak akses.

### 8. Sistem Reservasi Ruang Pertemuan (Bukan Formulir)
* Reservasi tempat merupakan **tautan langsung ke ruang pertemuan**: `https://t.me/+NHhPUT9PqVw5YzIx`.
* Setelah booking disetujui, Admin dapat menekan tombol **"Kirim Link Ruang Pertemuan"** di Dashboard Admin.
* Pelanggan menerima undangan resmi dengan tombol URL **`🏨 GABUNG RUANG PERTEMUAN`** langsung ke tautan ruang pertemuan.
* Pelanggan dapat menekan tombol **`✅ Konfirmasi Sudah Bergabung`** untuk memperbarui status menjadi `Reservasi Tempat Tercatat`.

### 9. Notifikasi Otomatis ke Channel / Group Telegram
* Cukup undang bot `@ASCHENBOOKBOT` ke dalam **Channel** atau **Group** Anda sebagai **Administrator**.
* Bot akan otomatis mendeteksi, mencatat channel, dan mengirimkan pesan konfirmasi sambutan.
* Setiap kali ada formulir booking baru yang dikirimkan oleh pelanggan, bot akan **otomatis mengirimkan rincian lengkap booking** ke channel tersebut secara *real-time*.
* Tersedia panel pengelola saluran dan tombol uji coba kirim notifikasi di Dashboard Admin.

### 9. Komunikasi Dua Arah (Admin & Pelanggan)
* Admin membalas pesan pelanggan langsung dari dashboard.
* Pesan masuk ke Telegram bot pemesan dengan rujukan Booking ID yang tepat.
* Pelanggan dapat membalas pesan atau mengirim info tambahan melalui tombol `💬 Balas Pesan Admin`.
* Pesan terisolasi ketat sesuai Booking ID (mencegah salah kirim antar booking).

### 10. Pengiriman Ucapan Terima Kasih Otomatis (19:00 WIB)
* Begitu booking disetujui (`Booking Diterima` atau `Booking Dikonfirmasi`), jadwal pengiriman otomatis dibuat untuk **tanggal acara pukul 19:00 WIB (UTC+7)**.
* Berjalan di latar belakang tanpa tindakan manual admin pada hari H.
* Jika tanggal acara diubah, jadwal diperbarui secara otomatis.
* Jika pesan gagal terkirim (misal pemesan memblokir bot), status dicatat gagal dan notifikasi peringatan dikirimkan ke admin.
* Teks resmi yang dikirim:
```
𓄲 ASCHEN EVENT ORGANIZER

Terima kasih telah memilih dan mempercayakan momen spesial Anda kepada ASCHEN EVENT ORGANIZER.

Merupakan suatu kehormatan bagi kami untuk menjadi bagian dari hari istimewa Anda.

Semoga kebahagiaan, kenangan indah, dan kesan terbaik selalu menyertai Anda.

With Love,
ASCHEN EVENT ORGANIZER.
```

---

## 🚀 Panduan Menjalankan Sistem

### 1. Konfigurasi Lingkungan (.env)
Buka file `.env` di direktori proyek dan atur token bot Telegram Anda:
```env
# Masukkan token bot dari @BotFather
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Port Admin Dashboard
PORT=3000

# Akun Login Admin Dashboard
ADMIN_DEFAULT_USER=admin
ADMIN_DEFAULT_PASS=aschen2026

# ID Numerik Telegram Admin (pisahkan koma jika lebih dari satu)
ADMIN_TELEGRAM_IDS=123456789

# Secret key untuk JWT
JWT_SECRET=aschen-secret-event-organizer-2026

# Path Database SQLite
DB_PATH=./data/aschen_booking.db
```

### 2. Menjalankan Aplikasi
Jalankan perintah berikut:
```bash
npm start
```
Atau:
```bash
node server.js
```

### 3. Mengakses Dashboard Admin
Buka browser dan kunjungi:
👉 `http://localhost:3000`
* **Username:** `admin`
* **Password:** `aschen2026`

### 4. Perintah Bot Telegram
* `/start` — Menampilkan pesan sambutan mewah dan 6 tombol kategori pemesanan.
* `/status` — Memeriksa daftar dan rincian pemesanan milik akun pengguna.
* `/batal` — Membatalkan pengisian formulir yang sedang aktif.
* `/help` — Menampilkan bantuan dan kontak resmi ASCHEN.
* `/admin` — Panel ringkasan untuk admin resmi di Telegram.

---

## 🧪 Pengujian Sistem
Sistem telah dilengkapi dengan test suite lengkap untuk memverifikasi 100% fungsionalitas:
```bash
npm test
```
Semua 12 unit & integrasi tes mencakup validasi formulir 6 kategori, batasan guest star, URL resmi, format preview, SQLite WAL transactions, 9 status booking, reservasi tempat, 2-way chat, dan automated 19:00 WIB scheduler.

---

## 🌐 Panduan Deploy ke VERCEL & Pasang Custom Domain

Sistem ini telah dikonfigurasi penuh (**Serverless Ready**) untuk di-deploy ke **Vercel** dengan dukungan **Custom Domain**, **Telegram Webhook**, dan **Vercel Cron Jobs**.

### Langkah 1: Push Proyek ke GitHub
1. Buat repository baru di GitHub (misal: `aschen-booking-bot`).
2. Di folder proyek, jalankan:
```bash
git init
git add .
git commit -m "feat: ASCHEN Booking Bot & Admin Dashboard Vercel Ready"
git branch -M main
git remote add origin https://github.com/USERNAME/aschen-booking-bot.git
git push -u origin main
```

---

### Langkah 2: Import Proyek ke Vercel
1. Masuk ke dashboard [vercel.com](https://vercel.com).
2. Klik tombol **"Add New..."** lalu pilih **"Project"**.
3. Hubungkan akun GitHub Anda dan pilih repository `aschen-booking-bot`.
4. Di bagian **Environment Variables**, tambahkan variabel berikut:
   * `BOT_TOKEN`: `9136985528:AAHUyI2NMUWWU8JuT3ogDTMFCUNkcW3pdjs` (atau token bot Anda)
   * `ADMIN_DEFAULT_USER`: `admin`
   * `ADMIN_DEFAULT_PASS`: `aschen2026` (atau password rahasia Anda)
   * `JWT_SECRET`: `aschen-secret-key-super-2026`
5. Klik **"Deploy"**. Tunggu 1–2 menit hingga build selesai.

---

### Langkah 3: Pasang Custom Domain Anda di Vercel
1. Di halaman proyek Vercel Anda, buka menu **Settings** > **Domains**.
2. Masukkan domain atau subdomain yang Anda miliki (contoh: `booking.aschendomain.com` atau `aschendomain.com`).
3. Vercel akan memberikan petunjuk DNS:
   * **Untuk Subdomain** (contoh: `booking.aschendomain.com`):
     * **Type:** `CNAME`
     * **Name:** `booking`
     * **Value:** `cname.vercel-dns.com`
   * **Untuk Root Domain** (contoh: `aschendomain.com`):
     * **Type:** `A`
     * **Name:** `@`
     * **Value:** `76.76.21.21`
4. Buka panel DNS registrar domain Anda (Cloudflare, Niagahoster, Domainesia, Namecheap, GoDaddy, dll.) dan masukkan DNS Record di atas.
5. Setelah DNS terverifikasi (biasanya 1–10 menit), domain Anda akan berstatus **Valid Configuration** dan ber-SSL HTTPS otomatis dari Vercel!

---

### Langkah 4: Sambungkan Webhook Telegram (1 Kali Klik!)
Setelah website dapat dibuka lewat domain kustom Anda (misal `https://booking.aschendomain.com`):

**Opsi A (Melalui Dashboard Admin - Paling Praktis):**
1. Buka `https://booking.aschendomain.com` di browser Anda.
2. Login dengan akun admin.
3. Buka tab **"Manajemen Admin"** di menu samping.
4. Pada panel **"Pengaturan Domain & Webhook Telegram"**, klik tombol emas **"🔗 Sambungkan Webhook ke Domain Ini"**.
5. Selesai! Bot Telegram langsung terhubung ke domain Anda!

**Opsi B (Melalui URL Browser Langsung):**
Cukup buka alamat ini di browser Anda:
```
https://domain-kustom-anda.com/api/setup-webhook
```
Telegram akan otomatis merespons:
```json
{
  "success": true,
  "message": "✅ Webhook Telegram berhasil dihubungkan ke: https://domain-kustom-anda.com/api/webhook"
}
```

---

### Langkah 5: Pesan Ucapan Terima Kasih 19:00 WIB (Vercel Cron)
File `vercel.json` telah dikonfigurasi untuk mengeksekusi cron check setiap menit:
```json
{
  "crons": [
    {
      "path": "/api/cron/check-messages",
      "schedule": "* * * * *"
    }
  ]
}
```
Setiap booking yang tanggal acaranya jatuh tempo, sistem akan otomatis mengirimkan ucapan terima kasih pada pukul **19:00 WIB** tanpa perlu intervensi manual!

---

*With Love,*  
**ASCHEN EVENT ORGANIZER.**  
*@ASCHENEO*
