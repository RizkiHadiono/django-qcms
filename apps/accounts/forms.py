from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.core.forms import BootstrapMixin

from .models import User


class UserCreateForm(BootstrapMixin, UserCreationForm):
    nama_lengkap = forms.CharField(label="Nama lengkap", max_length=120, required=True)

    class Meta:
        model = User
        fields = ["username", "nama_lengkap", "role", "is_active"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.nama_lengkap = self.cleaned_data["nama_lengkap"]
        if commit:
            user.save()
        return user


class UserUpdateForm(BootstrapMixin, forms.ModelForm):
    password_baru = forms.CharField(
        label="Password baru",
        required=False,
        widget=forms.PasswordInput,
        help_text="Kosongkan bila tidak ingin mengubah password.",
    )

    class Meta:
        model = User
        fields = ["username", "nama_lengkap", "role", "is_active"]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password_baru")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
