from django.urls import path

from . import views

urlpatterns = [
    path("", views.board, name="board"),
    path("move/", views.move, name="move"),
    path("takipler/", views.activities, name="activities"),
    path("segmentler/", views.segments, name="segments"),
    path("kampanyalar/", views.campaigns, name="campaigns"),
    path("kampanyalar/yeni/", views.campaign_edit, name="campaign_new"),
    path("kampanyalar/<int:pk>/", views.campaign_detail, name="campaign"),
    path("kampanyalar/<int:pk>/duzenle/", views.campaign_edit, name="campaign_edit"),
    path("abonelik/<str:token>/", views.unsubscribe, name="unsubscribe"),
]
