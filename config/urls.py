from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.registry import module_urlpatterns

admin.site.site_header = "Eglo ERP"
admin.site.site_title = "Eglo ERP"
admin.site.index_title = "Yönetim"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.core.urls")),
] + module_urlpatterns()

from django.conf import settings  # noqa: E402

if settings.DEBUG:  # canlıda /media/ dosyalarını Caddy sunar
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
