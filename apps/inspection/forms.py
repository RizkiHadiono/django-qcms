from django import forms
from django.forms import BaseFormSet, formset_factory
from django.utils import timezone

from apps.core.forms import BootstrapMixin
from apps.masterdata.models import DefectCategory, Severity
from apps.production.models import ProductionBatch

from .models import QcInspection


class InspectionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = QcInspection
        fields = [
            "batch",
            "metode",
            "total_production",
            "sample_size",
            "qty_fail",
            "catatan",
        ]
        widgets = {
            "catatan": forms.Textarea(attrs={"rows": 2}),
            "qty_fail": forms.NumberInput(attrs={"min": 0}),
            "total_production": forms.NumberInput(attrs={"min": 1}),
            "sample_size": forms.NumberInput(attrs={"min": 1}),
        }
        labels = {
            "qty_fail": "Jumlah unit cacat",
        }
        help_texts = {
            "qty_fail": "Total unit yang tidak lolos pemeriksaan.",
            "total_production": "Total unit yang diproduksi pada batch ini.",
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_batch = batch
        if batch is not None:
            self.fields["batch"].queryset = ProductionBatch.objects.filter(pk=batch.pk)
            self.fields["batch"].initial = batch.pk
            self.fields["batch"].widget = forms.HiddenInput()
            self.fields["total_production"].initial = batch.qty_plan
        else:
            cutoff = timezone.localdate() - timezone.timedelta(days=180)
            self.fields["batch"].queryset = (
                ProductionBatch.objects.select_related("product", "line", "shift")
                .filter(tanggal_produksi__gte=cutoff)
                .order_by("-tanggal_produksi", "-id")
            )
        self.fields["batch"].empty_label = "-- Pilih batch produksi --"

    def clean(self):
        cleaned = super().clean()
        metode = cleaned.get("metode")
        total = cleaned.get("total_production")
        sample = cleaned.get("sample_size")
        qty_fail = cleaned.get("qty_fail")

        if total is None or metode is None:
            return cleaned

        if total <= 0:
            self.add_error("total_production", "Total produksi harus lebih dari 0.")

        if metode == QcInspection.Metode.FULL:
            cleaned["sample_size"] = None
            inspected = total
        else:
            if not sample:
                self.add_error(
                    "sample_size", "Jumlah sampel wajib diisi untuk metode sampling."
                )
                inspected = 0
            elif sample > total:
                self.add_error(
                    "sample_size",
                    "Jumlah sampel tidak boleh melebihi total produksi.",
                )
                inspected = sample
            else:
                inspected = sample

        cleaned["qty_inspected"] = inspected

        if qty_fail is not None and inspected and qty_fail > inspected:
            self.add_error(
                "qty_fail",
                f"Jumlah cacat ({qty_fail}) melebihi jumlah diperiksa ({inspected}).",
            )
        return cleaned

    def _post_clean(self):
        # ModelForm memanggil full_clean() pada instance. Saat mengedit,
        # qty_inspected/qty_pass masih nilai lama sehingga validasi silang model
        # akan gagal. Samakan dulu dengan hasil perhitungan form.
        if "qty_inspected" in self.cleaned_data:
            inspected = self.cleaned_data["qty_inspected"]
            qty_fail = self.cleaned_data.get("qty_fail") or 0
            self.instance.qty_inspected = inspected
            self.instance.qty_fail = qty_fail
            self.instance.qty_pass = inspected - qty_fail
        super()._post_clean()


class UnitForm(forms.Form):
    """Satu unit cacat beserta satu atau lebih kategori kecacatan."""

    unit_ref = forms.CharField(
        label="Kode unit",
        max_length=32,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )
    categories = forms.ModelMultipleChoiceField(
        label="Kategori kecacatan",
        queryset=DefectCategory.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "defect-checks"}),
        error_messages={
            "required": "Pilih minimal satu kategori kecacatan.",
        },
    )
    severity = forms.ChoiceField(
        label="Severity",
        choices=Severity.choices,
        initial=Severity.MAJOR,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    catatan = forms.CharField(
        label="Catatan",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = DefectCategory.objects.filter(
            is_active=True
        ).order_by("grup", "kode")


class BaseUnitFormSet(BaseFormSet):
    """Formset unit: baris tambahan boleh kosong, tapi baris terisi wajib valid."""

    def _construct_form(self, i, **kwargs):
        form = super()._construct_form(i, **kwargs)
        if i >= self.initial_form_count():
            form.empty_permitted = True
        return form


UnitFormSet = formset_factory(
    UnitForm, formset=BaseUnitFormSet, extra=0, can_delete=True
)
