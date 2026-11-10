"""
Vercel Blob storage synchronizer for MEDIAPATNER BOT.
Enables SQLite database snapshotting and restoring across serverless invocations.
"""

import os
import logging
import urllib.request
import urllib.error
import json

logger = logging.getLogger(__name__)

BLOB_FILENAME = "mediapatner_cloud.db"


def restore_from_blob(db_path: str) -> bool:
    """Restores SQLite database file from Vercel Blob if available."""
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        return False

    try:
        req = urllib.request.Request(
            f"https://blob.vercel-storage.com?prefix={BLOB_FILENAME}&limit=1",
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                blobs = data.get("blobs", [])
                if blobs:
                    download_url = blobs[0].get("downloadUrl")
                    if download_url:
                        dl_req = urllib.request.Request(
                            download_url,
                            headers={"Authorization": f"Bearer {token}"},
                            method="GET",
                        )
                        with urllib.request.urlopen(dl_req, timeout=15) as dl_resp:
                            if dl_resp.status == 200:
                                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
                                with open(db_path, "wb") as f:
                                    f.write(dl_resp.read())
                                logger.info(f"Database restored successfully from Vercel Blob to {db_path}")
                                return True
    except Exception as e:
        logger.warning(f"Could not restore from Vercel Blob: {e}")
    return False


def save_to_blob(db_path: str) -> bool:
    """Uploads a snapshot of the SQLite database to Vercel Blob."""
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token or not os.path.exists(db_path):
        return False

    try:
        with open(db_path, "rb") as f:
            content = f.read()

        req = urllib.request.Request(
            f"https://blob.vercel-storage.com/{BLOB_FILENAME}",
            data=content,
            headers={
                "Authorization": f"Bearer {token}",
                "x-add-random-suffix": "false",
                "x-allow-overwrite": "true",
                "x-content-type": "application/x-sqlite3",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status in (200, 201):
                logger.info(f"Database successfully synced to Vercel Blob ({len(content)} bytes)")
                return True
    except Exception as e:
        logger.warning(f"Could not save to Vercel Blob: {e}")
    return False
