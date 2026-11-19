from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("new/", views.choose, name="choose"),
    path("new/<str:provider>/<str:step>/", views.wizard, name="wizard"),
    path("<int:pk>/", views.account_detail, name="account"),
    path("<int:pk>/listings/", views.listings, name="listings"),
    path("jobs/", views.jobs, name="jobs"),
    path("kanal/<int:pk>/", views.channel, name="channel"),
]
