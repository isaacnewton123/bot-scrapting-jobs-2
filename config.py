"""
config.py — Konfigurasi terpusat untuk seluruh bot.

Load .env sekali, validasi variabel wajib, dan export sebagai konstanta bertipe.
Semua modul lain cukup: `from config import GEMINI_API_KEY, MONGODB_URI, ...`
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# ─── Load .env ────────────────────────────────────────────────────────────────

_ENV_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ[_key.strip()] = _val.strip().strip("\"'")

# ─── Telegram ─────────────────────────────────────────────────────────────────

TELEGRAM_API_ID: Optional[str] = os.environ.get("TELEGRAM_API_ID")
TELEGRAM_API_HASH: Optional[str] = os.environ.get("TELEGRAM_API_HASH")
TELEGRAM_CHANNEL: str = os.environ.get("TELEGRAM_CHANNEL", "bukajobs")
TELEGRAM_STRING_SESSION: str = os.environ.get("TELEGRAM_STRING_SESSION", "")

# ─── Gemini AI ────────────────────────────────────────────────────────────────

GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")

GEMINI_MODELS: list[str] = [
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

# ─── Cloudflare R2 ────────────────────────────────────────────────────────────

R2_ACCOUNT_ID: Optional[str] = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID: Optional[str] = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY: Optional[str] = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME: Optional[str] = os.environ.get("R2_BUCKET_NAME")
R2_PUBLIC_DOMAIN: Optional[str] = os.environ.get("R2_PUBLIC_DOMAIN")

def r2_is_configured() -> bool:
    """Return True jika semua credential R2 tersedia."""
    return all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_DOMAIN])

# ─── MongoDB ──────────────────────────────────────────────────────────────────

MONGODB_URI: Optional[str] = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME: str = os.environ.get("MONGODB_DB_NAME", "nyarikerja_db")
MONGODB_COLLECTION_NAME: str = os.environ.get("MONGODB_COLLECTION_NAME", "jobs")

# ─── HTTP ─────────────────────────────────────────────────────────────────────

HTTP_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ─── Path ke .env (untuk auto-save session) ───────────────────────────────────

ENV_PATH: str = _ENV_PATH

# ─── Validasi ─────────────────────────────────────────────────────────────────

def validate_telegram() -> None:
    """Pastikan credential Telegram sudah diset. Exit jika belum."""
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("=" * 70)
        print("ERROR: TELEGRAM_API_ID dan TELEGRAM_API_HASH belum diset di .env")
        print("Dapatkan dari https://my.telegram.org lalu tambahkan ke .env")
        print("=" * 70)
        sys.exit(1)


def validate_gemini() -> None:
    """Peringatan jika GEMINI_API_KEY belum diset."""
    if not GEMINI_API_KEY:
        print("PERINGATAN: GEMINI_API_KEY belum diset. AI rewriting akan dilewati.")


def validate_mongodb() -> None:
    """Peringatan jika MONGODB_URI belum diset."""
    if not MONGODB_URI:
        print("PERINGATAN: MONGODB_URI belum diset. Penyimpanan ke database akan gagal.")
