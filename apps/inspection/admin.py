from django.contrib import admin

from .models import InspectionDefect, InspectionUnit, QcInspection


class InspectionUnitInline(admin.TabularInline):
    model = InspectionUnit
    extra = 0


@admin.register(QcInspection)
class QcInspectionAdmin(admin.ModelAdmin):
    list_display = (
        "batch",
        "inspector",
        "metode",
        "qty_inspected",
        "qty_pass",
        "qty_fail",
        "status",
        "inspected_at",
    )
    list_filter = ("status", "metode", "inspected_at")
    search_fields = ("batch__kode", "batch__product__part_number")
    date_hierarchy = "inspected_at"
    inlines = [InspectionUnitInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(InspectionDefect)
class InspectionDefectAdmin(admin.ModelAdmin):
    list_display = ("unit", "category", "severity")
    list_filter = ("severity", "category")
