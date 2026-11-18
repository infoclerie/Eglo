from django.urls import path

from . import views

urlpatterns = [
    path("", views.queue, name="queue"),
    path("<int:pk>/", views.pick, name="pick"),
]
