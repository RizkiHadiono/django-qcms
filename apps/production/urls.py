from django.urls import path

from . import views

urlpatterns = [
    path("", views.batch_list, name="batch_list"),
    path("baru/", views.batch_create, name="batch_create"),
    path("<int:pk>/", views.batch_detail, name="batch_detail"),
]
