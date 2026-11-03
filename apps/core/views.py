from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect


@login_required
def home(request):
    """Arahkan pengguna ke halaman awal sesuai rolenya."""
    user = request.user
    if user.is_superuser or user.role in ("admin", "supervisor"):
        return redirect("dashboard")
    return redirect("inspection_list")


def healthz(request):
    """Healthcheck sederhana untuk container/orchestrator."""
    return HttpResponse("ok", content_type="text/plain")


def error_403(request, exception=None):
    from django.shortcuts import render

    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    from django.shortcuts import render

    return render(request, "errors/404.html", status=404)


def error_500(request):
    from django.shortcuts import render

    return render(request, "errors/500.html", status=500)
