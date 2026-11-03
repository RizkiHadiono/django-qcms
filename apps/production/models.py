from django.conf import settings
from django.db import IntegrityError, models, transaction

from apps.masterdata.models import Product, ProductionLine, Shift


class ProductionBatch(models.Model):
    """Kelompok produksi (batch/lot) dengan kode yang dibuat otomatis."""

    kode = models.CharField("Kode produksi", max_length=32, unique=True, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="batches", verbose_name="Produk"
    )
    line = models.ForeignKey(
        ProductionLine,
        on_delete=models.PROTECT,
        related_name="batches",
        verbose_name="Lini produksi",
    )
    shift = models.ForeignKey(
        Shift, on_delete=models.PROTECT, related_name="batches", verbose_name="Shift"
    )
    tanggal_produksi = models.DateField("Tanggal produksi")
    qty_plan = models.PositiveIntegerField(
        "Jumlah produksi (unit)", help_text="Total unit yang diproduksi pada batch ini."
    )
    catatan = models.TextField("Catatan", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_batches",
        verbose_name="Dibuat oleh",
    )
    created_at = models.DateTimeField("Dibuat pada", auto_now_add=True)

    class Meta:
        verbose_name = "Batch Produksi"
        verbose_name_plural = "Batch Produksi"
        ordering = ["-tanggal_produksi", "-id"]
        indexes = [
            models.Index(fields=["tanggal_produksi"]),
            models.Index(fields=["kode"]),
        ]

    def __str__(self):
        return self.kode

    def save(self, *args, **kwargs):
        if self.kode:
            return super().save(*args, **kwargs)

        last_error = None
        for _ in range(5):
            try:
                with transaction.atomic():
                    self.kode = self.generate_kode(self.line, self.tanggal_produksi)
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:  # kode bentrok -> coba lagi
                last_error = exc
                self.kode = ""
        raise IntegrityError(
            "Gagal membuat kode produksi unik, silakan coba lagi."
        ) from last_error

    @staticmethod
    def prefix_for(line, tanggal):
        return f"QC-{tanggal:%Y%m%d}-{line.kode}"

    @classmethod
    def generate_kode(cls, line, tanggal):
        """Buat kode QC-YYYYMMDD-L{n}-{urut}. Harus dipanggil dalam transaksi."""
        prefix = cls.prefix_for(line, tanggal)
        last = (
            cls.objects.select_for_update()
            .filter(kode__startswith=f"{prefix}-")
            .order_by("-id")
            .first()
        )
        urut = 1
        if last:
            try:
                urut = int(last.kode.rsplit("-", 1)[1]) + 1
            except (ValueError, IndexError):
                urut = 1
        return f"{prefix}-{urut:03d}"

    @property
    def total_diperiksa(self):
        return sum(i.qty_inspected for i in self.inspections.filter(status="final"))

    @property
    def total_cacat(self):
        return sum(i.qty_fail for i in self.inspections.filter(status="final"))

    @property
    def defect_rate(self):
        inspected = self.total_diperiksa
        return (self.total_cacat / inspected * 100) if inspected else 0
