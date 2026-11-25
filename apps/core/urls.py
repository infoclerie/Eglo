from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ayarlar/gorunum/", views.appearance, name="appearance"),
    path("ayarlar/panel-duzeni/", views.save_layout, name="save_layout"),
    path("api/kurlar/", views.rates, name="rates"),
    path("ayarlar/yedekler/", views.backups, name="backups"),
    path("ayarlar/yedekler/ai-rehberi/", views.ai_context, name="ai_context"),
    path("ayarlar/guncellemeler/", views.updates, name="updates"),
    path("ayarlar/guncellemeler/durum/", views.updates_progress, name="updates_progress"),
    path("islem-gecmisi/", views.activity, name="activity"),
    path("ayarlar/aktif-kullanicilar/", views.active_users, name="active_users"),
    path("ayarlar/yedekler/indir/<str:filename>", views.backup_download, name="backup_download"),
]
