from django.urls import path

from . import views

urlpatterns = [
    path("<int:pk>/fotograflar/", views.photos, name="photos"),
]
