from django.urls import path

from . import views

urlpatterns = [
    path("", views.summary, name="summary"),
    path("scan/", views.scan, name="scan"),
    path("receive/", views.receive, name="receive"),
    path("transfer/", views.transfer, name="transfer"),
]
