from django.urls import path

from . import views

urlpatterns = [
    path("", views.user_list, name="user_list"),
    path("baru/", views.user_create, name="user_create"),
    path("<int:pk>/ubah/", views.user_update, name="user_update"),
    path("<int:pk>/aktif/", views.user_toggle, name="user_toggle"),
]
