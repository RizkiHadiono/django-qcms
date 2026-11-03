from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "nama_lengkap", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Profil QC", {"fields": ("nama_lengkap", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profil QC", {"fields": ("nama_lengkap", "role")}),
    )
