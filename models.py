"""
types.py — Type definitions untuk seluruh bot.

Menggantikan semua `dict[str, Any]` dengan TypedDict yang ketat.
Sama seperti interface di TypeScript — setiap field punya tipe yang jelas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from typing_extensions import TypedDict


class SectionData(TypedDict):
    """Satu section artikel (header + paragraf)."""
    header: str
    paragraphs: list[str]


class SalaryData(TypedDict):
    """Satu baris data gaji."""
    position: str
    salary: str


class JobPosition(TypedDict):
    """Satu posisi lowongan + kualifikasinya."""
    position: str
    requirements: list[str]


class ApplyLink(TypedDict):
    """Satu link pendaftaran."""
    url: str
    method: str


class SeoData(TypedDict):
    """Metadata SEO."""
    meta_title: str
    meta_description: str
    tags: list[str]


class AIResult(TypedDict, total=False):
    """Hasil dari AI rewriting. `total=False` karena beberapa field bisa kosong."""
    slug: str
    category: str
    location: str
    job_type: str
    education: str
    meta_title: str
    meta_description: str
    tags: list[str]
    section_1: SectionData
    section_2: SectionData
    salaries: list[SalaryData]
    section_3: SectionData
    section_4: SectionData
    jobs: list[JobPosition]
    section_5: SectionData


class JobData(TypedDict, total=False):
    """Dokumen lowongan kerja lengkap untuk MongoDB."""
    original_url: str
    company: str
    slug: str
    image_url: str
    location: str
    job_type: str
    education: str
    seo: SeoData
    category: str
    section_1: SectionData
    section_2: SectionData
    salaries: list[SalaryData]
    section_3: SectionData
    section_4: SectionData
    jobs: list[JobPosition]
    section_5: SectionData
    apply_links: list[ApplyLink]
    apply_error: str
    created_at: str
    updated_at: str


class BotStats(TypedDict):
    """Statistik bot yang ditampilkan di status page."""
    started_at: Optional[datetime]
    channel_name: str
    total_messages: int
    total_urls_found: int
    total_success: int
    total_errors: int
    last_processed_url: str
    last_processed_at: str
    last_company: str
