"""
parsers.py — HTML parsing dan content cleaning untuk Disnakerja.

Berisi:
- fetch_html()           : Download halaman web
- extract_js_redirect_url() : Ekstrak URL asli dari halaman loading 5 detik
- MyHTMLParser           : Ekstrak judul, konten, meta dari halaman loker Disnakerja
- DownloadPageParser     : Ekstrak link pendaftaran dari halaman /download/
- clean_and_structure_content() : Bersihkan teks dari iklan, social links, disclaimer
"""

from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser
from typing import Any

from config import HTTP_HEADERS
from logger import get_logger

logger = get_logger(__name__)


# ─── Fetch HTML & JS Redirect Extractor ──────────────────────────────────────

def fetch_html(target_url: str) -> str:
    """Download dan return HTML mentah dari sebuah URL."""
    logger.info(f"Fetching HTML: {target_url}")
    req = urllib.request.Request(target_url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req) as response:
        html = response.read().decode("utf-8")
        logger.debug(f"HTML diterima: {len(html)} bytes")
        return html


def extract_js_redirect_url(html: str) -> str | None:
    """Mengekstrak var url = "TARGET" dari halaman redirect Disnakerja."""
    # Contoh pola di Disnakerja: var url = "https://docs.google.com/forms/...";
    match = re.search(r'var\s+url\s*=\s*[\'"]([^\'"]+)[\'"]\s*;', html)
    if match:
        return match.group(1)
    return None


# ─── Main HTML Parser ────────────────────────────────────────────────────────

class MyHTMLParser(HTMLParser):
    """Parser untuk halaman detail loker Disnakerja.
    
    Mengekstrak:
    - title           : Judul lowongan (dari <h1 class="entry-title">)
    - content         : List teks konten artikel
    - apply_page_url  : URL halaman /download/ jika ada
    - published_time  : Waktu publikasi dari meta tag
    - og_image        : URL gambar Open Graph
    """

    def __init__(self) -> None:
        super().__init__()
        self.in_title: bool = False
        self.in_content: bool = False
        self.title: str = ""
        self.content: list[str] = []
        self.apply_page_url: str | None = None
        self.current_content: str = ""
        self.div_depth: int = 0
        self.content_div_depth: int = -1
        self.in_a: bool = False
        self.current_href: str = ""
        self.published_time: str = ""
        self.og_image: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict: dict[str, str] = dict(attrs)  # type: ignore[arg-type]

        if tag == "meta":
            if attrs_dict.get("property") == "article:published_time":
                self.published_time = attrs_dict.get("content", "")
            if attrs_dict.get("property") == "og:image":
                self.og_image = attrs_dict.get("content", "")

        if tag == "h1" and "entry-title" in attrs_dict.get("class", ""):
            self.in_title = True

        if tag == "div":
            self.div_depth += 1
            if "entry-content" in attrs_dict.get("class", ""):
                self.in_content = True
                self.content_div_depth = self.div_depth

        if tag == "a":
            self.in_a = True
            self.current_href = attrs_dict.get("href", "")
            # Disnakerja menggunakan /download/ atau /download di area manapun (biasanya sebelum content)
            if "/download" in self.current_href.lower():
                self.apply_page_url = self.current_href

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self.in_title = False
        if tag == "div":
            if self.div_depth == self.content_div_depth:
                self.in_content = False
                self.content_div_depth = -1
            self.div_depth -= 1

        if tag == "a":
            self.in_a = False
            self.current_href = ""

        if tag in ["p", "li", "h2", "h3", "h4", "td"] and self.in_content:
            if self.current_content.strip():
                self.content.append(self.current_content.strip())
            self.current_content = ""

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data.strip()
        if self.in_content:
            self.current_content += data

    def finalize(self) -> None:
        if self.current_content.strip():
            self.content.append(self.current_content.strip())
            self.current_content = ""


# ─── Download Page Parser ────────────────────────────────────────────────────

class DownloadPageParser(HTMLParser):
    """Parser untuk halaman /download/ yang berisi link pendaftaran (?link=x)."""

    def __init__(self) -> None:
        super().__init__()
        self.apply_links: list[dict[str, str]] = []
        self.in_a: bool = False
        self.current_href: str = ""
        self.current_text: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict: dict[str, str] = dict(attrs)  # type: ignore[arg-type]
        if tag == "a":
            self.in_a = True
            self.current_href = attrs_dict.get("href", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.in_a = False
            # Cari yang memiliki parameter ?link=
            if "?link=" in self.current_href:
                self.apply_links.append({
                    "url": self.current_href,
                    "method": self.current_text.strip() if self.current_text.strip() else "Apply Here",
                })
            self.current_href = ""
            self.current_text = ""

    def handle_data(self, data: str) -> None:
        if self.in_a:
            self.current_text += data


# ─── Content Cleaner ─────────────────────────────────────────────────────────

_STOP_KEYWORDS: list[str] = [
    "post views:",
    "posting terkait:",
    "baca juga:",
    "perusahaan lainnya:",
]

_JUNK_KEYWORDS: list[str] = [
    "adsbygoogle", "Post Views:", "Perhatian :", "NOTE :", "Join Whatsapp",
    "Jika link error", "Posting terkait:", "Baca juga", "Lowongan lainnya",
    "Share", "Bagikan", "Follow", "Instagram", "Telegram", "Linkedin",
    "Grup Telegram", "Grup Whatsapp", "Gabung Grup", "DISCLAIMER",
    "Hati-hati penipuan", "Seluruh proses seleksi", "TIDAK dipungut biaya",
    "Tidak memungut biaya", "Pelamar yang lolos", "Kirim Lamaran", "Apply here",
    "INFO LOWONGAN LAINNYA", "DAPAT DITEMUKAN DI", "T.ME/DISNAKERJA", "INFO:",
    "Akses lebih mudah di aplikasi Disnakerja", "Laporkan apabila terdapat kesalahan",
    "Jika link sudah tidak bisa lagi diakses",
]

def clean_and_structure_content(raw_content: list[str]) -> list[str]:
    """Bersihkan konten mentah dari iklan, social links, dan disclaimer."""
    description: list[str] = []
    skip_next: bool = False

    for text in raw_content:
        text = text.strip()
        if not text:
            continue

        if skip_next:
            skip_next = False
            continue

        if text.lower() == "tanggal publikasi:":
            skip_next = True
            continue

        if any(stop in text.lower() for stop in _STOP_KEYWORDS):
            logger.debug(f"Stop keyword ditemukan: '{text[:50]}...' — menghentikan parsing.")
            break

        if any(junk.lower() in text.lower() for junk in _JUNK_KEYWORDS):
            logger.debug(f"Junk dibuang: '{text[:60]}...'")
            continue

        if len(text) < 3 and not any(c.isalpha() for c in text):
            continue

        description.append(text)

    logger.info(f"Content cleaning selesai: {len(raw_content)} baris → {len(description)} baris bersih.")
    return description


def extract_emails(content: list[str]) -> list[str]:
    """Ekstrak semua alamat email unik dari konten."""
    emails: list[str] = []
    for text in content:
        matches = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        emails.extend(matches)
    unique = list(set(emails))
    if unique:
        logger.info(f"Ditemukan {len(unique)} email: {unique}")
    return unique
