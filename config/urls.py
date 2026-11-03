from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("", core_views.home, name="home"),
    path("healthz", core_views.healthz, name="healthz"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("akun/", include("apps.accounts.urls")),
    path("master/", include("apps.masterdata.urls")),
    path("produksi/", include("apps.production.urls")),
    path("pemeriksaan/", include("apps.inspection.urls")),
    path("", include("apps.reporting.urls")),
    path("django-admin/", admin.site.urls),
]

admin.site.site_header = f"{settings.APP_NAME} Administration"
admin.site.site_title = settings.APP_NAME
admin.site.index_title = "Administrasi Data"

# Halaman error kustom (dipakai saat DEBUG=False).
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
