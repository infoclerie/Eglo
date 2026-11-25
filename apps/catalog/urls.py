from django.urls import path

from . import views

urlpatterns = [
    path("", views.product_list, name="list"),
    path("yeni/", views.product_create, name="create"),
    path("<int:pk>/", views.product_detail, name="detail"),
    path("<int:pk>/duzenle/", views.product_edit, name="edit"),
    path("<int:pk>/fotograflar/", views.photos, name="photos"),
    path("alt-kategoriler/", views.subcategories, name="subcategories"),
]
