from django.urls import path

from . import views

urlpatterns = [
    path("api/poll/", views.poll, name="poll"),
    path("api/people/", views.people, name="people"),
    path("api/start/", views.start, name="start"),
    path("api/send/", views.send, name="send"),
]
