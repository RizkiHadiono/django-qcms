"""Ambil screenshot halaman QCMS untuk dokumentasi portofolio.

Jalankan setelah aplikasi hidup di http://127.0.0.1:8080:
    pip install -r requirements-dev.txt
    python -m playwright install chromium
    python scripts/screenshots.py

Hasil berupa .webp di docs/screenshots/ (ukuran jauh lebih kecil dari PNG).
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"

# Rentang 30 hari terakhir agar grafik terlihat penuh pada screenshot.
HARI_INI = date.today()
DARI = (HARI_INI - timedelta(days=29)).isoformat()
RENTANG = f"?dari={DARI}&sampai={HARI_INI.isoformat()}"

# (nama file, path, tunggu chart)
PAGES = [
    ("01-login", "/login/", False),
    ("02-dashboard", "/dashboard/" + RENTANG, True),
    ("03-analisis", "/analisis/" + RENTANG, True),
    ("04-laporan", "/laporan/" + RENTANG, False),
    ("05-pemeriksaan", "/pemeriksaan/", False),
    ("06-pemeriksaan-form", "/pemeriksaan/baru/", False),
    ("07-pemeriksaan-detail", "/pemeriksaan/{detail_id}/", False),
    ("08-riwayat", "/pemeriksaan/riwayat/", False),
    ("09-produksi", "/produksi/", False),
    ("10-master-produk", "/master/produk/", False),
]


def simpan(page, name, tmpdir):
    """Screenshot ke PNG sementara, lalu konversi ke WebP."""
    png = Path(tmpdir) / f"{name}.png"
    page.screenshot(path=png)
    with Image.open(png) as img:
        img.save(OUT / f"{name}.webp", "WEBP", quality=88, method=6)
    png.unlink(missing_ok=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            locale="id-ID",
            timezone_id="Asia/Jakarta",
        )
        page = context.new_page()

        page.goto(f"{BASE}/login/", wait_until="networkidle")
        simpan(page, "01-login", tmpdir)
        print("ok 01-login")

        page.fill("#id_username", "supervisor")
        page.fill("#id_password", "supervisor123")
        page.click("button[type=submit]")
        page.wait_for_url(f"{BASE}/dashboard/", timeout=20000)
        page.wait_for_load_state("networkidle")

        # Ambil id sesi pertama dari halaman riwayat untuk screenshot detail.
        page.goto(f"{BASE}/pemeriksaan/riwayat/", wait_until="networkidle")
        detail_id = page.evaluate(
            """() => {
                const a = [...document.querySelectorAll('a[href*="/pemeriksaan/"]')]
                    .find(el => /pemeriksaan\\/\\d+\\//.test(el.getAttribute('href')));
                return a ? a.getAttribute('href').match(/pemeriksaan\\/(\\d+)\\//)[1] : null;
            }"""
        )
        print("detail_id:", detail_id)

        for name, path, wait_chart in PAGES[1:]:
            page.goto(
                BASE + path.format(detail_id=detail_id or 1), wait_until="networkidle"
            )
            if wait_chart:
                page.wait_for_timeout(1800)  # beri waktu Chart.js menggambar
            simpan(page, name, tmpdir)
            print("ok", name)

        browser.close()

    files = sorted(OUT.glob("*.webp"))
    total = sum(f.stat().st_size for f in files)
    print(f"\n{len(files)} gambar, total {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
