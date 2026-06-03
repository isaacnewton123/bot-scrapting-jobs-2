"""
storage.py — Upload gambar ke R2 dan simpan data ke MongoDB.

Berisi:
- upload_image_to_r2()  : Upload gambar loker ke Cloudflare R2
- save_to_mongodb()     : Upsert data lowongan ke MongoDB Atlas
"""

from __future__ import annotations

import urllib.request
from datetime import datetime
from typing import Optional

import boto3
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from config import (
    HTTP_HEADERS,
    MONGODB_COLLECTION_NAME,
    MONGODB_DB_NAME,
    MONGODB_URI,
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET_NAME,
    R2_PUBLIC_DOMAIN,
    R2_SECRET_ACCESS_KEY,
    r2_is_configured,
)
from logger import get_logger
from models import JobData

logger = get_logger(__name__)


# ─── R2 Upload ────────────────────────────────────────────────────────────────

def upload_image_to_r2(image_url: str, slug: str) -> Optional[str]:
    """Download gambar dari URL dan upload ke Cloudflare R2.
    
    Args:
        image_url: URL gambar sumber (biasanya og:image dari BukaJobs).
        slug: Slug lowongan untuk dijadikan nama file.
        
    Returns:
        URL publik gambar di R2, atau None jika gagal.
    """
    if not r2_is_configured():
        logger.warning("Kredensial R2 tidak lengkap. Upload gambar dilewati.")
        return None

    try:
        import re
        # Hapus prefix CDN Jetpack (i0.wp.com, dll) agar mendownload langsung dari server asli
        # yang tidak nge-block IP datacenter Render
        clean_url = re.sub(r'^https?://i[0-9]\.wp\.com/', 'https://', image_url)
        
        logger.info(f"Mendownload gambar: {clean_url}")
        req = urllib.request.Request(clean_url, headers=HTTP_HEADERS)
        with urllib.request.urlopen(req) as response:
            image_data: bytes = response.read()
            content_type: str = response.headers.get("Content-Type", "image/jpeg")

            # Tentukan ekstensi file
            ext: str = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"

            filename: str = f"{slug}{ext}"
            logger.info(f"Mengupload ke R2: {filename} ({len(image_data)} bytes)")

            s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            )

            s3.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=filename,
                Body=image_data,
                ContentType=content_type,
            )

            # Bangun URL publik
            public_url: str = R2_PUBLIC_DOMAIN or ""
            if not public_url.startswith("http"):
                public_url = "https://" + public_url
            if not public_url.endswith("/"):
                public_url += "/"

            final_url: str = f"{public_url}{filename}"
            logger.info(f"Upload R2 berhasil: {final_url}")
            return final_url

    except Exception as e:
        logger.error(f"Gagal upload gambar ke R2: {e}", exc_info=True)
        return None


# ─── MongoDB Save ─────────────────────────────────────────────────────────────

def save_to_mongodb(data: JobData) -> bool:
    """Upsert data lowongan ke MongoDB Atlas berdasarkan original_url.
    
    Args:
        data: JobData berisi data lowongan yang sudah diproses.
        
    Returns:
        True jika berhasil, False jika gagal.
    """
    if not MONGODB_URI:
        logger.error("MONGODB_URI belum diset di .env. Penyimpanan dibatalkan.")
        return False

    original_url: str = data.get("original_url", "")
    if not original_url:
        logger.error("original_url tidak ditemukan dalam data. Penyimpanan dibatalkan.")
        return False

    try:
        # Tambah timestamp
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        if "created_at" not in data:
            data["created_at"] = data["updated_at"]

        logger.info(f"Menyimpan ke MongoDB: {original_url}")
        client: MongoClient = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
        db = client[MONGODB_DB_NAME]
        collection = db[MONGODB_COLLECTION_NAME]

        result = collection.update_one(
            {"original_url": original_url},
            {"$set": data},
            upsert=True,
        )

        if result.upserted_id:
            logger.info(f"Loker BARU disimpan ke MongoDB. ID: {result.upserted_id}")
        else:
            logger.info(f"Loker LAMA di-update di MongoDB: {original_url}")

        client.close()
        return True

    except Exception as e:
        logger.error(f"Gagal menyimpan ke MongoDB: {e}", exc_info=True)
        return False
