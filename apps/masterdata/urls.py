from django.urls import path

from . import views

urlpatterns = [
    path("produk/", views.master_list, {"key": "product"}, name="product_list"),
    path(
        "produk/baru/", views.master_create, {"key": "product"}, name="product_create"
    ),
    path(
        "produk/<int:pk>/ubah/",
        views.master_update,
        {"key": "product"},
        name="product_update",
    ),
    path(
        "produk/<int:pk>/aktif/",
        views.master_toggle,
        {"key": "product"},
        name="product_toggle",
    ),
    path("line/", views.master_list, {"key": "line"}, name="line_list"),
    path("line/baru/", views.master_create, {"key": "line"}, name="line_create"),
    path(
        "line/<int:pk>/ubah/",
        views.master_update,
        {"key": "line"},
        name="line_update",
    ),
    path(
        "line/<int:pk>/aktif/",
        views.master_toggle,
        {"key": "line"},
        name="line_toggle",
    ),
    path("shift/", views.master_list, {"key": "shift"}, name="shift_list"),
    path("shift/baru/", views.master_create, {"key": "shift"}, name="shift_create"),
    path(
        "shift/<int:pk>/ubah/",
        views.master_update,
        {"key": "shift"},
        name="shift_update",
    ),
    path(
        "shift/<int:pk>/aktif/",
        views.master_toggle,
        {"key": "shift"},
        name="shift_toggle",
    ),
    path("kecacatan/", views.master_list, {"key": "defect"}, name="defect_list"),
    path(
        "kecacatan/baru/",
        views.master_create,
        {"key": "defect"},
        name="defect_create",
    ),
    path(
        "kecacatan/<int:pk>/ubah/",
        views.master_update,
        {"key": "defect"},
        name="defect_update",
    ),
    path(
        "kecacatan/<int:pk>/aktif/",
        views.master_toggle,
        {"key": "defect"},
        name="defect_toggle",
    ),
]
