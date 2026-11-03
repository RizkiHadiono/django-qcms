from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.auditlog.utils import log_action
from apps.core.decorators import admin_required

from .forms import UserCreateForm, UserUpdateForm
from .models import User


@admin_required
def user_list(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.all()
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(nama_lengkap__icontains=query)
            | Q(role__icontains=query)
        )
    paginator = Paginator(users, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "accounts/user_list.html",
        {"page_obj": page, "query": query, "total": users.count()},
    )


@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_action(request.user, "create", user, {"username": user.username})
        messages.success(request, f"Pengguna {user.username} berhasil dibuat.")
        return redirect("user_list")
    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "title": "Tambah Pengguna"},
    )


@admin_required
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        changes = {}
        for field in ("username", "nama_lengkap", "role", "is_active"):
            old = getattr(user, field)
            new = form.cleaned_data.get(field)
            if str(old) != str(new):
                changes[field] = [str(old), str(new)]
        form.save()
        if changes:
            log_action(request.user, "update", user, changes)
        messages.success(request, f"Pengguna {user.username} diperbarui.")
        return redirect("user_list")
    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "title": f"Ubah Pengguna: {user.username}", "object": user},
    )


@admin_required
def user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "Anda tidak dapat menonaktifkan akun sendiri.")
        return redirect("user_list")
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    log_action(request.user, "update", user, {"is_active": ["", str(user.is_active)]})
    state = "diaktifkan" if user.is_active else "dinonaktifkan"
    messages.success(request, f"Pengguna {user.username} {state}.")
    return redirect("user_list")
