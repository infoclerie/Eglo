from django.contrib.auth.models import User
from django.test import TestCase

from apps.core.models import UserActivity


class ActiveUsersTests(TestCase):
    def test_ip_and_list(self):
        boss = User.objects.create_superuser("boss", password="x" * 12)
        u = User.objects.create_user("satis", password="x" * 12)
        self.client.post("/login/", {"username": "satis", "password": "x" * 12}, HTTP_X_FORWARDED_FOR="85.105.1.2, 10.0.0.1",
                         HTTP_USER_AGENT="Mozilla/5.0 (iPhone) Safari/605")
        a = UserActivity.objects.get(user=u)
        self.assertEqual((a.ip, a.login_ip), ("85.105.1.2", "85.105.1.2"))
        self.assertEqual(self.client.get("/ayarlar/aktif-kullanicilar/").status_code, 302)  # yönetici değil
        from django.core.cache import cache
        cache.clear()
        self.client.force_login(boss)
        r = self.client.get("/ayarlar/aktif-kullanicilar/", REMOTE_ADDR="1.2.3.4")
        self.assertContains(r, "85.105.1.2")
        self.assertContains(r, "Safari · iPhone")
        self.assertContains(r, "Çevrimiçi")
        self.assertEqual(UserActivity.objects.get(user=boss).ip, "1.2.3.4")
