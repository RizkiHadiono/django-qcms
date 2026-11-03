from django.db import transaction

from .models import InspectionDefect, InspectionUnit, QcInspection


def collect_units(formset):
    """Ambil baris unit yang benar-benar diisi dari formset."""
    units = []
    for form in formset.forms:
        data = getattr(form, "cleaned_data", None)
        if not data:
            continue
        if data.get("DELETE"):
            continue
        units.append(data)
    return units


def validate_units(units, qty_fail):
    """Validasi silang antara detail unit dan jumlah cacat."""
    errors = []
    if len(units) > qty_fail:
        errors.append(
            f"Detail unit ({len(units)}) tidak boleh melebihi jumlah unit cacat ({qty_fail})."
        )
    refs = [u["unit_ref"].strip().upper() for u in units]
    duplicates = {ref for ref in refs if refs.count(ref) > 1}
    if duplicates:
        errors.append(
            "Kode unit tidak boleh ganda: " + ", ".join(sorted(duplicates)) + "."
        )
    return errors


def initial_units(inspection):
    """Siapkan data awal formset saat mengedit pemeriksaan."""
    initial = []
    for unit in inspection.units.prefetch_related("defects").all():
        defects = list(unit.defects.all())
        initial.append(
            {
                "unit_ref": unit.unit_ref,
                "categories": [d.category_id for d in defects],
                "severity": defects[0].severity if defects else "major",
                "catatan": unit.catatan,
            }
        )
    return initial


@transaction.atomic
def persist_inspection(*, header_form, units, user, status, instance=None):
    """Simpan header + detail unit + kecacatan dalam satu transaksi."""
    inspection = header_form.save(commit=False)
    cleaned = header_form.cleaned_data

    inspection.qty_inspected = cleaned["qty_inspected"]
    inspection.qty_fail = cleaned["qty_fail"]
    inspection.qty_pass = inspection.qty_inspected - inspection.qty_fail
    inspection.status = status

    if instance is not None:
        inspection.pk = instance.pk
        inspection.inspector = instance.inspector
        inspection.created_at = instance.created_at
    else:
        inspection.inspector = user

    inspection.full_clean()
    inspection.save()

    # Tulis ulang detail agar konsisten dengan input terbaru.
    inspection.units.all().delete()
    for data in units:
        unit = InspectionUnit.objects.create(
            inspection=inspection,
            unit_ref=data["unit_ref"].strip().upper(),
            catatan=data.get("catatan", ""),
        )
        for category in data["categories"]:
            InspectionDefect.objects.create(
                unit=unit,
                category=category,
                severity=data["severity"],
                catatan=data.get("catatan", ""),
            )

    return inspection


def snapshot(inspection):
    """Ringkasan untuk audit log."""
    return {
        "kode_produksi": inspection.batch.kode,
        "status": inspection.status,
        "diperiksa": inspection.qty_inspected,
        "lolos": inspection.qty_pass,
        "cacat": inspection.qty_fail,
        "detail_unit": inspection.units.count(),
        "metode": inspection.metode,
    }


def void_inspection(inspection, user, reason):
    from django.utils import timezone

    inspection.status = QcInspection.Status.VOID
    inspection.void_reason = reason
    inspection.voided_by = user
    inspection.voided_at = timezone.now()
    inspection.save(
        update_fields=["status", "void_reason", "voided_by", "voided_at", "updated_at"]
    )
    return inspection
