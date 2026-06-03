"""
telegram_listener.py — Telegram channel listener.

Satu tanggung jawab: mendengarkan pesan di channel Telegram,
mengekstrak URL, dan menjalankan pipeline scraping.

Status page dan stats tracking di-import dari modul terpisah.
"""

from __future__ import annotations

import os
import re

from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import (
    ENV_PATH,
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_CHANNEL,
    TELEGRAM_STRING_SESSION,
    validate_telegram,
)
from logger import get_logger
from scrape import process_job_url
from stats import (
    mark_started,
    record_error,
    record_message,
    record_success,
    record_url_found,
    set_channel_name,
)
from status_page import build_status_html
from storage import save_to_mongodb
from models import JobData
import time

logger = get_logger(__name__)

# Cache untuk mencegah duplikasi jika pesan di-edit berulang-ulang
# Format: { "url": timestamp_terakhir_diproses }
PROCESSED_URLS: dict[str, float] = {}

# ─── Validasi ─────────────────────────────────────────────────────────────────

validate_telegram()

# ─── Telegram Client ──────────────────────────────────────────────────────────

client = TelegramClient(
    StringSession(TELEGRAM_STRING_SESSION),
    int(TELEGRAM_API_ID),  # type: ignore[arg-type]
    TELEGRAM_API_HASH,  # type: ignore[arg-type]
)


# ─── Event Handler ────────────────────────────────────────────────────────────

async def on_new_message(event: events.NewMessage.Event) -> None:
    """Handler untuk setiap pesan baru di channel target."""
    message_text: str = event.raw_text or event.text or ""
    record_message()
    logger.info(f"Pesan baru terdeteksi dari channel {TELEGRAM_CHANNEL}!")
    
    # Debug isi pesan (potong jika terlalu panjang agar tidak spam)
    snippet = message_text[:200].replace('\n', ' ')
    logger.info(f"Isi pesan (raw): {snippet}...")

    # Cari URL disnakerja.com
    match = re.search(r"(https://(?:www\.)?disnakerja\.com/[^\s]+)", message_text)
    if not match:
        logger.info("Tidak ada URL Disnakerja di pesan ini. Mengabaikan.")
        return

    url: str = match.group(1).strip()
    current_time = time.time()
    
    # Jika URL pernah diproses dalam 1 jam (3600 detik) terakhir, abaikan (mencegah spam edit)
    if url in PROCESSED_URLS and (current_time - PROCESSED_URLS[url]) < 3600:
        logger.info(f"URL sudah diproses baru-baru ini (< 1 jam): {url}. Mengabaikan.")
        return
        
    # Catat waktu pemrosesan URL ini
    PROCESSED_URLS[url] = current_time
    
    # Bersihkan cache URL yang sudah lewat dari 1 jam agar memori tidak bengkak
    keys_to_delete = [k for k, v in PROCESSED_URLS.items() if (current_time - v) >= 3600]
    for k in keys_to_delete:
        del PROCESSED_URLS[k]

    record_url_found()
    logger.info(f"URL Disnakerja ditemukan: {url}")

    try:
        logger.info("Memulai pipeline: scrape → AI rewrite → upload...")
        result: JobData = process_job_url(url)

        logger.info("Menyimpan hasil ke MongoDB Atlas...")
        success: bool = save_to_mongodb(result)

        if success:
            record_success(url, result.get("company", "—"))
            logger.info(f"SUKSES! Loker dari {url} berhasil diproses dan disimpan.")
        else:
            record_error()
            logger.error(f"GAGAL menyimpan loker dari {url} ke MongoDB.")

    except Exception as e:
        record_error()
        logger.error(f"Error saat memproses {url}: {e}", exc_info=True)


# ─── Channel Resolver ────────────────────────────────────────────────────────

def _normalize_channel(raw: str) -> str:
    """Normalisasi input channel ke format yang bisa di-resolve Telethon."""
    channel = raw.strip()
    if channel.startswith("https://t.me/"):
        channel = channel.split("/")[-1]
    if not channel.startswith("@") and not channel.replace("-", "").isdigit():
        channel = f"@{channel}"
    return channel


# ─── Session Auto-Save ───────────────────────────────────────────────────────

def _save_session_to_env(session_string: str) -> None:
    """Simpan StringSession baru ke file .env."""
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

        found: bool = False
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith("TELEGRAM_STRING_SESSION="):
                    f.write(f"TELEGRAM_STRING_SESSION={session_string}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f"\nTELEGRAM_STRING_SESSION={session_string}\n")

        logger.info("String Session baru berhasil disimpan ke .env.")
    except Exception as e:
        logger.error(f"Gagal menyimpan session ke .env: {e}", exc_info=True)


# ─── Web Server ──────────────────────────────────────────────────────────────

async def _start_status_server() -> None:
    """Jalankan HTTP server dengan halaman status untuk Render.com."""
    app = web.Application()

    async def handle_status(request: web.Request) -> web.Response:
        html: str = build_status_html()
        return web.Response(text=html, content_type="text/html")

    async def handle_ping(request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/", handle_status)
    app.router.add_get("/ping", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    port: int = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Status server berjalan di port {port}.")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    """Entry point utama: connect → resolve channel → listen."""
    mark_started()
    await client.start()  # type: ignore[arg-type]
    logger.info("Berhasil terhubung ke Telegram.")

    # Auto-save session jika baru pertama kali login
    if not TELEGRAM_STRING_SESSION:
        new_session: str = client.session.save()  # type: ignore[union-attr]
        logger.info("Session baru terdeteksi! Menyimpan otomatis...")
        _save_session_to_env(new_session)

    # Jalankan status server
    await _start_status_server()

    # Resolve channel target
    channel_input: str = _normalize_channel(TELEGRAM_CHANNEL)
    try:
        logger.info(f"Mencari channel target: {channel_input}...")
        target_entity = await client.get_entity(channel_input)
        set_channel_name(target_entity.title)  # type: ignore[union-attr]
        logger.info(f"Channel ditemukan: {target_entity.title}")  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"GAGAL menemukan channel {channel_input}: {e}")
        logger.error("Pastikan akun Telegram Anda sudah JOIN channel tersebut!")
        return

    # Register event handler
    client.add_event_handler(on_new_message, events.NewMessage(chats=target_entity))
    client.add_event_handler(on_new_message, events.MessageEdited(chats=target_entity))

    logger.info(f"Menjalankan listener untuk: {target_entity.title} ({channel_input})")  # type: ignore[union-attr]
    logger.info("Tekan Ctrl+C untuk berhenti.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(main())  # type: ignore[union-attr]
