"""
scrape.py — Pipeline utama untuk scraping dan processing loker Disnakerja.

Alur:
1. Fetch HTML dari Disnakerja
2. Parse konten dengan MyHTMLParser
3. Bersihkan teks dengan clean_and_structure_content
4. Rewrite dengan AI (Gemini)
5. Ekstrak link pendaftaran (via /download/ -> JS Bypass) + email
6. Return data terstruktur (simpan ke JSON)

Usage:
    python scrape.py                              # Default: PT Surya Pertiwi (TOTO)
    python scrape.py https://www.disnakerja.com/xxx/    # URL spesifik
"""

from __future__ import annotations

import json
import sys
from urllib.parse import urljoin

from ai_rewriter import rewrite_with_ai
from logger import get_logger
from parsers import (
    DownloadPageParser,
    MyHTMLParser,
    clean_and_structure_content,
    extract_emails,
    extract_js_redirect_url,
    fetch_html,
)
from storage import save_to_mongodb, upload_image_to_r2
from models import AIResult, ApplyLink, JobData

logger = get_logger(__name__)


def process_job_url(target_url: str) -> JobData:
    """Pipeline lengkap: scrape → clean → AI rewrite → extract links.
    
    Args:
        target_url: URL halaman lowongan di Disnakerja.
        
    Returns:
        JobData berisi data lowongan terstruktur siap disave.
    """
    logger.info(f"{'='*60}")
    logger.info(f"MEMULAI PROSES: {target_url}")
    logger.info(f"{'='*60}")

    # 1. Fetch & Parse HTML
    logger.info("[1/5] Fetching dan parsing HTML...")
    html = fetch_html(target_url)
    parser = MyHTMLParser()
    parser.feed(html)
    parser.finalize()
    logger.info(f"Judul ditemukan: '{parser.title}'")
    logger.info(f"Konten mentah: {len(parser.content)} baris")

    # 2. Bersihkan konten
    logger.info("[2/5] Membersihkan konten dari sampah...")
    desc: list[str] = clean_and_structure_content(parser.content)
    title_clean: str = parser.title.replace("– DISNAKERJA.COM", "").replace("- DISNAKERJA.COM", "").strip()

    # 3. AI Rewriting
    logger.info("[3/5] Mengirim ke AI untuk rewriting...")
    original_desc_text: str = "\n".join(desc)
    ai_result: AIResult = rewrite_with_ai(original_desc_text, title_clean)

    # 4. Upload gambar ke R2
    slug: str = ai_result.get("slug", title_clean.lower().replace(" ", "-").replace(".", ""))
    image_url: str = ""
    if parser.og_image:
        logger.info(f"[4/6] Mengupload gambar: {parser.og_image}")
        r2_url = upload_image_to_r2(parser.og_image, slug)
        if r2_url:
            image_url = r2_url
    else:
        logger.info("[4/6] Tidak ada gambar OG ditemukan. Dilewati.")

    # 5. Susun data JSON
    logger.info("[5/6] Menyusun data akhir...")
    empty_section = {"header": "", "paragraphs": []}

    result: JobData = {
        "original_url": target_url,
        "company": title_clean,
        "slug": slug,
        "image_url": image_url,
        "location": ai_result.get("location", ""),
        "job_type": ai_result.get("job_type", ""),
        "education": ai_result.get("education", ""),
        "seo": {
            "meta_title": ai_result.get("meta_title", ""),
            "meta_description": ai_result.get("meta_description", ""),
            "tags": ai_result.get("tags", []),
        },
        "category": ai_result.get("category", "Lainnya"),
        "section_1": ai_result.get("section_1", empty_section),
        "section_2": ai_result.get("section_2", empty_section),
        "salaries": ai_result.get("salaries", []),
        "section_3": ai_result.get("section_3", empty_section),
        "section_4": ai_result.get("section_4", empty_section),
        "jobs": ai_result.get("jobs", []),
        "section_5": ai_result.get("section_5", empty_section),
        "apply_links": [],
    }

    # 6. Ekstrak link pendaftaran
    logger.info("[6/6] Mengekstrak link pendaftaran (termasuk bypass JS)...")
    apply_links: list[ApplyLink] = []

    # Jika ada halaman /download/
    if parser.apply_page_url:
        try:
            download_url = urljoin(target_url, parser.apply_page_url)
            logger.info(f"Fetching halaman download: {download_url}")
            dl_html = fetch_html(download_url)
            dl_parser = DownloadPageParser()
            dl_parser.feed(dl_html)
            
            # Loop setiap link download (?link=x)
            for link_data in dl_parser.apply_links:
                redirect_page_url = urljoin(download_url, link_data["url"])
                logger.info(f"Membuka halaman redirect (5 detik): {redirect_page_url}")
                redirect_html = fetch_html(redirect_page_url)
                
                # Ekstrak JS var url = "..."
                final_url = extract_js_redirect_url(redirect_html)
                if final_url:
                    logger.info(f"  -> Bypass berhasil! URL Asli: {final_url}")
                    apply_links.append(ApplyLink(url=final_url, method=link_data["method"]))
                else:
                    logger.warning(f"  -> Gagal menemukan URL di halaman redirect: {redirect_page_url}")

        except Exception as e:
            logger.warning(f"Gagal fetch halaman download: {e}")
            result["apply_error"] = str(e)
    else:
        logger.info("Tidak ada halaman /download/ ditemukan.")

    # Ekstrak email dari konten
    emails: list[str] = extract_emails(parser.content)
    for email in emails:
        apply_links.append(ApplyLink(url=f"mailto:{email}", method="Apply via Email"))

    result["apply_links"] = apply_links

    logger.info(f"PROSES SELESAI: {title_clean}")
    logger.info(f"  Posisi: {len(result.get('jobs', []))} | Apply links: {len(result['apply_links'])}")
    logger.info(f"{'='*60}")
    return result


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_url: str = sys.argv[1] if len(sys.argv) > 1 else "https://www.disnakerja.com/?p=36864"
    logger.info(f"CLI Mode: Scraping {test_url}")

    result_data: JobData = process_job_url(test_url)

    output_file: str = "result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=4, ensure_ascii=False)

    # Save ke MongoDB
    save_to_mongodb(result_data)

    logger.info(f"Hasil disimpan ke: {output_file} dan MongoDB")
    print(f"\n✅ Berhasil! Data tersimpan di {output_file} dan MongoDB")
