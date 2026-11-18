"""Testlerde ortak kullanılan hazır veri (modüller arası akış testleri için)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from apps.catalog.models import KitComponent, Product, ProductPrice, SalesChannel
from apps.inventory import services as inventory
from apps.inventory.models import Location, Warehouse


class ErpFixture:
    def setup_erp(self):
        self.today = timezone.localdate()
        self.wh = Warehouse.objects.create(code="A", name="Ana depo")
        for code, kind in [("A-KABUL", "receiving"), ("A-SEVK", "shipping"), ("A-IADE", "return_check"),
                           ("A-KAR", "quarantine"), ("A-HASAR", "damaged")]:
            Location.objects.create(code=code, warehouse=self.wh, kind=kind)
        self.r1 = Location.objects.create(code="A-01-01-01", warehouse=self.wh, kind="storage")
        self.r2 = Location.objects.create(code="A-02-01-01", warehouse=self.wh, kind="storage")
        self.web = SalesChannel.objects.create(code="web", name="Web")
        self.ty = SalesChannel.objects.create(code="trendyol", name="Trendyol")
        self.dealer_ch = SalesChannel.objects.create(code="bayi", name="Bayi")
        self.serum = Product.objects.create(sku="SRM", name="Serum", barcode="111", case_barcode="1110",
                                            units_per_case=12, list_price=100, cost=40, weight_kg="0.100",
                                            group="cosmetic")
        self.soap = Product.objects.create(sku="SVS", name="Sabun 3L", barcode="222", list_price=200, cost=70,
                                           weight_kg="3.200", group="liquid_cleaning")
        ProductPrice.objects.create(product=self.serum, channel=self.ty, price=120)
        ProductPrice.objects.create(product=self.serum, channel=self.dealer_ch, price=60)
        self.kit = Product.objects.create(sku="SET3", name="Serum 3'lü", kind="kit", list_price=250)
        KitComponent.objects.create(kit=self.kit, component=self.serum, quantity=3)
        inventory.receive(self.serum, 100, self.r1, lot_no="S1", expiry_date=self.today + timedelta(days=400))
        inventory.receive(self.soap, 50, self.r2, lot_no="V1", expiry_date=self.today + timedelta(days=900))
        self.boss = User.objects.create_superuser("boss", password="x" * 12)
        self.clerk = User.objects.create_user("clerk", password="x" * 12)
