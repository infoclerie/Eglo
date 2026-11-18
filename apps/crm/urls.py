from django.urls import path

from . import views

urlpatterns = [
    path("", views.board, name="board"),
    path("move/", views.move, name="move"),
    path("takipler/", views.activities, name="activities"),
    path("segmentler/", views.segments, name="segments"),
]
