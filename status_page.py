"""
status_page.py — HTML status page builder.

Satu modul, satu tanggung jawab: generate HTML halaman status.
Tidak ada logika bisnis, hanya presentasi.
"""

from __future__ import annotations

from stats import get_stats, get_success_rate, get_uptime


def build_status_html() -> str:
    """Generate HTML status page — tanpa data sensitif apapun."""
    stats = get_stats()
    uptime = get_uptime()
    success_rate = get_success_rate()
    status_emoji = "🟢" if stats["started_at"] else "🔴"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Disnakerja Bot Status</title>
        <style>
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f3f4f6;
                color: #1f2937;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 40px 20px;
                margin: 0;
            }}
            .card {{
                background-color: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                padding: 30px;
                width: 100%;
                max-width: 600px;
            }}
            .header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid #e5e7eb;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            .title {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
                color: #111827;
            }}
            .status-badge {{
                background-color: #10b981;
                color: white;
                padding: 6px 12px;
                border-radius: 9999px;
                font-size: 14px;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .status-dot {{
                width: 8px;
                height: 8px;
                background-color: white;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
                100% {{ opacity: 1; }}
            }}
            .stat-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }}
            .stat-box {{
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 32px;
                font-weight: 700;
                margin: 0;
                line-height: 1;
            }}
            .stat-label {{
                font-size: 14px;
                color: #6b7280;
                margin-top: 8px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .val-success {{ color: #10b981; }}
            .val-error {{ color: #ef4444; }}
            
            .info-section {{
                background-color: #f8fafc;
                border-left: 4px solid #3b82f6;
                padding: 16px;
                border-radius: 4px;
                margin-bottom: 20px;
            }}
            .info-row {{
                display: flex;
                margin-bottom: 8px;
                font-size: 14px;
            }}
            .info-row:last-child {{ margin-bottom: 0; }}
            .info-key {{
                font-weight: 600;
                width: 140px;
                color: #475569;
            }}
            .info-val {{ color: #1e293b; }}
            
            .footer {{
                margin-top: 40px;
                text-align: center;
                color: #9ca3af;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1 class="title">Disnakerja Bot Dashboard</h1>
                <div class="status-badge">
                    <div class="status-dot"></div>
                    Online
                </div>
            </div>
            
            <div class="stat-grid">
                <div class="stat-box">
                    <p class="stat-value val-success">{stats['total_success']}</p>
                    <p class="stat-label">Berhasil</p>
                </div>
                <div class="stat-box">
                    <p class="stat-value val-error">{stats['total_errors']}</p>
                    <p class="stat-label">Gagal</p>
                </div>
                <div class="stat-box">
                    <p class="stat-value val-msg">{stats['total_messages']}</p>
                    <p class="stat-label">Pesan Masuk</p>
                </div>
                <div class="stat-box">
                    <p class="stat-value val-url">{success_rate}</p>
                    <p class="stat-label">Success Rate</p>
                </div>
            </div>
            
            <div class="info-section">
                <div class="info-row">
                    <div class="info-key">Uptime</div>
                    <div class="info-val">{uptime}</div>
                </div>
                <div class="info-row">
                    <div class="info-key">Channel</div>
                    <div class="info-val">{stats['channel_name']}</div>
                </div>
                <div class="info-row">
                    <div class="info-key">Terakhir Update</div>
                    <div class="info-val">{stats['last_processed_at']}</div>
                </div>
                <div class="info-row">
                    <div class="info-key">Perusahaan Terakhir</div>
                    <div class="info-val">{stats['last_company']}</div>
                </div>
            </div>
            
            <div class="footer">
                &copy; 2026 NyariKerja.online
            </div>
        </div>
    </body>
    </html>
    """
    return html
