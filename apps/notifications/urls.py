from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_view, name="list"),
    path("api/", views.api, name="api"),
    path("merkez/", views.center, name="center"),
    path("merkez/<int:pk>/", views.edit_rule, name="edit"),
]
