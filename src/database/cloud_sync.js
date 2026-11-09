/**
 * ASCHEN EVENT ORGANIZER - Cloud State & Database Synchronizer
 * Automatically synchronizes bookings and SQLite state across Vercel serverless containers
 * using Vercel Blob with static read-write token.
 */

const fs = require('fs');
const path = require('path');

let blobModule = null;
try {
  blobModule = require('@vercel/blob');
} catch (e) {
  blobModule = null;
}

const BLOB_FILENAME = 'aschen_booking_cloud.db';
let isSyncing = false;
let pendingSync = false;
let lastRestoredEtag = null;
let lastCheckTime = 0;

/**
 * Downloads and restores the SQLite database from Vercel Blob if a newer snapshot exists.
 * @param {string} resolvedDbPath - Path to local SQLite file
 * @param {Function} [onReload] - Callback invoked when a new snapshot is restored
 * @param {boolean} [force] - If true, bypasses the 2s throttle check
 * @returns {Promise<boolean>}
 */
async function syncFromCloud(resolvedDbPath, onReload, force = false) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!blobModule || !token) return false;

  const now = Date.now();
  if (!force && now - lastCheckTime < 2000 && lastRestoredEtag) {
    return false;
  }
  lastCheckTime = now;

  try {
    const { list } = blobModule;
    const { blobs } = await list({ prefix: BLOB_FILENAME, limit: 1, token });
    if (!blobs || blobs.length === 0) {
      return false;
    }

    const targetBlob = blobs.find(b => b.pathname === BLOB_FILENAME) || blobs[0];
    if (targetBlob && targetBlob.downloadUrl) {
      // If the cloud blob has the same etag as our local memory, no need to redownload
      if (lastRestoredEtag && targetBlob.etag === lastRestoredEtag) {
        return false;
      }

      const res = await fetch(targetBlob.downloadUrl, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (res.ok) {
        const buffer = await res.arrayBuffer();
        fs.writeFileSync(resolvedDbPath, Buffer.from(buffer));
        lastRestoredEtag = targetBlob.etag;
        console.log(`[CloudSync] Database dipulihkan dari Vercel Blob (${buffer.byteLength} bytes, etag: ${targetBlob.etag}). Data permanen siap.`);
        if (typeof onReload === 'function') {
          onReload();
        }
        return true;
      } else {
        console.warn(`[CloudSync] Peringatan download blob (HTTP ${res.status})`);
      }
    }
  } catch (err) {
    console.warn('[CloudSync] Peringatan unduh cloud DB:', err.message);
  }
  return false;
}

/**
 * Commits SQLite WAL to file and snapshots the database to Vercel Blob.
 * @param {string} resolvedDbPath - Path to local SQLite file
 * @param {object} [dbInstance] - better-sqlite3 database instance
 * @returns {Promise<boolean>}
 */
async function syncToCloud(resolvedDbPath, dbInstance) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!blobModule || !token) return false;
  if (!fs.existsSync(resolvedDbPath)) return false;

  if (isSyncing) {
    pendingSync = true;
    return false;
  }

  isSyncing = true;
  try {
    // Flush WAL checkpoint to main DB file before snapshotting
    if (dbInstance && dbInstance.open) {
      try {
        dbInstance.pragma('wal_checkpoint(TRUNCATE)');
      } catch (e) {
        // Ignored if busy
      }
    }

    const { put } = blobModule;
    const data = fs.readFileSync(resolvedDbPath);
    const blob = await put(BLOB_FILENAME, data, {
      access: 'private',
      allowOverwrite: true,
      addRandomSuffix: false,
      token
    });

    if (blob && blob.etag) {
      lastRestoredEtag = blob.etag;
    }
    console.log(`[CloudSync] Data permanen berhasil disimpan ke Vercel Blob (${data.length} bytes, etag: ${blob.etag}).`);
    return true;
  } catch (err) {
    console.warn('[CloudSync] Peringatan simpan cloud DB:', err.message);
    return false;
  } finally {
    isSyncing = false;
    if (pendingSync) {
      pendingSync = false;
      syncToCloud(resolvedDbPath, dbInstance).catch(() => {});
    }
  }
}

module.exports = {
  syncFromCloud,
  syncToCloud
};
