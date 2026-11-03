from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Pengguna aplikasi dengan role Admin / Supervisor QC / Petugas QC."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SUPERVISOR = "supervisor", "Supervisor QC"
        QC = "qc", "Petugas QC"

    nama_lengkap = models.CharField("Nama lengkap", max_length=120, blank=True)
    role = models.CharField(
        "Role", max_length=20, choices=Role.choices, default=Role.QC
    )

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"
        ordering = ["username"]

    def __str__(self):
        return self.nama_lengkap or self.username

    @property
    def display_name(self):
        return self.nama_lengkap or self.username

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_supervisor(self):
        return self.is_admin_role or self.role == self.Role.SUPERVISOR

    @property
    def is_qc(self):
        return self.role == self.Role.QC

    @property
    def role_label(self):
        return self.get_role_display()

    def save(self, *args, **kwargs):
        # Superuser selalu dianggap admin agar tidak terkunci dari menu.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)
