from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "aksi",
        "model_name",
        "object_id",
        "ringkasan",
    )
    list_filter = ("aksi", "model_name")
    search_fields = ("ringkasan", "object_id")
    readonly_fields = (
        "user",
        "aksi",
        "model_name",
        "object_id",
        "ringkasan",
        "changes",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
