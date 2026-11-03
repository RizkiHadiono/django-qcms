from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*roles):
    """Batasi view hanya untuk role tertentu. Superuser selalu diizinkan."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect("login")
            if user.is_superuser or user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(
                request, "Anda tidak memiliki hak akses untuk halaman tersebut."
            )
            return redirect("home")

        return _wrapped

    return decorator


def supervisor_required(view_func):
    return role_required("admin", "supervisor")(view_func)


def admin_required(view_func):
    return role_required("admin")(view_func)


def qc_required(view_func):
    return role_required("admin", "supervisor", "qc")(view_func)


class RolePermissionMixin:
    """Mixin untuk class-based view: batasi berdasarkan role."""

    allowed_roles = ("admin", "supervisor", "qc")

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect("login")
        if not (user.is_superuser or user.role in self.allowed_roles):
            raise PermissionDenied("Anda tidak memiliki hak akses.")
        return super().dispatch(request, *args, **kwargs)
