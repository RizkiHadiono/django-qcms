from django.contrib import admin

from .models import DefectCategory, Product, ProductionLine, Shift


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("part_number", "nama", "customer", "model", "is_active")
    list_filter = ("is_active", "customer")
    search_fields = ("part_number", "nama")


@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    list_display = ("kode", "nama", "is_active")
    search_fields = ("kode", "nama")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("kode", "nama", "jam_mulai", "jam_selesai", "is_active")


@admin.register(DefectCategory)
class DefectCategoryAdmin(admin.ModelAdmin):
    list_display = ("kode", "nama", "grup", "severity_default", "is_active")
    list_filter = ("grup", "severity_default", "is_active")
    search_fields = ("kode", "nama")
