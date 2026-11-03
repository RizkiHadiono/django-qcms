"""Perhitungan agregat untuk dashboard, analisis, dan laporan."""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.inspection.models import InspectionDefect, QcInspection
from apps.masterdata.models import DefectCategory
from apps.production.models import ProductionBatch

GRUP_LABELS = dict(DefectCategory.Grup.choices)


def parse_period(request, default_days=7):
    """Ambil periode dari query string, dengan nilai bawaan yang masuk akal."""
    today = timezone.localdate()
    dari = parse_date(request.GET.get("dari", "") or "")
    sampai = parse_date(request.GET.get("sampai", "") or "")
    if not dari and not sampai:
        dari = today - timedelta(days=default_days - 1)
        sampai = today
    elif not dari:
        dari = sampai - timedelta(days=default_days - 1)
    elif not sampai:
        sampai = today
    if dari > sampai:
        dari, sampai = sampai, dari
    return dari, sampai


def filters_from_request(request):
    return {
        "line": request.GET.get("line", ""),
        "shift": request.GET.get("shift", ""),
        "product": request.GET.get("product", ""),
        "metode": request.GET.get("metode", ""),
    }


def base_queryset(dari, sampai, filters=None):
    """Pemeriksaan final dalam periode (void & draft tidak dihitung)."""
    filters = filters or {}
    qs = QcInspection.objects.filter(
        status=QcInspection.Status.FINAL,
        inspected_at__date__gte=dari,
        inspected_at__date__lte=sampai,
    )
    if filters.get("line"):
        qs = qs.filter(batch__line_id=filters["line"])
    if filters.get("shift"):
        qs = qs.filter(batch__shift_id=filters["shift"])
    if filters.get("product"):
        qs = qs.filter(batch__product_id=filters["product"])
    if filters.get("metode"):
        qs = qs.filter(metode=filters["metode"])
    return qs


def summary(qs):
    agg = qs.aggregate(
        inspected=Sum("qty_inspected"),
        passed=Sum("qty_pass"),
        failed=Sum("qty_fail"),
    )
    inspected = agg["inspected"] or 0
    failed = agg["failed"] or 0
    passed = agg["passed"] or 0

    total_production = (
        ProductionBatch.objects.filter(inspections__in=qs)
        .distinct()
        .aggregate(total=Sum("qty_plan"))["total"]
        or 0
    )
    occurrences = InspectionDefect.objects.filter(unit__inspection__in=qs).count()

    return {
        "total_production": total_production,
        "inspected": inspected,
        "passed": passed,
        "failed": failed,
        "defect_rate": (failed / inspected * 100) if inspected else 0,
        "pass_rate": (passed / inspected * 100) if inspected else 0,
        "coverage": (inspected / total_production * 100) if total_production else 0,
        "occurrences": occurrences,
        "dpu": (occurrences / inspected) if inspected else 0,
        "sessions": qs.count(),
        "batches": qs.values("batch_id").distinct().count(),
    }


def pareto(qs, limit=None):
    rows = list(
        InspectionDefect.objects.filter(unit__inspection__in=qs)
        .values("category__kode", "category__nama", "category__grup")
        .annotate(total=Count("id"))
        .order_by("-total", "category__nama")
    )
    total = sum(row["total"] for row in rows) or 1
    cumulative = 0
    for row in rows:
        cumulative += row["total"]
        row["pct"] = row["total"] / total * 100
        row["cum_pct"] = cumulative / total * 100
        row["grup_label"] = GRUP_LABELS.get(
            row["category__grup"], row["category__grup"]
        )
    if limit:
        return rows[:limit]
    return rows


def severity_breakdown(qs):
    rows = (
        InspectionDefect.objects.filter(unit__inspection__in=qs)
        .values("severity")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    labels = {"critical": "Critical", "major": "Major", "minor": "Minor"}
    return [
        {
            "severity": row["severity"],
            "label": labels.get(row["severity"], row["severity"]),
            "total": row["total"],
        }
        for row in rows
    ]


def daily_trend(qs, dari, sampai):
    rows = (
        qs.values("inspected_at__date")
        .annotate(inspected=Sum("qty_inspected"), failed=Sum("qty_fail"))
        .order_by("inspected_at__date")
    )
    by_date = {row["inspected_at__date"]: row for row in rows}

    trend = []
    current = dari
    while current <= sampai:
        row = by_date.get(current)
        inspected = (row["inspected"] or 0) if row else 0
        failed = (row["failed"] or 0) if row else 0
        trend.append(
            {
                "tanggal": current,
                "label": current.strftime("%d-%m"),
                "inspected": inspected,
                "failed": failed,
                "rate": (failed / inspected * 100) if inspected else 0,
            }
        )
        current += timedelta(days=1)
    return trend


def line_breakdown(qs):
    rows = (
        qs.values("batch__line__kode", "batch__line__nama")
        .annotate(
            inspected=Sum("qty_inspected"),
            failed=Sum("qty_fail"),
            sessions=Count("id"),
        )
        .order_by("batch__line__kode")
    )
    result = []
    for row in rows:
        inspected = row["inspected"] or 0
        failed = row["failed"] or 0
        result.append(
            {
                "kode": row["batch__line__kode"],
                "nama": row["batch__line__nama"],
                "inspected": inspected,
                "failed": failed,
                "rate": (failed / inspected * 100) if inspected else 0,
                "sessions": row["sessions"],
            }
        )
    return result


def product_breakdown(qs, limit=10):
    rows = (
        qs.values("batch__product__part_number", "batch__product__nama")
        .annotate(
            inspected=Sum("qty_inspected"),
            failed=Sum("qty_fail"),
        )
        .order_by("-inspected", "batch__product__nama")[:limit]
    )
    result = []
    for row in rows:
        inspected = row["inspected"] or 0
        failed = row["failed"] or 0
        result.append(
            {
                "part_number": row["batch__product__part_number"],
                "nama": row["batch__product__nama"],
                "inspected": inspected,
                "failed": failed,
                "rate": (failed / inspected * 100) if inspected else 0,
            }
        )
    return result


def previous_period_summary(dari, sampai, filters=None):
    span = (sampai - dari).days + 1
    prev_sampai = dari - timedelta(days=1)
    prev_dari = prev_sampai - timedelta(days=span - 1)
    qs = base_queryset(prev_dari, prev_sampai, filters)
    return summary(qs)


def report_rows(qs):
    """Baris laporan per sesi pemeriksaan (dipakai tabel & export)."""
    qs = qs.select_related(
        "batch__product", "batch__line", "batch__shift", "inspector"
    ).prefetch_related("units__defects__category")
    rows = []
    # "-id" sebagai tiebreaker agar urutan stabil bila jam inspeksi sama.
    for inspection in qs.order_by("-inspected_at", "-id"):
        categories = []
        for unit in inspection.units.all():
            for defect in unit.defects.all():
                if defect.category.nama not in categories:
                    categories.append(defect.category.nama)
        rows.append(
            {
                "kode_produksi": inspection.batch.kode,
                "tanggal": inspection.batch.tanggal_produksi,
                "produk": inspection.batch.product.nama,
                "part_number": inspection.batch.product.part_number,
                "line": inspection.batch.line.kode,
                "shift": inspection.batch.shift.kode,
                "metode": inspection.get_metode_display(),
                "total_produksi": inspection.total_production,
                "diperiksa": inspection.qty_inspected,
                "lolos": inspection.qty_pass,
                "cacat": inspection.qty_fail,
                "defect_rate": inspection.defect_rate,
                "kategori": ", ".join(categories) if categories else "-",
                "inspector": inspection.inspector.display_name,
                "status": inspection.get_status_display(),
            }
        )
    return rows
