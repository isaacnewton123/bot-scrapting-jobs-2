"""
ai_rewriter.py — AI rewriting menggunakan Gemini API.

Berisi:
- AI_PROMPT_TEMPLATE  : Template prompt yang mudah diedit
- rewrite_with_ai()   : Kirim teks ke Gemini, terima JSON terstruktur
"""

from __future__ import annotations

import json
import urllib.request

from config import GEMINI_API_KEY, GEMINI_MODELS
from logger import get_logger
from models import AIResult

logger = get_logger(__name__)

# ─── Prompt Template ─────────────────────────────────────────────────────────

AI_PROMPT_TEMPLATE: str = (
    "Tulis ulang deskripsi lowongan pekerjaan ini agar unik, tidak terlihat duplikat, dan SANGAT OPTIMAL UNTUK SEO. "
    "Gunakan bahasa Indonesia yang profesional dan informatif.\n\n"
    "ATURAN PENTING:\n"
    "1. Sisipkan kata kunci (keyword) berikut secara natural: 'Lowongan kerja', 'Loker', 'Karir', '{company}'.\n"
    "2. FORMAT RESPONSE: Respon keseluruhan HARUS berupa JSON murni yang valid. SANGAT PENTING: Jangan bungkus dengan markdown code block (```json). Jika membuat baris baru (newline) di dalam string untuk Markdown list, pastikan men-escape dengan benar (gunakan `\\n`) agar format JSON tidak rusak!\n"
    "3. GAYA PENULISAN (MARKDOWN): Anda SANGAT DISARANKAN menggunakan format Markdown (seperti **bold** atau list poin-poin) DI DALAM string paragraf. JANGAN membuat tabel dan DILARANG KERAS MENGGUNAKAN EMOJI agar bahasa tetap profesional dan relevan. Karena `paragraphs` adalah array, Anda juga bisa memisahkan paragraf/list baru sebagai elemen string terpisah di dalam array tersebut.\n"
    "4. STRUKTUR: Tulis teks secara ringkas, padat, dan tidak bertele-tele. Pastikan tetap kaya akan kata kunci (keyword) SEO LSI.\n"
    "5. Section 1 dan 2 ditempatkan SEBELUM tabel Gaji. Pastikan akhir paragraf Section 2 mengarahkan pembaca untuk melihat tabel gaji. Section 3 dan 4 ditempatkan SETELAH tabel Gaji dan SEBELUM daftar Posisi & Kualifikasi. Pastikan akhir paragraf Section 4 mengarahkan pembaca untuk melihat posisi pekerjaan dan kualifikasi yang ada di bawahnya.\n"
    "6. Section 5 adalah penutup dan ajakan (Call to Action) sebelum link pendaftaran.\n"
    "7. Ekstrak informasi gaji dari teks asli ke dalam array 'salaries'. Jika tidak ada info gaji, biarkan array kosong [].\n"
    "8. EKSTRAK SEMUA POSISI LOWONGAN KERJA beserta kualifikasi/persyaratannya ke dalam array 'jobs'. Bentuknya [{{ 'position': 'Nama Jabatan', 'requirements': ['Syarat 1', 'Syarat 2'] }}]. AI harus cukup pintar membedakan mana teks deskripsi dan mana daftar kualifikasi posisi. JIKA ADA BANYAK POSISI namun kualifikasinya ditulis menjadi satu di bagian bawah, pasangkan kualifikasi tersebut ke semua posisi yang relevan!\n"
    "9. EKSTRAK METADATA LOKASI, TIPE PEKERJAAN, DAN PENDIDIKAN TERAKHIR (location, job_type, education). Jika tidak ada di teks, biarkan string kosong \"\".\n"
    '10. Buatkan \'slug\' URL super SEO-friendly, \'meta_title\' memancing klik (maks 60 karakter), dan \'meta_description\' (maks 150 karakter). Untuk array \'tags\', BERIKAN MINIMAL 10-15 TAGS populer dan sangat relevan (termasuk sinonim jabatan, nama daerah, jenis industri, tipe pekerjaan, misal: \'Loker Cikarang\', \'Pabrik\', \'SMA/SMK\', dll) untuk menyapu bersih semua trafik pencarian.\n'
    "11. Tentukan SATU 'category' utama untuk perusahaan/pekerjaan ini (misalnya: 'Manufaktur & Pabrik', 'F&B dan Restoran', 'IT & Teknologi', 'Logistik & Gudang', 'Retail', 'Kesehatan', 'Administrasi', atau buat sendiri yang relevan).\n"
    "12. Anda HARUS merespon dengan format JSON murni seperti ini:\n"
    "{{\n"
    '  "slug": "lowongan-kerja-pt-oneject-indonesia-jawa-barat",\n'
    '  "category": "Manufaktur & Pabrik",\n'
    '  "location": "Jawa Barat",\n'
    '  "job_type": "Full-Time",\n'
    '  "education": "SMK/SMA/S1",\n'
    '  "meta_title": "Lowongan Kerja PT Oneject Indonesia Terbaru",\n'
    '  "meta_description": "...",\n'
    '  "tags": ["Manufaktur", "Alat Kesehatan"],\n'
    '  "section_1": {{"header": "Judul 1", "paragraphs": ["Paragraf 1"]}}, \n'
    '  "section_2": {{"header": "Judul 2", "paragraphs": ["Paragraf yg mengarahkan ke tabel gaji"]}}, \n'
    '  "salaries": [{{"position": "nama posisi", "salary": "nominal/rentang gaji"}}],\n'
    '  "section_3": {{"header": "Judul 3", "paragraphs": ["Paragraf lanjutan"]}}, \n'
    '  "section_4": {{"header": "Judul 4", "paragraphs": ["Paragraf lanjutan"]}}, \n'
    '  "jobs": [{{"position": "Staff Produksi", "requirements": ["Syarat 1", "Syarat 2"]}}],\n'
    '  "section_5": {{"header": "Judul 5", "paragraphs": ["Paragraf penutup"]}}\n'
    "}}\n"
    "13. Gunakan teknik LSI (Latent Semantic Indexing) secara natural di seluruh paragraf. Rata kanan SEO-nya! Sikat habis semua keyword pencarian potensial tanpa terlihat seperti spam.\n\n"
    "Deskripsi Asli:\n{text}"
)

# ─── Empty Section ────────────────────────────────────────────────────────────

_EMPTY_SECTION: dict[str, str | list[str]] = {"header": "", "paragraphs": []}


# ─── Fallback Result ─────────────────────────────────────────────────────────

def _build_fallback(text: str, company: str) -> AIResult:
    """Buat struktur data fallback jika semua model AI gagal."""
    return AIResult(
        slug=company.lower().replace(" ", "-").replace(".", ""),
        category="Lainnya",
        location="",
        job_type="",
        education="",
        meta_title=f"Lowongan Kerja {company}",
        meta_description=f"Daftar lowongan kerja terbaru di {company}.",
        tags=["Lowongan Kerja"],
        section_1={"header": "", "paragraphs": [p.strip() for p in text.split("\n") if p.strip()]},
        section_2={"header": "", "paragraphs": []},
        salaries=[],
        jobs=[],
        section_3={"header": "", "paragraphs": []},
        section_4={"header": "", "paragraphs": []},
        section_5={"header": "", "paragraphs": []},
    )


# ─── Main Function ───────────────────────────────────────────────────────────

def rewrite_with_ai(text: str, company: str) -> AIResult:
    """Kirim teks lowongan ke Gemini API dan terima JSON terstruktur.
    
    Mencoba beberapa model secara berurutan. Jika semua gagal, 
    kembalikan fallback data mentah.
    
    Args:
        text: Teks lowongan yang sudah dibersihkan.
        company: Nama perusahaan.
        
    Returns:
        AIResult berisi data lowongan terstruktur.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY tidak tersedia. Menggunakan fallback.")
        return _build_fallback(text, company)

    prompt: str = AI_PROMPT_TEMPLATE.format(company=company, text=text)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    payload: bytes = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }).encode("utf-8")

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            logger.info(f"Mencoba AI model: {model}...")
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                raw_ai: str = result["candidates"][0]["content"]["parts"][0]["text"]
                ai_json: AIResult = json.loads(raw_ai)
                logger.info(f"Berhasil menggunakan model: {model}")
                logger.debug(f"AI response keys: {list(ai_json.keys())}")
                return ai_json
        except Exception as e:
            logger.warning(f"Model {model} gagal: {e}")
            continue

    logger.error("Semua model AI gagal/sibuk. Menggunakan fallback data mentah.")
    return _build_fallback(text, company)
