from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:kind>/sablon/", views.template, name="template"),
    path("<slug:kind>/", views.upload, name="upload"),
]
