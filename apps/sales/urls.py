from django.urls import path

from . import views

urlpatterns = [
    path("", views.pool, name="pool"),
    path("<int:pk>/", views.order_detail, name="detail"),
]
