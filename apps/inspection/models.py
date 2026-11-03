from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.masterdata.models import DefectCategory, Severity
from apps.production.models import ProductionBatch


class QcInspection(models.Model):
    """Satu sesi pemeriksaan QC pada sebuah batch produksi."""

    class Metode(models.TextChoices):
        FULL = "full", "Full Inspection"
        SAMPLING = "sampling", "Sampling Inspection"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINAL = "final", "Final"
        VOID = "void", "Void"

    batch = models.ForeignKey(
        ProductionBatch,
        on_delete=models.PROTECT,
        related_name="inspections",
        verbose_name="Batch produksi",
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspections",
        verbose_name="Petugas QC",
    )
    metode = models.CharField(
        "Metode pemeriksaan",
        max_length=20,
        choices=Metode.choices,
        default=Metode.FULL,
    )
    total_production = models.PositiveIntegerField("Total produksi (unit)")
    sample_size = models.PositiveIntegerField(
        "Jumlah sampel", null=True, blank=True, help_text="Hanya untuk metode sampling."
    )
    qty_inspected = models.PositiveIntegerField("Diperiksa (unit)")
    qty_pass = models.PositiveIntegerField("Lolos (unit)", default=0)
    qty_fail = models.PositiveIntegerField("Cacat (unit)", default=0)
    inspected_at = models.DateTimeField("Waktu pemeriksaan", default=timezone.now)
    status = models.CharField(
        "Status", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    catatan = models.TextField("Catatan", blank=True)
    void_reason = models.TextField("Alasan void", blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voided_inspections",
        verbose_name="Di-void oleh",
    )
    voided_at = models.DateTimeField("Waktu void", null=True, blank=True)
    created_at = models.DateTimeField("Dibuat pada", auto_now_add=True)
    updated_at = models.DateTimeField("Diperbarui pada", auto_now=True)

    class Meta:
        verbose_name = "Pemeriksaan QC"
        verbose_name_plural = "Pemeriksaan QC"
        ordering = ["-inspected_at", "-id"]
        indexes = [
            models.Index(fields=["inspected_at"]),
            models.Index(fields=["status", "inspected_at"]),
        ]

    def __str__(self):
        return f"{self.batch.kode} - {self.inspected_at:%d-%m-%Y %H:%M}"

    def clean(self):
        if self.qty_pass + self.qty_fail != self.qty_inspected:
            raise ValidationError(
                "Jumlah lolos + cacat harus sama dengan jumlah diperiksa."
            )
        if self.qty_fail > self.qty_inspected:
            raise ValidationError("Jumlah cacat tidak boleh melebihi jumlah diperiksa.")
        if self.metode == self.Metode.SAMPLING:
            if not self.sample_size:
                raise ValidationError(
                    "Jumlah sampel wajib diisi untuk metode sampling."
                )
            if self.sample_size > self.total_production:
                raise ValidationError(
                    "Jumlah sampel tidak boleh melebihi total produksi."
                )

    # --- Metrik turunan -------------------------------------------------
    @property
    def defect_rate(self):
        if not self.qty_inspected:
            return 0
        return self.qty_fail / self.qty_inspected * 100

    @property
    def pass_rate(self):
        if not self.qty_inspected:
            return 0
        return self.qty_pass / self.qty_inspected * 100

    @property
    def coverage(self):
        if not self.total_production:
            return 0
        return self.qty_inspected / self.total_production * 100

    @property
    def defect_occurrences(self):
        return sum(unit.defects.count() for unit in self.units.all())

    @property
    def dpu(self):
        """Defect per unit: jumlah kejadian cacat dibagi unit yang diperiksa."""
        if not self.qty_inspected:
            return 0
        return self.defect_occurrences / self.qty_inspected

    @property
    def detailed_units(self):
        return self.units.count()

    @property
    def unclassified_units(self):
        return max(self.qty_fail - self.detailed_units, 0)

    @property
    def is_void(self):
        return self.status == self.Status.VOID

    @property
    def is_editable(self):
        return self.status != self.Status.VOID


class InspectionUnit(models.Model):
    """Unit produk cacat yang diperiksa (detail per unit)."""

    inspection = models.ForeignKey(
        QcInspection,
        on_delete=models.CASCADE,
        related_name="units",
        verbose_name="Pemeriksaan",
    )
    unit_ref = models.CharField("Kode unit", max_length=32)
    is_pass = models.BooleanField("Lolos", default=False)
    catatan = models.CharField("Catatan", max_length=255, blank=True)

    class Meta:
        verbose_name = "Unit Diperiksa"
        verbose_name_plural = "Unit Diperiksa"
        ordering = ["unit_ref"]
        constraints = [
            models.UniqueConstraint(
                fields=["inspection", "unit_ref"], name="unique_unit_per_inspection"
            )
        ]

    def __str__(self):
        return f"{self.inspection.batch.kode} / {self.unit_ref}"


class InspectionDefect(models.Model):
    """Satu jenis kecacatan pada satu unit. Satu unit boleh punya banyak kecacatan."""

    unit = models.ForeignKey(
        InspectionUnit,
        on_delete=models.CASCADE,
        related_name="defects",
        verbose_name="Unit",
    )
    category = models.ForeignKey(
        DefectCategory,
        on_delete=models.PROTECT,
        related_name="defects",
        verbose_name="Kategori kecacatan",
    )
    severity = models.CharField(
        "Severity", max_length=20, choices=Severity.choices, default=Severity.MAJOR
    )
    catatan = models.CharField("Catatan", max_length=255, blank=True)

    class Meta:
        verbose_name = "Detail Kecacatan"
        verbose_name_plural = "Detail Kecacatan"
        ordering = ["category__nama"]
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "category"], name="unique_category_per_unit"
            )
        ]

    def __str__(self):
        return f"{self.unit.unit_ref} - {self.category.nama}"
