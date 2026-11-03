from django.urls import path

from . import views

urlpatterns = [
    path("", views.inspection_list, name="inspection_list"),
    path("baru/", views.inspection_create, name="inspection_create"),
    path(
        "baru/batch/<int:batch_id>/",
        views.inspection_create,
        name="inspection_create_batch",
    ),
    path("riwayat/", views.inspection_history, name="inspection_history"),
    path("<int:pk>/", views.inspection_detail, name="inspection_detail"),
    path("<int:pk>/koreksi/", views.inspection_update, name="inspection_update"),
    path("<int:pk>/void/", views.inspection_void, name="inspection_void"),
]
