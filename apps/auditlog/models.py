from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Aksi(models.TextChoices):
        CREATE = "create", "Tambah"
        UPDATE = "update", "Ubah"
        VOID = "void", "Void"
        DELETE = "delete", "Hapus"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Pengguna",
    )
    aksi = models.CharField("Aksi", max_length=20, choices=Aksi.choices)
    model_name = models.CharField("Model", max_length=80)
    object_id = models.CharField("ID Objek", max_length=40, blank=True)
    ringkasan = models.CharField("Ringkasan", max_length=255, blank=True)
    changes = models.JSONField("Perubahan", default=dict, blank=True)
    created_at = models.DateTimeField("Waktu", auto_now_add=True)

    class Meta:
        verbose_name = "Jejak Audit"
        verbose_name_plural = "Jejak Audit"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        return f"{self.get_aksi_display()} {self.model_name}#{self.object_id}"
