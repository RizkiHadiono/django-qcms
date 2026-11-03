from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from apps.core.decorators import supervisor_required
from apps.masterdata.models import Product, ProductionLine, Shift

from . import services
from .exports import export_csv, export_xlsx


def _filter_options():
    return {
        "lines": ProductionLine.objects.filter(is_active=True),
        "shifts": Shift.objects.filter(is_active=True),
        "products": Product.objects.filter(is_active=True),
    }


def _period_context(dari, sampai):
    today = timezone.localdate()
    return {
        "dari": dari,
        "sampai": sampai,
        "today": today,
        "presets": {
            "hari_ini": today,
            "tujuh_hari": today - timezone.timedelta(days=6),
            "tiga_puluh_hari": today - timezone.timedelta(days=29),
            "bulan_ini": today.replace(day=1),
        },
    }


@supervisor_required
def dashboard(request):
    dari, sampai = services.parse_period(request, default_days=7)
    filters = services.filters_from_request(request)
    qs = services.base_queryset(dari, sampai, filters)

    data = services.summary(qs)
    previous = services.previous_period_summary(dari, sampai, filters)
    delta = data["defect_rate"] - previous["defect_rate"]

    trend = services.daily_trend(qs, dari, sampai)
    pareto = services.pareto(qs, limit=8)
    severity = services.severity_breakdown(qs)
    lines = services.line_breakdown(qs)

    threshold = settings.QC_DEFECT_RATE_THRESHOLD
    chart_data = {
        "trend": {
            "labels": [row["label"] for row in trend],
            "rates": [round(row["rate"], 2) for row in trend],
            "inspected": [row["inspected"] for row in trend],
            "failed": [row["failed"] for row in trend],
            "threshold": threshold,
        },
        "pareto": {
            "labels": [row["category__nama"] for row in pareto],
            "totals": [row["total"] for row in pareto],
            "cumulative": [round(row["cum_pct"], 2) for row in pareto],
        },
        "severity": {
            "labels": [row["label"] for row in severity],
            "totals": [row["total"] for row in severity],
        },
        "composition": {
            "labels": ["Lolos", "Cacat"],
            "totals": [data["passed"], data["failed"]],
        },
    }

    return render(
        request,
        "reporting/dashboard.html",
        {
            "data": data,
            "previous": previous,
            "delta": delta,
            "threshold": threshold,
            "is_alert": data["defect_rate"] > threshold,
            "trend": trend,
            "pareto": pareto,
            "severity": severity,
            "lines": lines,
            "recent": qs.select_related(
                "batch__product", "batch__line", "inspector"
            ).order_by("-inspected_at", "-id")[:6],
            "chart_data": chart_data,
            "filters": filters,
            **_filter_options(),
            **_period_context(dari, sampai),
        },
    )


@supervisor_required
def analysis(request):
    dari, sampai = services.parse_period(request, default_days=30)
    filters = services.filters_from_request(request)
    qs = services.base_queryset(dari, sampai, filters)

    data = services.summary(qs)
    trend = services.daily_trend(qs, dari, sampai)
    pareto = services.pareto(qs)
    severity = services.severity_breakdown(qs)
    lines = services.line_breakdown(qs)
    products = services.product_breakdown(qs)

    threshold = settings.QC_DEFECT_RATE_THRESHOLD
    chart_data = {
        "trend": {
            "labels": [row["label"] for row in trend],
            "rates": [round(row["rate"], 2) for row in trend],
            "inspected": [row["inspected"] for row in trend],
            "failed": [row["failed"] for row in trend],
            "threshold": threshold,
        },
        "pareto": {
            "labels": [row["category__nama"] for row in pareto],
            "totals": [row["total"] for row in pareto],
            "cumulative": [round(row["cum_pct"], 2) for row in pareto],
        },
        "severity": {
            "labels": [row["label"] for row in severity],
            "totals": [row["total"] for row in severity],
        },
        "composition": {
            "labels": ["Lolos", "Cacat"],
            "totals": [data["passed"], data["failed"]],
        },
        "lines": {
            "labels": [row["kode"] for row in lines],
            "rates": [round(row["rate"], 2) for row in lines],
        },
    }

    return render(
        request,
        "reporting/analysis.html",
        {
            "data": data,
            "threshold": threshold,
            "is_alert": data["defect_rate"] > threshold,
            "trend": trend,
            "pareto": pareto,
            "severity": severity,
            "lines": lines,
            "products": products,
            "chart_data": chart_data,
            "filters": filters,
            **_filter_options(),
            **_period_context(dari, sampai),
        },
    )


def _report_context(request):
    dari, sampai = services.parse_period(request, default_days=0)
    if not request.GET.get("dari") and not request.GET.get("sampai"):
        today = timezone.localdate()
        dari = today.replace(day=1)
        sampai = today
    filters = services.filters_from_request(request)
    qs = services.base_queryset(dari, sampai, filters)
    rows = services.report_rows(qs)

    filter_labels = []
    if filters.get("line"):
        line = ProductionLine.objects.filter(pk=filters["line"]).first()
        if line:
            filter_labels.append(f"Line {line.kode}")
    if filters.get("shift"):
        shift = Shift.objects.filter(pk=filters["shift"]).first()
        if shift:
            filter_labels.append(f"Shift {shift.kode}")
    if filters.get("product"):
        product = Product.objects.filter(pk=filters["product"]).first()
        if product:
            filter_labels.append(f"Produk {product.part_number}")
    if filters.get("metode"):
        filter_labels.append("Metode " + filters["metode"])

    return {
        "rows": rows,
        "data": services.summary(qs),
        "dari": dari,
        "sampai": sampai,
        "filters": filters,
        "filter_text": ", ".join(filter_labels),
        **_filter_options(),
        **_period_context(dari, sampai),
    }


@supervisor_required
def reports(request):
    context = _report_context(request)
    paginator = Paginator(context["rows"], 25)
    context["page_obj"] = paginator.get_page(request.GET.get("page"))
    context["total_rows"] = len(context["rows"])
    return render(request, "reporting/reports.html", context)


@supervisor_required
def report_export_csv(request):
    context = _report_context(request)
    meta = {"filter_text": context["filter_text"]}
    return export_csv(context["rows"], context["dari"], context["sampai"], meta)


@supervisor_required
def report_export_xlsx(request):
    context = _report_context(request)
    meta = {"filter_text": context["filter_text"]}
    return export_xlsx(context["rows"], context["dari"], context["sampai"], meta)
