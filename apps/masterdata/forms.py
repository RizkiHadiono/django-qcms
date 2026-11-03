from django import forms

from apps.core.forms import BootstrapMixin, TimeInput

from .models import DefectCategory, Product, ProductionLine, Shift


class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["part_number", "nama", "customer", "model", "is_active"]


class ProductionLineForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ProductionLine
        fields = ["kode", "nama", "is_active"]

    def clean_kode(self):
        return self.cleaned_data["kode"].strip().upper()


class ShiftForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["kode", "nama", "jam_mulai", "jam_selesai", "is_active"]
        widgets = {
            "jam_mulai": TimeInput(),
            "jam_selesai": TimeInput(),
        }


class DefectCategoryForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DefectCategory
        fields = ["kode", "nama", "grup", "severity_default", "is_active"]

    def clean_kode(self):
        return self.cleaned_data["kode"].strip().upper()
