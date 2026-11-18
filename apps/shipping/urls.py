from django.urls import path

from . import views

urlpatterns = [
    path("", views.queue, name="queue"),
    path("<int:pk>/", views.pick, name="pick"),
    path("<int:pk>/label/", views.labels, name="label"),
    path("labels/", views.labels, name="labels"),
]
