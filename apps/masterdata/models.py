from django.db import models


class Severity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    MAJOR = "major", "Major"
    MINOR = "minor", "Minor"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Dibuat", auto_now_add=True)
    updated_at = models.DateTimeField("Diperbarui", auto_now=True)

    class Meta:
        abstract = True


class ProductionLine(TimeStampedModel):
    kode = models.CharField(
        "Kode lini", max_length=10, unique=True, help_text="Contoh: L1"
    )
    nama = models.CharField("Nama lini", max_length=80)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Lini Produksi"
        verbose_name_plural = "Lini Produksi"
        ordering = ["kode"]

    def __str__(self):
        return f"{self.kode} - {self.nama}"


class Shift(TimeStampedModel):
    kode = models.CharField(
        "Kode shift", max_length=5, unique=True, help_text="Contoh: 1"
    )
    nama = models.CharField("Nama shift", max_length=80)
    jam_mulai = models.TimeField("Jam mulai")
    jam_selesai = models.TimeField("Jam selesai")
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Shift Kerja"
        verbose_name_plural = "Shift Kerja"
        ordering = ["kode"]

    def __str__(self):
        return f"Shift {self.kode} ({self.nama})"

    @property
    def rentang_jam(self):
        return f"{self.jam_mulai:%H:%M} - {self.jam_selesai:%H:%M}"


class Product(TimeStampedModel):
    part_number = models.CharField("Part number", max_length=50, unique=True)
    nama = models.CharField("Nama produk", max_length=120)
    customer = models.CharField("Customer", max_length=80, blank=True)
    model = models.CharField("Model kendaraan", max_length=80, blank=True)
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Produk"
        verbose_name_plural = "Produk"
        ordering = ["part_number"]

    def __str__(self):
        return f"{self.part_number} - {self.nama}"


class DefectCategory(TimeStampedModel):
    class Grup(models.TextChoices):
        ELECTRICAL = "electrical", "Electrical"
        CRIMPING = "crimping", "Crimping"
        CONNECTOR = "connector", "Connector"
        WIRE = "wire", "Wire"
        TAPING = "taping", "Taping / Sleeve"
        ROUTING = "routing", "Routing / Assembly"
        LABELING = "labeling", "Label / Marking"
        OTHER = "other", "Lainnya"

    kode = models.CharField("Kode", max_length=20, unique=True)
    nama = models.CharField("Nama kecacatan", max_length=120)
    grup = models.CharField(
        "Grup", max_length=20, choices=Grup.choices, default=Grup.OTHER
    )
    severity_default = models.CharField(
        "Severity bawaan",
        max_length=20,
        choices=Severity.choices,
        default=Severity.MAJOR,
    )
    is_active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name = "Kategori Kecacatan"
        verbose_name_plural = "Kategori Kecacatan"
        ordering = ["grup", "kode"]

    def __str__(self):
        return f"{self.kode} - {self.nama}"
