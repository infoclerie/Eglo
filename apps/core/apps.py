from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    verbose_name = "Çekirdek"

    def ready(self):
        from . import audit
        from .registry import check_dependencies
        check_dependencies()
        audit.connect()
        from django.contrib.auth.signals import user_logged_in

        def on_login(sender, request, user, **kw):
            from django.utils import timezone

            from .middleware import client_ip
            from .models import UserActivity
            ip = client_ip(request)
            UserActivity.objects.update_or_create(user=user, defaults={
                "ip": ip, "login_ip": ip, "login_at": timezone.now(), "last_seen": timezone.now(),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300], "path": request.path[:300]})
        user_logged_in.connect(on_login, dispatch_uid="erp_user_activity_login")
