from django import forms
from django.utils import timezone

from apps.core.forms import BootstrapMixin, DateInput
from apps.masterdata.models import Product, ProductionLine, Shift

from .models import ProductionBatch


class ProductionBatchForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ProductionBatch
        fields = ["product", "line", "shift", "tanggal_produksi", "qty_plan", "catatan"]
        widgets = {
            "tanggal_produksi": DateInput(),
            "catatan": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True)
        self.fields["line"].queryset = ProductionLine.objects.filter(is_active=True)
        self.fields["shift"].queryset = Shift.objects.filter(is_active=True)
        self.fields["tanggal_produksi"].initial = timezone.localdate()
        self.fields["qty_plan"].widget.attrs.setdefault("min", 1)
        self.fields["product"].empty_label = "-- Pilih produk --"
        self.fields["line"].empty_label = "-- Pilih lini --"
        self.fields["shift"].empty_label = "-- Pilih shift --"

    def clean_qty_plan(self):
        qty = self.cleaned_data["qty_plan"]
        if qty <= 0:
            raise forms.ValidationError("Jumlah produksi harus lebih dari 0.")
        return qty
