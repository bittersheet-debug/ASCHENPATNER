# 𓄲 PANDUAN DEPLOY VERCEL TERPISAH — ASCHEN MEDIA PARTNER
*ASCHEN EVENT ORGANIZER — "Elegant Collaboration, Memorable Celebration"*

Panduan ini digunakan untuk mendeploy sistem **Website & Bot Telegram Media Partner ASCHEN (@PATNERASCHENBOT)** ke project Vercel yang baru dan terpisah (misalnya: `aschenpatner.vercel.app`).

---

## 1. Persiapan Repository GitHub

Pastikan seluruh kode telah berada di repository GitHub:
`https://github.com/bittersheet-debug/ASCHENPATNER`

---

## 2. Cara Deploy ke Project Vercel Baru

1. Buka [Vercel Dashboard](https://vercel.com/dashboard).
2. Klik tombol **"Add New..."** ➔ **"Project"**.
3. Pada bagian **"Import Git Repository"**, cari dan pilih repository:
   **`bittersheet-debug/ASCHENPATNER`**
4. Pada form konfigurasi:
   - **Project Name**: Masukkan nama project (contoh: `aschenpatner` atau `aschen-media-partner`).
   - **Framework Preset**: Pilih **Other** (atau biarkan default).
   - **Root Directory**: `./` (biarkan default root).
5. Buka bagian **"Environment Variables"** dan tambahkan variabel berikut:

| Nama Variabel | Nilai / Contoh | Keterangan |
|---|---|---|
| `BOT_TOKEN` | `9068758227:AAEOuuxsLvDznlEvAqjgQ-H8jafPg15XHv4` | Token Bot Telegram Media Partner resmi dari @BotFather |
| `ADMIN_PASSWORD` | `aschen2026` | Kata sandi untuk login Dashboard Admin dan `/admin` |
| `CHANNEL_USERNAME` | `@ASCHENEO` | Channel siaran resmi publikasi poster |
| `BLOB_READ_WRITE_TOKEN` | *(Opsional / Dari Tab Storage Vercel)* | Token penyimpanan cloud Vercel Blob untuk persistensi database SQLite |

6. Klik tombol **"Deploy"**.
7. Tunggu 1–2 menit hingga Vercel selesai melakukan build dan status menjadi **Ready**.

---

## 3. Menghubungkan Webhook Telegram (1-Klik Saja)

Setelah Vercel selesai mendeploy dan memberikan URL domain (contoh: `https://aschenpatner.vercel.app`):

1. Buka browser Anda dan akses endpoint pendaftaran webhook:
   ```
   https://<DOMAIN-VERCEL-ANDA>/api/mediapatner-setup-webhook
   ```
   *Contoh:*
   `https://aschenpatner.vercel.app/api/mediapatner-setup-webhook`

2. Browser akan menampilkan respon:
   ```json
   {
     "success": true,
     "webhook_url": "https://aschenpatner.vercel.app/api/mediapatner-webhook",
     "telegram": {
       "ok": true,
       "result": true,
       "description": "Webhook was set"
     },
     "message": "Webhook MEDIAPATNER BOT berhasil disetel..."
   }
   ```
3. Bot Telegram `@PATNERASCHENBOT` kini telah aktif dan terhubung permanen secara serverless ke server Vercel Anda!

---

## 4. Fitur Website & Dashboard yang Aktif

- **Beranda Website**: `https://<DOMAIN-VERCEL-ANDA>/`
  - Informasi jam operasional (Senin–Sabtu aktif mulai 06.00 WIB, Minggu TUTUP).
  - Jadwal resmi publikasi poster (Selasa/Kamis 09.00, Rabu/Jumat 12.00, Sabtu 20.00 WIB).
  - Panduan Media Partner (Forward pesan asli dari channel tanpa edit caption).
  - Live status telemetry bot online.
- **Admin Portal**:
  - Tombol **"Admin Portal"** di pojok kanan atas navbar.
  - Masukkan password: `aschen2026`.
  - Mengelola daftar request poster, menyetujui, menolak, atau menandai selesai.
  - Melihat status perangkat MTProto yang login.
  - Mengubah chat tujuan pelaporan (default: `-1004479248551`).

---

## 5. Sinkronisasi Database Cloud (Vercel Blob)

Untuk menyimpan data request poster dan riwayat secara permanen di serverless Vercel:
1. Pada project Vercel Anda, klik tab **"Storage"**.
2. Klik **"Create Database"** ➔ Pilih **"Blob"**.
3. Klik **"Create Blob Store"** (nama bebas, misalnya `mediapatner-store`).
4. Vercel secara otomatis akan menambahkan environment variable `BLOB_READ_WRITE_TOKEN` ke project Anda.
5. Lakukan **Redeploy** sekali. Sistem bot otomatis melakukan backup dan restore database SQLite setiap ada request baru!
