# 🤖 NyariKerja Bot

Bot otomatis untuk scraping, AI rewriting, dan penyimpanan data lowongan kerja dari channel Telegram ke MongoDB Atlas. Bot ini menjadi "backend" yang mengisi konten untuk [NyariKerja.online](https://nyarikerja.online).

---

## ✨ Fitur Utama

| Fitur                     | Deskripsi                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------- |
| **Telegram Listener**     | Mendengarkan pesan baru & edit di channel Telegram secara real-time                               |
| **Auto Scraper**          | Mengekstrak data lowongan dari BukaJobs (judul, konten, gambar, link apply, email)                |
| **AI Rewriting (Gemini)** | Menulis ulang deskripsi agar unik dan SEO-optimized menggunakan Gemini API (multi-model fallback) |
| **Image Upload (R2)**     | Mengunduh dan mengunggah gambar lowongan ke Cloudflare R2 CDN                                     |
| **MongoDB Upsert**        | Menyimpan data terstruktur ke MongoDB Atlas tanpa duplikasi                                       |
| **Status Dashboard**      | Halaman web monitoring real-time (uptime, success rate, statistik)                                |
| **Duplicate Guard**       | Cache URL in-memory untuk mencegah pemrosesan ulang dalam 1 jam                                   |
| **Type-Safe**             | Seluruh kode menggunakan TypedDict — tanpa `dict[str, Any]`                                       |

---

## 🛠️ Tech Stack

| Layer              | Teknologi                                                                          |
| ------------------ | ---------------------------------------------------------------------------------- |
| **Bahasa**         | Python 3.10+                                                                       |
| **Telegram**       | [Telethon](https://docs.telethon.dev/) (MTProto, StringSession)                    |
| **AI**             | [Google Gemini API](https://ai.google.dev/) (REST, multi-model fallback)           |
| **Object Storage** | [Cloudflare R2](https://developers.cloudflare.com/r2/) via `boto3` (S3-compatible) |
| **Database**       | [MongoDB Atlas](https://www.mongodb.com/atlas) via `pymongo`                       |
| **Web Server**     | `aiohttp` (status page + health check)                                             |
| **Hosting**        | [Render](https://render.com/) (Free Tier)                                          |

---

## 📁 Struktur Proyek

```
bot/
├── telegram_listener.py   # Entry point — Telegram listener + web server
├── scrape.py              # Pipeline utama (fetch → parse → AI → upload → save)
├── parsers.py             # HTML parser (MyHTMLParser, ApplyPageParser) + content cleaner
├── ai_rewriter.py         # Gemini API integration + prompt template
├── storage.py             # Upload gambar ke R2 + upsert data ke MongoDB
├── models.py              # TypedDict definitions (8 tipe data ketat)
├── config.py              # Load .env, validasi, export config bertipe
├── logger.py              # Console-only logging (stdout untuk Render)
├── stats.py               # In-memory stats tracker (uptime, counters)
├── status_page.py         # HTML status page builder (glassmorphism UI)
├── requirements.txt       # Dependencies
└── .env                   # Environment variables (JANGAN commit!)
```

---

## 🔄 Alur Kerja Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  Channel Telegram (pesan baru / edit)                       │
│                   ↓                                         │
│  telegram_listener.py                                       │
│  • Deteksi URL BukaJobs via regex                           │
│  • Cek duplikasi (cache 1 jam)                              │
│                   ↓                                         │
│  scrape.py — Pipeline 6 Langkah                             │
│                                                             │
│  [1/6] Fetch HTML (urllib) + Parse (MyHTMLParser)           │
│         → judul, konten, og:image, published_time           │
│                   ↓                                         │
│  [2/6] Clean content (parsers.py)                           │
│         → Buang iklan, social links, disclaimer             │
│                   ↓                                         │
│  [3/6] AI Rewriting (Gemini API)                            │
│         → 5 section, gaji, posisi, SEO metadata             │
│         → Fallback otomatis jika semua model gagal          │
│                   ↓                                         │
│  [4/6] Upload gambar ke Cloudflare R2                       │
│         → Slug-based filename, public URL                   │
│                   ↓                                         │
│  [5/6] Ekstrak link pendaftaran                             │
│         → Parse halaman /apply/ + email dari konten         │
│                   ↓                                         │
│  [6/6] Simpan ke MongoDB Atlas (upsert by original_url)     │
│         → created_at / updated_at otomatis                  │
│                                                             │
│  ✅ Data siap tampil di frontend NyariKerja.online          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧩 Modul Detail

### `telegram_listener.py` — Entry Point

- Telethon client dengan `StringSession` (persistent login)
- Event handler: `NewMessage` + `MessageEdited`
- URL duplicate cache (in-memory, TTL 1 jam)
- Auto-save session baru ke `.env`
- HTTP status server via `aiohttp` (port dari env `PORT`)
- Channel normalizer (support `@channel`, `https://t.me/channel`, nama langsung)

### `parsers.py` — HTML Parsing

- `MyHTMLParser`: Parsing halaman detail BukaJobs
  - Ekstrak: `<h1 class="entry-title">`, `<div class="entry-content">`, meta tags (og:image, published_time)
  - Tracking div depth untuk menangani nested elements
- `ApplyPageParser`: Parsing halaman `/apply/` untuk link pendaftaran (`<ul class="pjs-download-list">`)
- `clean_and_structure_content()`: Pembersihan konten
  - Stop keywords: "post views:", "posting terkait:", "baca juga:"
  - Junk removal: 20+ pattern (iklan, social, disclaimer, dll.)
- `extract_emails()`: Regex extraction email dari konten

### `ai_rewriter.py` — Gemini AI

- Prompt template yang sangat detail (13 aturan)
  - 5 section artikel naratif (bukan list/bullet)
  - Ekstraksi: lokasi, job_type, education, salaries, positions + requirements
  - SEO: slug, meta_title (maks 60 char), meta_description (maks 150 char), 10-15 tags
  - Category classification (Manufaktur, F&B, IT, Logistik, Retail, dll.)
- Multi-model fallback chain:
  1. `gemini-3.5-flash`
  2. `gemini-3-flash`
  3. `gemini-2.5-flash`
  4. `gemini-3.1-flash-lite`
  5. `gemini-2.5-flash-lite`
- Fallback data mentah jika semua model gagal
- Response format: `application/json` (structured output)

### `storage.py` — Penyimpanan

- **R2 Upload**: Download gambar → detect content-type → upload dengan slug-based filename
- **MongoDB Upsert**: `update_one` dengan filter `original_url` + `upsert=True`
  - Auto-set `created_at` (pertama kali) dan `updated_at` (setiap update)
  - Connection: `ServerApi("1")` dengan TLS

### `models.py` — Type Definitions

8 TypedDict yang ketat:

- `SectionData` — section artikel (header + paragraphs)
- `SalaryData` — data gaji per posisi
- `JobPosition` — posisi + requirements
- `ApplyLink` — link pendaftaran (url + method)
- `SeoData` — meta_title, meta_description, tags
- `AIResult` — output dari AI (total=False untuk field opsional)
- `JobData` — dokumen MongoDB lengkap
- `BotStats` — statistik bot

---

## 🔧 Konfigurasi

Buat file `.env` di dalam folder `bot/`:

```env
# Telegram (wajib)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_CHANNEL=bukajobs
TELEGRAM_STRING_SESSION=

# Gemini AI (wajib)
GEMINI_API_KEY=your_gemini_api_key

# Cloudflare R2 (opsional — gambar dilewati jika tidak diset)
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=your_bucket
R2_PUBLIC_DOMAIN=https://your-domain.r2.dev

# MongoDB Atlas (wajib)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DB_NAME=nyarikerja_db
MONGODB_COLLECTION_NAME=jobs
```

### Cara Mendapatkan Credentials

| Credential                              | Sumber                                                   |
| --------------------------------------- | -------------------------------------------------------- |
| `TELEGRAM_API_ID` & `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org)               |
| `TELEGRAM_STRING_SESSION`               | Auto-generate saat pertama kali login                    |
| `GEMINI_API_KEY`                        | [Google AI Studio](https://aistudio.google.com/apikey)   |
| `R2_*`                                  | [Cloudflare Dashboard → R2](https://dash.cloudflare.com) |
| `MONGODB_URI`                           | [MongoDB Atlas](https://cloud.mongodb.com)               |

---

## 🚀 Menjalankan Lokal

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Siapkan .env (salin template di atas, isi nilainya)

# 3. Jalankan Telegram listener (pertama kali akan meminta login)
python telegram_listener.py

# 4. Atau jalankan scraper manual (tanpa Telegram)
python scrape.py https://bukajobs.com/contoh-perusahaan/
```

> **Catatan:** Saat pertama kali menjalankan `telegram_listener.py`, Telethon akan meminta nomor HP dan OTP untuk login. Session akan otomatis disimpan ke `.env` sebagai `TELEGRAM_STRING_SESSION`.

---

## 🌐 Deploy ke Render

### Pengaturan Render Web Service

| Setting           | Value                             |
| ----------------- | --------------------------------- |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python telegram_listener.py`     |
| **Environment**   | Python 3                          |
| **Plan**          | Free                              |

### Environment Variables

Tambahkan semua variabel dari `.env` ke **Render Dashboard → Environment**.

> ⚠️ **Penting:** `TELEGRAM_STRING_SESSION` harus diisi. Jalankan bot di lokal sekali untuk generate session, lalu salin nilainya ke Render.

### Health Check Endpoints

| Endpoint    | Response          | Fungsi                    |
| ----------- | ----------------- | ------------------------- |
| `GET /`     | HTML status page  | Dashboard monitoring      |
| `GET /ping` | `ok` (plain text) | Health check untuk Render |

---

## 📊 Status Dashboard

Saat bot berjalan, buka URL Render di browser untuk melihat dashboard:

- 🟢/🔴 Status bot (hidup/mati)
- ⏱️ Uptime
- 📈 Total berhasil / gagal / URL ditemukan
- 📊 Success rate (persentase)
- 📡 Channel yang didengarkan
- 🏢 Perusahaan terakhir diproses + waktu

> Dashboard ini **tidak menampilkan data sensitif** (API key, URI database, session).

---

## 🛡️ Keamanan

- `.env` masuk `.gitignore` — tidak pernah ter-commit
- Status page tidak menampilkan credential apapun
- `TELEGRAM_STRING_SESSION` bersifat rahasia — jangan bagikan
- MongoDB menggunakan `mongodb+srv://` dengan TLS
- Bot load `.env` manual (tanpa `python-dotenv`) — zero extra dependency

---

## 📝 Lisensi

© 2026 NyariKerja.online — All rights reserved.
