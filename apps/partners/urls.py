from django.urls import path

from . import views

urlpatterns = [
    path("", views.partner_list, name="list"),
    path("yeni/", views.partner_create, name="create"),
    path("<int:pk>/", views.partner_detail, name="detail"),
    path("<int:pk>/duzenle/", views.partner_edit, name="edit"),
]
