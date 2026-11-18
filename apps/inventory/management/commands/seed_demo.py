"""Örnek veri: dokümandaki depo yapısı, satış kanalları ve birkaç ürün. Tekrar çalıştırılabilir."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Brand, Category, KitComponent, Product, ProductPrice, SalesChannel
from apps.inventory import services
from apps.inventory.models import Location, Quant, Warehouse

AREAS = [  # (kod, ad, tür)
    ("A-KABUL", "Mal kabul alanı", "receiving"), ("A-SEVK", "Sevkiyat alanı", "shipping"),
    ("A-IADE", "İade alanı", "return_check"), ("A-KARANTINA", "Karantina alanı", "quarantine"),
    ("A-HASAR", "Hasarlı ürün alanı", "damaged"), ("A-NUMUNE", "Numune alanı", "sample"),
]
CHANNELS = [("trendyol", "Trendyol"), ("hepsiburada", "Hepsiburada"), ("amazon", "Amazon"), ("web", "Web sitesi"),
            ("bayi", "B2B Bayi"), ("eczane", "Eczane"), ("kurumsal", "Kurumsal"), ("telefon", "Telefon / manuel")]


class Command(BaseCommand):
    help = "Demo depo, lokasyon, kanal ve ürün verisi oluşturur."

    @transaction.atomic
    def handle(self, *args, **opts):
        wh, _ = Warehouse.objects.get_or_create(code="A", defaults={"name": "Ana depo"})
        for code, name, kind in AREAS:
            Location.objects.get_or_create(code=code, defaults={"warehouse": wh, "name": name, "kind": kind})
        for aisle in ("01", "02"):
            for rack in ("01", "02", "03"):
                for level in ("01", "02"):
                    Location.objects.get_or_create(code=f"A-{aisle}-{rack}-{level}", defaults={
                        "warehouse": wh, "kind": "storage", "aisle": aisle, "rack": rack, "level": level})
        for code, name in CHANNELS:
            SalesChannel.objects.get_or_create(code=code, defaults={"name": name})

        brand, _ = Brand.objects.get_or_create(name="Clerie")
        cos, _ = Category.objects.get_or_create(name="Kozmetik", parent=None)
        cln, _ = Category.objects.get_or_create(name="Temizlik", parent=None)
        serum, _ = Product.objects.get_or_create(sku="CLR-SRM-30", defaults=dict(
            name="Clerie Yüz Serumu 30 ml", barcode="8680000000011", brand=brand, category=cos, group="cosmetic",
            volume="30 ml", units_per_case=24, cost=95, list_price=250, min_stock=100, safety_stock=50,
            lead_time_days=20, shelf_life_days=730))
        soap, _ = Product.objects.get_or_create(sku="CLR-SVS-3L", defaults=dict(
            name="Clerie Sıvı Sabun 3 L", barcode="8680000000028", brand=brand, category=cln, group="liquid_cleaning",
            volume="3 L", weight_kg=3.2, units_per_case=4, cases_per_pallet=60, cost=70, list_price=160,
            min_stock=200, safety_stock=100, lead_time_days=15, shelf_life_days=1095))
        kit, _ = Product.objects.get_or_create(sku="CLR-SET-3", defaults=dict(
            name="Clerie Serum 3'lü Set", kind="kit", group="set", brand=brand, category=cos, list_price=650))
        KitComponent.objects.get_or_create(kit=kit, component=serum, defaults={"quantity": 3})
        for ch, price in (("trendyol", 329), ("hepsiburada", 319), ("web", 299), ("bayi", 190), ("kurumsal", 210)):
            ProductPrice.objects.get_or_create(product=serum, channel=SalesChannel.objects.get(code=ch), defaults={"price": price})

        if not Quant.objects.exists():
            today = timezone.localdate()
            services.receive(serum, 300, Location.objects.get(code="A-01-01-01"), lot_no="SRM2601",
                             expiry_date=today + timedelta(days=100), reference="DEMO")
            services.receive(serum, 500, Location.objects.get(code="A-01-02-01"), lot_no="SRM2605",
                             expiry_date=today + timedelta(days=500), reference="DEMO")
            services.receive(soap, 150, Location.objects.get(code="A-02-01-01"), lot_no="SVS2603",
                             expiry_date=today + timedelta(days=900), reference="DEMO")
        self.stdout.write(self.style.SUCCESS("Demo veri hazır."))
