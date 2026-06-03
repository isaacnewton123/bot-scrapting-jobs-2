"""
stats.py — In-memory stats tracker untuk bot.

Satu modul, satu tanggung jawab: mencatat statistik aktivitas bot.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from models import BotStats


# ─── State ────────────────────────────────────────────────────────────────────

_stats: BotStats = {
    "started_at": None,
    "channel_name": "—",
    "total_messages": 0,
    "total_urls_found": 0,
    "total_success": 0,
    "total_errors": 0,
    "last_processed_url": "—",
    "last_processed_at": "—",
    "last_company": "—",
}


# ─── Getters ──────────────────────────────────────────────────────────────────

def get_stats() -> BotStats:
    """Return snapshot statistik saat ini."""
    return _stats


def get_uptime() -> str:
    """Hitung uptime dalam format yang mudah dibaca manusia."""
    if not _stats["started_at"]:
        return "—"
    delta = datetime.utcnow() - _stats["started_at"]
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0:
        parts.append(f"{hours} jam")
    parts.append(f"{minutes} menit")
    return " ".join(parts)


def get_success_rate() -> str:
    """Hitung persentase keberhasilan."""
    total = _stats["total_success"] + _stats["total_errors"]
    if total == 0:
        return "—"
    pct = (_stats["total_success"] / total) * 100
    return f"{pct:.0f}%"


# ─── Setters ──────────────────────────────────────────────────────────────────

def mark_started() -> None:
    """Tandai bot sudah mulai berjalan."""
    _stats["started_at"] = datetime.utcnow()


def set_channel_name(name: str) -> None:
    """Set nama channel yang sedang didengarkan."""
    _stats["channel_name"] = name


def record_message() -> None:
    """Catat satu pesan masuk."""
    _stats["total_messages"] += 1


def record_url_found() -> None:
    """Catat satu URL BukaJobs ditemukan."""
    _stats["total_urls_found"] += 1


def record_success(url: str, company: str) -> None:
    """Catat satu loker berhasil diproses."""
    _stats["total_success"] += 1
    _stats["last_processed_url"] = url
    _stats["last_processed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    _stats["last_company"] = company


def record_error() -> None:
    """Catat satu kegagalan."""
    _stats["total_errors"] += 1
