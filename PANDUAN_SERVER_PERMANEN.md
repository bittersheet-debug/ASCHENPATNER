# 𓄲 PANDUAN MENJALANKAN SERVER / BOT SECARA PERMANEN (24/7)
### ASCHEN EVENT ORGANIZER — MEDIAPATNER BOT

Panduan ini berisi metode lengkap untuk menjalankan bot Telegram **MEDIAPATNER BOT** secara **permanen, stabil, dan otomatis pulih jika terjadi error atau restart (Auto-Recovery & Auto-Restart)**.

---

## 📌 DAFTAR ISI
1. [Metode 1: Di Laptop / PC Windows (Lokal - 100% Gratis)](#metode-1-di-laptop--pc-windows-lokal)
2. [Metode 2: Di Cloud VPS Linux Ubuntu (Rekomendasi 24/7 Tanpa Perlu Laptop Hidup)](#metode-2-di-cloud-vps-linux-ubuntu-rekomendasi-247)
3. [Metode 3: Di Cloud PaaS (Railway / Render / Docker)](#metode-3-di-cloud-paas-railway--render)

---

## METODE 1: DI LAPTOP / PC WINDOWS (LOKAL)

Kami telah membuatkan sistem otomatis lengkap berbasis file `.bat` dan `.vbs` di folder proyek Anda:

### File yang Tersedia:
| Nama File | Fungsi |
| :--- | :--- |
| **`service_menu.bat`** | **Menu Utama Kontrol Bot** (Jalankan, Cek Status, Auto-Start, Stop) |
| **`start_background.vbs`** | Menjalankan bot di background **tanpa jendela terminal terbuka** |
| **`run_permanent.bat`** | Watchdog loop yang **otomatis me-restart bot jika crash/error** |
| **`stop_bot.bat`** | Menghentikan bot background secara bersih |
| **`check_status.bat`** | Memeriksa apakah bot sedang online dan membaca log terakhir |
| **`setup_autostart.bat`** | Memasang/menghapus auto-start saat Windows menyala (Boot Startup) |

---

### Cara Mengaktifkan (Mudah & Cepat):

#### Langkah 1: Buka Menu Utama
Klik ganda file **`service_menu.bat`**. Tampil menu:
```text
======================================================================
   MEDIAPATNER BOT - ASCHEN EVENT ORGANIZER
   PUSAT PENGENDALIAN LAYANAN PERMANEN (24/7)
======================================================================

 STATUS SAAT INI : [ NONAKTIF / OFFLINE ]
 AUTO-START BOOT : [ NONAKTIF ]
======================================================================

 PILIH MENU TINDAKAN:

  [1] Jalankan Bot di Background (Permanen + Auto-Restart jika crash)
  [2] Jalankan Bot dengan Jendela Terbuka (Mode Monitor / Debug)
  [3] Hentikan Bot (Stop Background)
  [4] Cek Status & Baca 15 Log Terakhir
  [5] Atur Auto-Start Saat Windows Menyala (Boot Startup)
  [6] Buka File Log Lengkap (data\bot_runtime.log)
  [0] Keluar dari Menu
```

#### Langkah 2: Jalankan Bot di Background
- Ketik angka **`1`** lalu tekan **Enter**.
- Bot akan langsung aktif berjalan di latar belakang (background) secara diam-diam tanpa ada jendela hitam command prompt yang mengganggu.

#### Langkah 3: Pasang Auto-Start (Agar Otomatis Nyala Saat Komputer Dihidupkan)
- Ketik angka **`5`** lalu pilih **`1`** (Pasang Auto-Start).
- File peluncur otomatis didaftarkan ke folder Startup Windows (`shell:startup`).
- **Hasil:** Setiap kali komputer atau laptop Anda dinyalakan/reboot, bot akan langsung otomatis menyala di background!

---

## METODE 2: DI CLOUD VPS LINUX UBUNTU (REKOMENDASI 24/7)

> [!NOTE]
> Jika laptop Anda dimatikan atau sleep, metode lokal tentu tidak dapat menerima sinyal internet. Untuk bot bisnis resmi seperti ASCHEN EVENT ORGANIZER yang harus selalu aktif 24 jam sehari bahkan saat admin tidur atau laptop mati, menggunakan **VPS Cloud (Linux Ubuntu)** adalah solusi terbaik. Biaya VPS sangat murah (mulai Rp 30.000 - Rp 50.000 per bulan di IDCloudHost, DomaiNesia, Biznet Gio, atau DigitalOcean).

Kami sudah menyediakan file service resmi: **`mediapatner.service`**.

### Langkah Pemasangan di VPS:

1. **Upload folder proyek ke VPS** (misal ke direktori `/var/www/cheneoasv`):
   ```bash
   mkdir -p /var/www/cheneoasv
   cd /var/www/cheneoasv
   ```

2. **Install Python & Dependencies di VPS**:
   ```bash
   sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
   pip3 install -r requirements.txt
   ```

3. **Pastikan file `.env` sudah terisi**:
   ```bash
   nano .env
   ```
   Isi konfigurasi bot token dan channel Anda.

4. **Pasang Layanan `systemd` Permanen**:
   ```bash
   sudo cp mediapatner.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable mediapatner
   sudo systemctl start mediapatner
   ```

5. **Cek Status**:
   ```bash
   sudo systemctl status mediapatner
   ```
   Bot Anda kini resmi **HIDUP PERMANEN 24/7**. Jika server VPS reboot atau bot mengalami network glitch, Linux `systemd` akan otomatis menyalakan ulang bot dalam 5 detik.

---

## METODE 3: DI CLOUD PAAS (RAILWAY / RENDER)

Kami juga telah menyediakan:
- **`Dockerfile`**
- **`Procfile`**

Jika menggunakan [Railway.app](https://railway.app):
1. Push proyek ini ke repository GitHub pribadi Anda.
2. Buka Railway -> **New Project** -> **Deploy from GitHub repo**.
3. Tambahkan Environment Variable di dashboard Railway:
   - `BOT_TOKEN`
   - `ADMIN_PASSWORD`
   - `CHANNEL_USERNAME`
   - `NOTIFICATION_CHANNEL_ID`
   - `TIMEZONE`
4. Railway akan otomatis mendeteksi `Dockerfile` atau `Procfile` dan menjalankan bot 24/7 secara gratis/cloud.
