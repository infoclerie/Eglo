from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ayarlar/gorunum/", views.appearance, name="appearance"),
    path("ayarlar/panel-duzeni/", views.save_layout, name="save_layout"),
    path("api/kurlar/", views.rates, name="rates"),
    path("ayarlar/yedekler/", views.backups, name="backups"),
    path("ayarlar/yedekler/indir/<str:filename>", views.backup_download, name="backup_download"),
]
