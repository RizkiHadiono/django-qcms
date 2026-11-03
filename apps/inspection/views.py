from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from apps.auditlog.models import AuditLog
from apps.auditlog.utils import log_action
from apps.core.decorators import qc_required, supervisor_required
from apps.masterdata.models import Product, ProductionLine, Shift
from apps.production.models import ProductionBatch

from .forms import InspectionForm, UnitFormSet
from .models import QcInspection
from .services import (
    collect_units,
    initial_units,
    persist_inspection,
    snapshot,
    validate_units,
    void_inspection,
)


def _filtered_queryset(request):
    qs = QcInspection.objects.select_related(
        "batch__product", "batch__line", "batch__shift", "inspector"
    )

    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(batch__kode__icontains=query)
            | Q(batch__product__part_number__icontains=query)
            | Q(batch__product__nama__icontains=query)
            | Q(inspector__username__icontains=query)
            | Q(inspector__nama_lengkap__icontains=query)
        )

    dari = parse_date(request.GET.get("dari", "") or "")
    sampai = parse_date(request.GET.get("sampai", "") or "")
    if dari:
        qs = qs.filter(inspected_at__date__gte=dari)
    if sampai:
        qs = qs.filter(inspected_at__date__lte=sampai)

    for key, field in (
        ("line", "batch__line_id"),
        ("shift", "batch__shift_id"),
        ("product", "batch__product_id"),
    ):
        value = request.GET.get(key, "")
        if value:
            qs = qs.filter(**{field: value})

    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)

    metode = request.GET.get("metode", "")
    if metode:
        qs = qs.filter(metode=metode)

    return qs


def _summary(qs):
    active = qs.exclude(status=QcInspection.Status.VOID)
    totals = active.aggregate(
        inspected=Sum("qty_inspected"), passed=Sum("qty_pass"), failed=Sum("qty_fail")
    )
    inspected = totals["inspected"] or 0
    failed = totals["failed"] or 0
    return {
        "inspected": inspected,
        "passed": totals["passed"] or 0,
        "failed": failed,
        "rate": (failed / inspected * 100) if inspected else 0,
        "sessions": active.count(),
    }


def _filter_options():
    return {
        "lines": ProductionLine.objects.filter(is_active=True),
        "shifts": Shift.objects.filter(is_active=True),
        "products": Product.objects.filter(is_active=True),
    }


@qc_required
def inspection_list(request):
    qs = _filtered_queryset(request)
    summary = _summary(qs)
    paginator = Paginator(qs, settings.QC_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inspection/list.html",
        {
            "page_obj": page,
            "summary": summary,
            "query": request.GET.get("q", ""),
            "selected": {
                "line": request.GET.get("line", ""),
                "shift": request.GET.get("shift", ""),
                "product": request.GET.get("product", ""),
                "status": request.GET.get("status", ""),
                "metode": request.GET.get("metode", ""),
                "dari": request.GET.get("dari", ""),
                "sampai": request.GET.get("sampai", ""),
            },
            **_filter_options(),
        },
    )


@qc_required
def inspection_history(request):
    qs = _filtered_queryset(request)
    if not request.GET.get("status"):
        qs = qs.exclude(status=QcInspection.Status.VOID)
    summary = _summary(qs)
    paginator = Paginator(qs, settings.QC_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inspection/history.html",
        {
            "page_obj": page,
            "summary": summary,
            "query": request.GET.get("q", ""),
            "selected": {
                "line": request.GET.get("line", ""),
                "shift": request.GET.get("shift", ""),
                "product": request.GET.get("product", ""),
                "status": request.GET.get("status", ""),
                "dari": request.GET.get("dari", ""),
                "sampai": request.GET.get("sampai", ""),
            },
            **_filter_options(),
        },
    )


def _render_form(request, form, formset, batch, title, inspection=None):
    return render(
        request,
        "inspection/form.html",
        {
            "form": form,
            "formset": formset,
            "batch": batch,
            "title": title,
            "inspection": inspection,
        },
    )


@qc_required
def inspection_create(request, batch_id=None):
    batch = None
    if batch_id:
        batch = get_object_or_404(
            ProductionBatch.objects.select_related("product", "line", "shift"),
            pk=batch_id,
        )

    form_kwargs = {"batch": batch} if batch else {}
    form = InspectionForm(request.POST or None, **form_kwargs)
    formset = UnitFormSet(request.POST or None, prefix="unit")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        units = collect_units(formset)
        errors = validate_units(units, form.cleaned_data["qty_fail"])
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            status = (
                QcInspection.Status.DRAFT
                if request.POST.get("action") == "draft"
                else QcInspection.Status.FINAL
            )
            inspection = persist_inspection(
                header_form=form, units=units, user=request.user, status=status
            )
            log_action(
                request.user,
                "create",
                inspection,
                snapshot(inspection),
                ringkasan=f"Pemeriksaan {inspection.batch.kode}",
            )
            messages.success(
                request,
                f"Pemeriksaan {inspection.batch.kode} berhasil disimpan "
                f"({inspection.defect_rate:.2f}% cacat).",
            )
            return redirect("inspection_detail", pk=inspection.pk)

    return _render_form(request, form, formset, batch, "Input Pemeriksaan QC")


@supervisor_required
def inspection_update(request, pk):
    inspection = get_object_or_404(
        QcInspection.objects.select_related("batch__product", "batch__line"), pk=pk
    )
    if inspection.is_void:
        messages.error(request, "Pemeriksaan yang sudah void tidak dapat diubah.")
        return redirect("inspection_detail", pk=inspection.pk)

    form = InspectionForm(
        request.POST or None, instance=inspection, batch=inspection.batch
    )
    formset = UnitFormSet(
        request.POST or None,
        prefix="unit",
        initial=None if request.method == "POST" else initial_units(inspection),
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        units = collect_units(formset)
        errors = validate_units(units, form.cleaned_data["qty_fail"])
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            before = snapshot(inspection)
            status = (
                QcInspection.Status.DRAFT
                if request.POST.get("action") == "draft"
                else QcInspection.Status.FINAL
            )
            inspection = persist_inspection(
                header_form=form,
                units=units,
                user=request.user,
                status=status,
                instance=inspection,
            )
            log_action(
                request.user,
                "update",
                inspection,
                {"sebelum": before, "sesudah": snapshot(inspection)},
                ringkasan=f"Koreksi pemeriksaan {inspection.batch.kode}",
            )
            messages.success(request, "Pemeriksaan berhasil diperbarui.")
            return redirect("inspection_detail", pk=inspection.pk)

    return _render_form(
        request,
        form,
        formset,
        inspection.batch,
        f"Koreksi Pemeriksaan: {inspection.batch.kode}",
        inspection=inspection,
    )


@qc_required
def inspection_detail(request, pk):
    inspection = get_object_or_404(
        QcInspection.objects.select_related(
            "batch__product", "batch__line", "batch__shift", "inspector", "voided_by"
        ),
        pk=pk,
    )
    units = inspection.units.prefetch_related("defects__category").all()
    audit_logs = AuditLog.objects.filter(
        model_name="QcInspection", object_id=str(inspection.pk)
    ).select_related("user")[:20]

    can_edit = request.user.is_supervisor and not inspection.is_void
    if (
        inspection.status == QcInspection.Status.DRAFT
        and inspection.inspector_id == request.user.id
    ):
        can_edit = True

    return render(
        request,
        "inspection/detail.html",
        {
            "inspection": inspection,
            "units": units,
            "audit_logs": audit_logs,
            "can_edit": can_edit,
            "can_void": request.user.is_supervisor and not inspection.is_void,
            "threshold": settings.QC_DEFECT_RATE_THRESHOLD,
        },
    )


@supervisor_required
def inspection_void(request, pk):
    inspection = get_object_or_404(QcInspection, pk=pk)
    if request.method != "POST":
        return redirect("inspection_detail", pk=pk)
    if inspection.is_void:
        messages.info(request, "Pemeriksaan ini sudah berstatus void.")
        return redirect("inspection_detail", pk=pk)

    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Alasan void wajib diisi.")
        return redirect("inspection_detail", pk=pk)

    void_inspection(inspection, request.user, reason)
    log_action(
        request.user,
        "void",
        inspection,
        {"alasan": reason},
        ringkasan=f"Void pemeriksaan {inspection.batch.kode}",
    )
    messages.success(
        request, "Pemeriksaan berhasil di-void dan tidak dihitung di laporan."
    )
    return redirect("inspection_detail", pk=pk)
