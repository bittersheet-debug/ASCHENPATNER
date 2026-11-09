/**
 * ASCHEN EVENT ORGANIZER - Cloud State & Database Synchronizer
 * Automatically synchronizes bookings and SQLite state across Vercel serverless containers
 * using Vercel Blob.
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
  if (!IS_VERCEL || !blobModule || !process.env.BLOB_STORE_ID) return false;

  try {
    const { list } = blobModule;
    const { blobs } = await list({ prefix: BLOB_FILENAME, limit: 1 });
    if (!blobs || blobs.length === 0) {
      console.log('[CloudSync] Belum ada snapshot cloud DB di Vercel Blob.');
      return false;
    }

    const targetBlob = blobs.find(b => b.pathname === BLOB_FILENAME) || blobs[0];
    if (targetBlob && targetBlob.url) {
      const res = await fetch(targetBlob.url);
      if (res.ok) {
        const buffer = await res.arrayBuffer();
        fs.writeFileSync(resolvedDbPath, Buffer.from(buffer));
        lastSyncTime = Date.now();
        console.log(`[CloudSync] Berhasil mengunduh snapshot database cloud (${buffer.byteLength} bytes).`);
        return true;
      }
    }
  } catch (err) {
    console.warn('[CloudSync] Peringatan unduh cloud DB:', err.message);
  }
  return false;
}

async function syncToCloud(resolvedDbPath) {
  if (!IS_VERCEL || !blobModule || !process.env.BLOB_STORE_ID || isSyncing) return false;
  if (!fs.existsSync(resolvedDbPath)) return false;

  isSyncing = true;
  try {
    const { put } = blobModule;
    const data = fs.readFileSync(resolvedDbPath);
    await put(BLOB_FILENAME, data, {
      access: 'public',
      addRandomSuffix: false
    });
    lastSyncTime = Date.now();
    console.log(`[CloudSync] Berhasil mengunggah database ke Vercel Blob (${data.length} bytes).`);
    return true;
  } catch (err) {
    console.warn('[CloudSync] Peringatan unggah cloud DB:', err.message);
    return false;
  } finally {
    isSyncing = false;
  }
}

module.exports = {
  syncFromCloud,
  syncToCloud
};
