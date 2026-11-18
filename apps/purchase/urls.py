from django.urls import path

from . import views

urlpatterns = [path("<int:pk>/receive/", views.receive, name="receive")]
