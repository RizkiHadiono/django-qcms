from django.contrib import admin

from .models import ProductionBatch


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = (
        "kode",
        "tanggal_produksi",
        "product",
        "line",
        "shift",
        "qty_plan",
    )
    list_filter = ("line", "shift", "tanggal_produksi")
    search_fields = ("kode", "product__part_number", "product__nama")
    readonly_fields = ("kode", "created_at")
    date_hierarchy = "tanggal_produksi"
