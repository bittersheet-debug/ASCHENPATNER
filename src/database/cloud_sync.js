/**
 * ASCHEN EVENT ORGANIZER - Cloud State & Database Synchronizer
 * Automatically synchronizes bookings and SQLite state across Vercel serverless containers
 * using Vercel Blob with static read-write token.
 */

const fs = require('fs');
const path = require('path');
const { IS_VERCEL } = require('../../config');

let blobModule = null;
try {
  blobModule = require('@vercel/blob');
} catch (e) {
  blobModule = null;
}

const BLOB_FILENAME = 'aschen_booking_cloud.db';
let isSyncing = false;
let lastSyncTime = 0;

async function syncFromCloud(resolvedDbPath) {
  if (!IS_VERCEL || !blobModule) return false;
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return false;

  try {
    const { list } = blobModule;
    const { blobs } = await list({ prefix: BLOB_FILENAME, limit: 1, token });
    if (!blobs || blobs.length === 0) {
      console.log('[CloudSync] Belum ada snapshot database di Vercel Blob.');
      return false;
    }

    const targetBlob = blobs.find(b => b.pathname === BLOB_FILENAME) || blobs[0];
    if (targetBlob && targetBlob.url) {
      const res = await fetch(targetBlob.url);
      if (res.ok) {
        const buffer = await res.arrayBuffer();
        fs.writeFileSync(resolvedDbPath, Buffer.from(buffer));
        lastSyncTime = Date.now();
        console.log(`[CloudSync] Berhasil memulihkan database dari cloud (${buffer.byteLength} bytes). Data tidak akan hilang!`);
        return true;
      }
    }
  } catch (err) {
    console.warn('[CloudSync] Peringatan unduh cloud DB:', err.message);
  }
  return false;
}

async function syncToCloud(resolvedDbPath, dbInstance) {
  if (!IS_VERCEL || !blobModule || isSyncing) return false;
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return false;
  if (!fs.existsSync(resolvedDbPath)) return false;

  isSyncing = true;
  try {
    // Flush WAL checkpoint to main DB file before upload
    if (dbInstance) {
      try {
        dbInstance.pragma('wal_checkpoint(TRUNCATE)');
      } catch (e) {}
    }

    const { put } = blobModule;
    const data = fs.readFileSync(resolvedDbPath);
    await put(BLOB_FILENAME, data, {
      access: 'public',
      addRandomSuffix: false,
      token
    });
    lastSyncTime = Date.now();
    console.log(`[CloudSync] Data permanen berhasil disimpan ke cloud (${data.length} bytes).`);
    return true;
  } catch (err) {
    console.warn('[CloudSync] Peringatan simpan cloud DB:', err.message);
    return false;
  } finally {
    isSyncing = false;
  }
}

module.exports = {
  syncFromCloud,
  syncToCloud
};
