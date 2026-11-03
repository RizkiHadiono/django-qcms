from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from apps.auditlog.utils import log_action
from apps.core.decorators import qc_required
from apps.masterdata.models import Product, ProductionLine

from .forms import ProductionBatchForm
from .models import ProductionBatch


@qc_required
def batch_list(request):
    query = request.GET.get("q", "").strip()
    line_id = request.GET.get("line", "")
    product_id = request.GET.get("product", "")
    dari = request.GET.get("dari", "")
    sampai = request.GET.get("sampai", "")

    batches = (
        ProductionBatch.objects.select_related("product", "line", "shift")
        .annotate(
            jumlah_pemeriksaan=Count(
                "inspections", filter=Q(inspections__status="final")
            )
        )
        .order_by("-tanggal_produksi", "-id")
    )

    if query:
        batches = batches.filter(
            Q(kode__icontains=query)
            | Q(product__part_number__icontains=query)
            | Q(product__nama__icontains=query)
        )
    if line_id:
        batches = batches.filter(line_id=line_id)
    if product_id:
        batches = batches.filter(product_id=product_id)
    if dari and parse_date(dari):
        batches = batches.filter(tanggal_produksi__gte=parse_date(dari))
    if sampai and parse_date(sampai):
        batches = batches.filter(tanggal_produksi__lte=parse_date(sampai))

    paginator = Paginator(batches, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "production/batch_list.html",
        {
            "page_obj": page,
            "query": query,
            "lines": ProductionLine.objects.filter(is_active=True),
            "products": Product.objects.filter(is_active=True),
            "selected": {
                "line": line_id,
                "product": product_id,
                "dari": dari,
                "sampai": sampai,
            },
            "total": batches.count(),
        },
    )


@qc_required
def batch_create(request):
    form = ProductionBatchForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        batch = form.save(commit=False)
        batch.created_by = request.user
        batch.save()
        log_action(request.user, "create", batch, {"kode": batch.kode})
        messages.success(
            request,
            f"Batch produksi {batch.kode} berhasil dibuat. Silakan lanjut input pemeriksaan.",
        )
        return redirect("inspection_create", batch_id=batch.pk)
    return render(
        request,
        "production/batch_form.html",
        {"form": form, "title": "Buat Batch Produksi"},
    )


@qc_required
def batch_detail(request, pk):
    batch = get_object_or_404(
        ProductionBatch.objects.select_related("product", "line", "shift"), pk=pk
    )
    inspections = batch.inspections.select_related("inspector").order_by(
        "-inspected_at", "-id"
    )
    return render(
        request,
        "production/batch_detail.html",
        {"batch": batch, "inspections": inspections},
    )
