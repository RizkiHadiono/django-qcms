from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analisis/", views.analysis, name="analysis"),
    path("laporan/", views.reports, name="reports"),
    path("laporan/export/csv/", views.report_export_csv, name="report_export_csv"),
    path("laporan/export/xlsx/", views.report_export_xlsx, name="report_export_xlsx"),
]
