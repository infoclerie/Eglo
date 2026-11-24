from django.contrib.auth import get_user_model
from django.test import TestCase


class OfficeTests(TestCase):
    def setUp(self):
        self.u = get_user_model().objects.create_superuser("ofis", "o@x.com", "x")

    def test_login_required(self):
        self.assertEqual(self.client.get("/office/").status_code, 302)
        self.assertEqual(self.client.get("/office/api/").status_code, 302)

    def test_page_and_api(self):
        self.client.force_login(self.u)
        r = self.client.get("/office/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "three.module.min.js")
        d = self.client.get("/office/api/").json()
        codes = [x["code"] for x in d["departments"]]
        for c in ("yonetim", "satis", "depo", "kargo", "muhasebe"):
            self.assertIn(c, codes)
        self.assertTrue(all(x["staff"] for x in d["departments"]))

    def test_menu_opens_new_tab(self):
        self.client.force_login(self.u)
        self.assertContains(self.client.get("/"), 'href="/office/" target="_blank"')
