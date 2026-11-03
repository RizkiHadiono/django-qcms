from django.conf import settings
from django.urls import NoReverseMatch, reverse


def _decorate(items, current_path):
    for item in items:
        try:
            item["url"] = reverse(item["url_name"])
        except NoReverseMatch:  # pragma: no cover
            item["url"] = "#"
        url = item["url"]
        item["active"] = current_path == url or (
            url != "/" and current_path.startswith(url)
        )
    return items


def app_identity(request):
    """Nama & deskripsi aplikasi, tersedia di seluruh template."""
    return {
        "app_name": settings.APP_NAME,
        "app_description": settings.APP_DESCRIPTION,
        "app_company": settings.APP_COMPANY,
        "demo_mode": settings.DEMO_MODE,
    }


def navigation(request):
    """Menu sidebar yang menyesuaikan role pengguna."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"nav_sections": []}

    is_admin = user.is_superuser or user.role == "admin"
    is_supervisor = is_admin or user.role == "supervisor"

    sections = [
        {
            "title": "Operasional",
            "items": [
                {
                    "label": "Pemeriksaan QC",
                    "url_name": "inspection_list",
                    "icon": "clipboard",
                },
                {"label": "Data Produksi", "url_name": "batch_list", "icon": "box"},
                {
                    "label": "Riwayat QC",
                    "url_name": "inspection_history",
                    "icon": "clock",
                },
            ],
        }
    ]

    if is_supervisor:
        sections.insert(
            0,
            {
                "title": "Ringkasan",
                "items": [
                    {"label": "Dashboard", "url_name": "dashboard", "icon": "grid"},
                    {
                        "label": "Analisis Kualitas",
                        "url_name": "analysis",
                        "icon": "chart",
                    },
                    {"label": "Laporan", "url_name": "reports", "icon": "file"},
                ],
            },
        )

    master_items = [
        {"label": "Data Produk", "url_name": "product_list", "icon": "tag"},
        {"label": "Data Kecacatan", "url_name": "defect_list", "icon": "alert"},
    ]
    if is_admin:
        master_items += [
            {"label": "Lini Produksi", "url_name": "line_list", "icon": "route"},
            {"label": "Shift Kerja", "url_name": "shift_list", "icon": "sun"},
        ]

    sections.append({"title": "Master Data", "items": master_items})

    if is_admin:
        sections.append(
            {
                "title": "Administrasi",
                "items": [
                    {
                        "label": "Manajemen Pengguna",
                        "url_name": "user_list",
                        "icon": "users",
                    },
                ],
            }
        )

    for section in sections:
        _decorate(section["items"], request.path)

    return {
        "nav_sections": sections,
        "current_path": request.path,
        "defect_threshold": settings.QC_DEFECT_RATE_THRESHOLD,
    }
