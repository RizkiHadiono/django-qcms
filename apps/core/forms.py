from django import forms


class BootstrapMixin:
    """Tambahkan class Bootstrap pada seluruh widget form secara otomatis."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                widget.attrs.setdefault("class", "defect-checks")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            elif isinstance(widget, forms.HiddenInput):
                continue
            else:
                widget.attrs.setdefault("class", "form-control")
            if field.required and not isinstance(
                widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)
            ):
                widget.attrs.setdefault("required", "required")


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None, **kwargs):
        attrs = {"class": "form-control", **(attrs or {})}
        super().__init__(attrs=attrs, **kwargs)


class TimeInput(forms.TimeInput):
    input_type = "time"

    def __init__(self, attrs=None, **kwargs):
        attrs = {"class": "form-control", **(attrs or {})}
        super().__init__(attrs=attrs, **kwargs)
