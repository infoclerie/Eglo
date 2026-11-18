from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from apps.core.events import publish, subscribe
from apps.core.models import Sequence
from apps.core.registry import check_dependencies, load_manifests


class CoreTests(TestCase):
    def test_manifests_and_dependencies(self):
        m = check_dependencies()
        self.assertIn("inventory", m)

    @override_settings(ERP_MODULES=["core", "inventory"])
    def test_missing_dependency_detected(self):
        with self.assertRaises(ImproperlyConfigured):
            check_dependencies(load_manifests())

    def test_event_bus(self):
        seen = []

        @subscribe("test.event")
        def h(value, **kw):
            seen.append(value)
            return value * 2

        self.assertEqual(publish("test.event", value=3), [6])
        self.assertEqual(seen, [3])

    def test_sequence(self):
        self.assertEqual(Sequence.next("t", "T-"), "T-000001")
        self.assertEqual(Sequence.next("t", "T-"), "T-000002")
