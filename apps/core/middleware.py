from contextvars import ContextVar

_current_user = ContextVar("current_user", default=None)


def get_current_user():
    return _current_user.get()


def set_current_user(user):
    return _current_user.set(user)


class CurrentUserMiddleware:
    """İşlem logunda 'kim yaptı' bilgisini doldurmak için aktif kullanıcıyı saklar."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        token = _current_user.set(user if user and user.is_authenticated else None)
        try:
            return self.get_response(request)
        finally:
            _current_user.reset(token)


def client_ip(request):
    """Gerçek istemci IP'si (Caddy önde olduğu için X-Forwarded-For'un ilk değeri)."""
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = (fwd.split(",")[0].strip() if fwd else "") or request.META.get("REMOTE_ADDR", "")
    return ip or None


class UserActivityMiddleware:
    """Giriş yapmış kullanıcının son görülme / IP / cihaz bilgisini günceller (aynı kullanıcı için en fazla 60 sn'de bir)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False) and not request.path.startswith(("/static/", "/media/")):
            from django.core.cache import cache
            from django.utils import timezone
            key = f"ua-seen:{user.pk}"
            if not cache.get(key):
                cache.set(key, 1, 60)
                from .models import UserActivity
                UserActivity.objects.update_or_create(user=user, defaults={
                    "ip": client_ip(request), "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
                    "path": request.path[:300], "last_seen": timezone.now()})
        return response
