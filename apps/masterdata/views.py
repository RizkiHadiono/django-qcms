"""View master data yang dikendalikan konfigurasi agar konsisten dan ringkas."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.auditlog.utils import log_action
from apps.core.decorators import admin_required, qc_required

from .forms import DefectCategoryForm, ProductForm, ProductionLineForm, ShiftForm
from .models import DefectCategory, Product, ProductionLine, Shift


def _active_badge(obj):
    return "Aktif" if obj.is_active else "Nonaktif"


MASTERS = {
    "product": {
        "model": Product,
        "form": ProductForm,
        "title": "Data Produk",
        "singular": "Produk",
        "description": "Daftar part number rangkaian kabel yang diproduksi.",
        "search_fields": ["part_number", "nama", "customer", "model"],
        "columns": [
            ("Part Number", "part_number", "mono"),
            ("Nama Produk", "nama", "text"),
            ("Customer", "customer", "text"),
            ("Model", "model", "text"),
            ("Status", _active_badge, "status"),
        ],
        "urls": {
            "list": "product_list",
            "create": "product_create",
            "update": "product_update",
            "toggle": "product_toggle",
        },
    },
    "line": {
        "model": ProductionLine,
        "form": ProductionLineForm,
        "title": "Lini Produksi",
        "singular": "Lini Produksi",
        "description": "Lini perakitan tempat batch produksi dijalankan.",
        "search_fields": ["kode", "nama"],
        "columns": [
            ("Kode", "kode", "mono"),
            ("Nama Lini", "nama", "text"),
            ("Status", _active_badge, "status"),
        ],
        "urls": {
            "list": "line_list",
            "create": "line_create",
            "update": "line_update",
            "toggle": "line_toggle",
        },
    },
    "shift": {
        "model": Shift,
        "form": ShiftForm,
        "title": "Shift Kerja",
        "singular": "Shift",
        "description": "Pembagian shift kerja beserta rentang jamnya.",
        "search_fields": ["kode", "nama"],
        "columns": [
            ("Kode", "kode", "mono"),
            ("Nama Shift", "nama", "text"),
            ("Jam Kerja", "rentang_jam", "mono"),
            ("Status", _active_badge, "status"),
        ],
        "urls": {
            "list": "shift_list",
            "create": "shift_create",
            "update": "shift_update",
            "toggle": "shift_toggle",
        },
    },
    "defect": {
        "model": DefectCategory,
        "form": DefectCategoryForm,
        "title": "Data Kecacatan",
        "singular": "Kategori Kecacatan",
        "description": "Kategori kerusakan yang dipakai saat pemeriksaan QC.",
        "search_fields": ["kode", "nama", "grup"],
        "columns": [
            ("Kode", "kode", "mono"),
            ("Nama Kecacatan", "nama", "text"),
            ("Grup", "get_grup_display", "text"),
            ("Severity", "get_severity_default_display", "severity"),
            ("Status", _active_badge, "status"),
        ],
        "urls": {
            "list": "defect_list",
            "create": "defect_create",
            "update": "defect_update",
            "toggle": "defect_toggle",
        },
    },
}


def _get_config(key):
    try:
        return MASTERS[key]
    except KeyError as exc:  # pragma: no cover - salah konfigurasi url
        raise Http404("Master data tidak dikenal") from exc


def _build_rows(objects, columns):
    rows = []
    for obj in objects:
        cells = []
        for label, accessor, kind in columns:
            value = accessor(obj) if callable(accessor) else getattr(obj, accessor, "")
            cells.append({"label": label, "value": value, "kind": kind})
        rows.append({"obj": obj, "cells": cells, "active": obj.is_active})
    return rows


@qc_required
def master_list(request, key):
    config = _get_config(key)
    query = request.GET.get("q", "").strip()
    qs = config["model"].objects.all()
    if query:
        condition = Q()
        for field in config["search_fields"]:
            condition |= Q(**{f"{field}__icontains": query})
        qs = qs.filter(condition)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "masterdata/list.html",
        {
            "config": config,
            "key": key,
            "page_obj": page,
            "rows": _build_rows(page.object_list, config["columns"]),
            "query": query,
            "total": qs.count(),
            "can_edit": request.user.is_admin_role,
        },
    )


@admin_required
def master_create(request, key):
    config = _get_config(key)
    form = config["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        log_action(request.user, "create", obj)
        messages.success(request, f"{config['singular']} berhasil ditambahkan.")
        return redirect(config["urls"]["list"])
    return render(
        request,
        "masterdata/form.html",
        {
            "config": config,
            "key": key,
            "form": form,
            "title": f"Tambah {config['singular']}",
        },
    )


@admin_required
def master_update(request, key, pk):
    config = _get_config(key)
    obj = get_object_or_404(config["model"], pk=pk)
    form = config["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        changes = {}
        for field in form.changed_data:
            changes[field] = [
                str(form.initial.get(field, "")),
                str(form.cleaned_data.get(field, "")),
            ]
        form.save()
        log_action(request.user, "update", obj, changes)
        messages.success(request, f"{config['singular']} berhasil diperbarui.")
        return redirect(config["urls"]["list"])
    return render(
        request,
        "masterdata/form.html",
        {
            "config": config,
            "key": key,
            "form": form,
            "title": f"Ubah {config['singular']}",
            "object": obj,
        },
    )


@admin_required
def master_toggle(request, key, pk):
    config = _get_config(key)
    obj = get_object_or_404(config["model"], pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active", "updated_at"])
    log_action(request.user, "update", obj, {"is_active": ["", str(obj.is_active)]})
    state = "diaktifkan" if obj.is_active else "dinonaktifkan"
    messages.success(request, f"{config['singular']} {state}.")
    return redirect(config["urls"]["list"])
