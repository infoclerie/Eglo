from django.urls import path

from . import views

urlpatterns = [
    path("", views.order_list, name="list"),
    path("yeni/", views.new, name="new"),
    path("<int:pk>/", views.detail, name="detail"),
]
