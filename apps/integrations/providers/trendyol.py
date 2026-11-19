"""
Trendyol Partner API (developers.trendyol.com, Kasım 2026 dokümanı).
- Taban: canlı https://apigw.trendyol.com/integration · test https://stageapigw.trendyol.com/integration (IP yetkisi gerekir)
- Kimlik: Basic (API Key : API Secret) + User-Agent "{SatıcıId} - SelfIntegration" (yoksa 403)
- Siparişler: GET /order/sellers/{id}/v2/orders?status=&startDate=&endDate=(ms)&page=&size=(≤200)  — en fazla son 1 ay
- Paket durumu: PUT /order/sellers/{id}/shipment-packages/{paketId}  {"lines":[{"lineId","quantity"}],"params":{},"status":"Picking"}
- Stok/fiyat: POST /inventory/sellers/{id}/products/price-and-inventory  {"items":[{"barcode","quantity","salePrice","listPrice"}]} (≤1000)
Trendyol fiyatları KDV DAHİL; sistemimizdeki kanal fiyatları KDV hariçtir → satış fiyatı = fiyat × (1 + KDV/100).
"""
import datetime as dt
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.utils import timezone

from . import Field, Provider

BASE = {"live": "https://apigw.trendyol.com/integration", "test": "https://stageapigw.trendyol.com/integration"}
CENT = Decimal("0.01")


class TrendyolError(Exception):
    pass


class TrendyolClient:
    def __init__(self, seller_id, api_key, api_secret, environment="live", session=None, timeout=60):
        self.seller_id, self.base = str(seller_id).strip(), BASE[environment]
        self.http = session or requests.Session()
        self.auth, self.timeout = (api_key, api_secret), timeout
        self.headers = {"User-Agent": f"{self.seller_id} - SelfIntegration", "Content-Type": "application/json"}

    def _req(self, method, path, **kw):
        url = self.base + path.format(seller=self.seller_id)
        try:
            r = self.http.request(method, url, auth=self.auth, headers=self.headers, timeout=self.timeout, **kw)
        except requests.RequestException as exc:
            raise TrendyolError(f"Trendyol'a bağlanılamadı: {exc}") from exc
        if r.status_code == 401:
            raise TrendyolError("Trendyol: API anahtarı veya şifresi hatalı (401).")
        if r.status_code == 403:
            raise TrendyolError("Trendyol: erişim reddedildi (403). Satıcı ID'yi kontrol edin; test ortamı IP yetkisi ister.")
        if r.status_code == 429:
            raise TrendyolError("Trendyol: istek limiti aşıldı (429), sonra tekrar denenecek.")
        if r.status_code >= 400:
            raise TrendyolError(f"Trendyol HTTP {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else {}

    def orders(self, start, end, status="Created", page=0, size=200):
        params = {"startDate": int(start.timestamp() * 1000), "endDate": int(end.timestamp() * 1000), "page": page,
                  "size": size, "orderByField": "PackageLastModifiedDate", "orderByDirection": "ASC"}
        if status:
            params["status"] = status
        return self._req("GET", "/order/sellers/{seller}/v2/orders", params=params)

    def update_package(self, package_id, lines, status, params=None):
        body = {"lines": [{"lineId": l["lineId"], "quantity": l["quantity"]} for l in lines], "params": params or {},
                "status": status}
        return self._req("PUT", "/order/sellers/{seller}/shipment-packages/" + str(package_id), json=body)

    def update_tracking(self, package_id, tracking_number, provider_code):
        return self._req("PUT", "/order/sellers/{seller}/shipment-packages/" + str(package_id) + "/tracking-details",
                         json={"cargoSenderNumber": tracking_number, "providerCode": provider_code})

    def settlements(self, start, end, types, page=0, size=1000):
        """Cari hesap ekstresi: satış, iade, indirim, kupon... (aralık ≤ 15 gün). Taban /integration/finance/che"""
        return self._req("GET", "/finance/che/sellers/{seller}/settlements", params={
            "transactionTypes": ",".join(types), "startDate": int(start.timestamp() * 1000),
            "endDate": int(end.timestamp() * 1000), "page": page, "size": size})

    def other_financials(self, start, end, types, page=0, size=1000):
        """Ödemeler (PaymentOrder), kesinti faturaları (DeductionInvoices) vb."""
        return self._req("GET", "/finance/che/sellers/{seller}/otherfinancials", params={
            "transactionTypes": ",".join(types), "startDate": int(start.timestamp() * 1000),
            "endDate": int(end.timestamp() * 1000), "page": page, "size": size})

    def price_inventory(self, items):
        return self._req("POST", "/inventory/sellers/{seller}/products/price-and-inventory", json={"items": items})


def _excl(price_incl, vat_rate):
    return (Decimal(str(price_incl)) / (1 + Decimal(str(vat_rate or 0)) / 100)).quantize(Decimal("0.0001"))


def _incl(price_excl, vat_rate):
    return (Decimal(str(price_excl)) * (1 + Decimal(str(vat_rate)) / 100)).quantize(CENT, rounding=ROUND_HALF_UP)


class Trendyol(Provider):
    code = "trendyol"
    name = "Trendyol"
    category = "marketplace"
    description = "Siparişleri otomatik alır, stok ve fiyatı gönderir, paket durumunu (toplanıyor / faturalandı) bildirir."
    color = "#f27a1a"
    icon = "cart"
    steps = [("credentials", "Bağlantı bilgileri"), ("test", "Bağlantı testi"), ("settings", "Ayarlar"),
             ("summary", "Özet ve etkinleştir")]
    fields = [
        Field("seller_id", "Satıcı ID (Cari ID)", help="Trendyol Satıcı Paneli › Hesap Bilgilerim › Entegrasyon Bilgileri"),
        Field("api_key", "API Key"),
        Field("api_secret", "API Secret", kind="password", secret=True),
        Field("environment", "Ortam", kind="choice", default="live",
              choices=[("live", "Canlı (gerçek mağaza)"), ("test", "Test (stage — IP yetkisi gerekir)")]),
        Field("import_orders", "Yeni siparişleri otomatik al", step="settings", kind="bool", default=True, required=False),
        Field("auto_confirm", "Gelen siparişte stoğu otomatik ayır (toplamaya düşsün)", step="settings", kind="bool", default=True, required=False),
        Field("order_interval", "Sipariş kontrol aralığı (dakika)", step="settings", kind="int", default=5),
        Field("push_stock", "Stok ve fiyatı Trendyol'a gönder", step="settings", kind="bool", default=True, required=False),
        Field("stock_interval", "Stok/fiyat gönderim aralığı (dakika)", step="settings", kind="int", default=15),
        Field("stock_buffer", "Güvenlik payı (her üründen düşülecek adet)", step="settings", kind="int", default=0, required=False,
              help="Fazla satışı önlemek için Trendyol'da gösterilen stoktan düşülür."),
        Field("send_status", "Toplama ve fatura durumunu Trendyol'a bildir", step="settings", kind="bool", default=True, required=False),
        Field("send_tracking", "Kendi kargo anlaşmamla gönderiyorum (takip numarasını Trendyol'a ilet)", step="settings", kind="bool",
              default=False, required=False, help="Trendyol Express / Trendyol anlaşmalı kargo kullanılıyorsa kapalı kalsın."),
        Field("pull_settlement", "Hakediş / cari hesap ekstresini çek", step="settings", kind="bool", default=True, required=False),
    ]

    @staticmethod
    def client(account=None, config=None, secrets=None, environment=None):
        if account is not None:
            config, secrets, environment = account.config, account.get_secrets(), account.environment
        return TrendyolClient(config.get("seller_id", ""), config.get("api_key", ""), secrets.get("api_secret", ""),
                              environment or "live")

    def test_connection(self, config, secrets, environment):
        try:
            c = self.client(config=config, secrets=secrets, environment=environment)
            now = timezone.now()
            res = c.orders(now - dt.timedelta(days=7), now, status="", size=1)
            return True, f"Trendyol'a bağlanıldı. Son 7 günde {res.get('totalElements', 0)} paket görünüyor."
        except TrendyolError as exc:
            return False, str(exc)

    def periodic(self, account):
        c, jobs = account.config, []
        if c.get("import_orders"):
            jobs.append(("trendyol.import_orders", "siparişler", {"hours": 48}, c.get("order_interval") or 5))
        if c.get("push_stock"):
            jobs.append(("trendyol.push_stock", "stok-fiyat", {}, c.get("stock_interval") or 15))
        if c.get("pull_settlement"):
            jobs.append(("trendyol.pull_settlement", "hakediş", {}, 360))
        return jobs

    # ------------------------------------------------------------ işler
    def handle(self, account, job):
        c = self.client(account)
        if job.kind == "trendyol.import_orders":
            return self._import_orders(account, c, int(job.payload.get("hours", 48)))
        if job.kind == "trendyol.push_stock":
            return self._push_stock(account, c)
        if job.kind == "trendyol.pull_settlement":
            return self._pull_settlement(account, c, job.payload)
        if job.kind == "trendyol.tracking":
            from ..models import ExternalOrder
            ext = ExternalOrder.objects.get(pk=job.payload["external_order_id"])
            c.update_tracking(ext.external_id, job.payload["tracking_no"], job.payload.get("provider_code", ""))
            return {"package": ext.external_id, "tracking": job.payload["tracking_no"]}
        if job.kind == "trendyol.update_status":
            from ..models import ExternalOrder
            ext = ExternalOrder.objects.get(pk=job.payload["external_order_id"])
            lines = [{"lineId": l["lineId"], "quantity": l["quantity"]} for l in ext.raw.get("lines", [])]
            c.update_package(ext.external_id, lines, job.payload["status"], job.payload.get("params") or {})
            ext.status = job.payload["status"]
            ext.save(update_fields=["status"])
            return {"package": ext.external_id, "status": ext.status}
        raise ValueError(f"Bilinmeyen iş türü: {job.kind}")

    def _barcode_map(self, account):
        """pazaryeri barkodu → ürün (eşleştirme tablosu, yoksa ürün barkodu)."""
        from apps.catalog.models import Product
        mapping = {p.barcode: p for p in Product.objects.filter(active=True).exclude(barcode=None).exclude(barcode="")}
        for l in account.listings.select_related("product").exclude(external_barcode=""):
            mapping[l.external_barcode] = l.product
        return mapping

    def _import_orders(self, account, c, hours):
        from apps.sales.services import import_channel_order
        from ..models import ExternalOrder
        end = timezone.now()
        start = end - dt.timedelta(hours=min(hours, 24 * 14))  # v2: en fazla 2 haftalık pencere
        mapping = self._barcode_map(account)
        created, skipped, errors, warnings, page, pages = 0, 0, [], [], 0, 1
        while page < pages:
            res = c.orders(start, end, status="Created", page=page)
            pages = int(res.get("totalPages") or 1)
            for pkg in res.get("content", []):
                pid = str(pkg.get("shipmentPackageId") or pkg.get("id"))
                if ExternalOrder.objects.filter(account=account, external_id=pid).exists():
                    skipped += 1
                    continue
                items = []
                for l in pkg.get("lines", []):
                    product = mapping.get(l.get("barcode"))
                    if product is None:
                        errors.append(f"Paket {pid}: '{l.get('barcode')}' barkodlu ürün eşleşmedi ({l.get('productName', '')})")
                        items = None
                        break
                    unit = l.get("lineUnitPrice", l.get("price"))
                    items.append({"code": product.sku, "quantity": l.get("quantity", 1),
                                  "unit_price": _excl(unit, l.get("vatRate", product.vat_rate)) if unit is not None else None})
                if not items:
                    continue
                addr = pkg.get("shipmentAddress") or {}
                inv = pkg.get("invoiceAddress") or {}
                name = f"{pkg.get('customerFirstName', '')} {pkg.get('customerLastName', '')}".strip()
                order, new = import_channel_order(
                    "trendyol", pid, items, auto_confirm=False,
                    customer_name=inv.get("fullName") or name, email=pkg.get("customerEmail", "") or "",
                    phone=addr.get("phone", "") or "", tax_number=(inv.get("taxNumber") or pkg.get("identityNumber") or "")[:11],
                    shipping_address=f"{addr.get('fullAddress', '')}\n{addr.get('district', '')} / {addr.get('city', '')}".strip(),
                    billing_address=f"{inv.get('fullAddress', '')}\n{inv.get('district', '')} / {inv.get('city', '')}".strip(),
                    note=f"Trendyol sipariş no: {pkg.get('orderNumber', '')} · paket {pid}")
                ExternalOrder.objects.get_or_create(account=account, external_id=pid,
                                                    defaults={"order": order, "status": pkg.get("status", ""), "raw": pkg})
                created += int(new)
                if new and account.config.get("auto_confirm"):
                    from django.core.exceptions import ValidationError
                    from apps.sales.services import confirm
                    try:
                        confirm(order)
                    except ValidationError as exc:  # stok yetersiz: sipariş "Yeni" kalır, havuzda görünür
                        warnings.append(f"{order.number}: {' '.join(exc.messages)}")
            page += 1
        if errors:
            # Eşleşmeyen ürünler: iş başarısız sayılır → ekranda görünür, eşleştirme sonrası "Yeniden dene"
            raise ValueError(f"{created} sipariş alındı; eşleşmeyen ürünler var: " + " | ".join(errors[:5]))
        return {"new_orders": created, "already_imported": skipped, "not_confirmed": warnings[:10]}

    def _push_stock(self, account, c):
        from apps.catalog.models import Product, SalesChannel
        from apps.inventory.services import stock_summary
        channel = SalesChannel.objects.filter(code="trendyol").first()
        buffer = int(account.config.get("stock_buffer") or 0)
        listings = {l.product_id: l for l in account.listings.all()}
        items = []
        for p in Product.objects.filter(active=True).exclude(kind__in=["raw", "packaging"]):
            l = listings.get(p.pk)
            barcode = (l.external_barcode if l and l.external_barcode else p.barcode)
            if not barcode or (l and not l.sync_stock):
                continue
            qty = max(int(stock_summary(p)["available"]) - buffer, 0)
            price = _incl(p.price_for(channel) if channel else p.list_price, p.vat_rate)
            items.append({"barcode": barcode, "quantity": qty, "salePrice": float(price), "listPrice": float(price)})
        batches = []
        for i in range(0, len(items), 1000):
            res = c.price_inventory(items[i:i + 1000])
            batches.append(res.get("batchRequestId", ""))
        return {"products": len(items), "batches": batches}

    def _pull_settlement(self, account, c, payload):
        """Haftalık hakediş: satış/iade/indirim/kupon/kargo + ödeme ve kesinti faturaları → muhasebe hakediş kaydı."""
        from apps.accounting.services import upsert_settlement
        from .hepsiburada import weeks_back
        tz = timezone.get_current_timezone()
        out = []
        for start, end in weeks_back(timezone.localdate(), int(payload.get("weeks", 2))):
            s_dt = dt.datetime.combine(start, dt.time.min, tzinfo=tz)
            e_dt = dt.datetime.combine(end, dt.time.max, tzinfo=tz)
            totals = {k: Decimal("0") for k in ("gross_sales", "commission", "shipping", "campaign_share", "returns",
                                                  "service_fees", "bank_received")}
            for rec in self._pages(c.settlements, s_dt, e_dt, SETTLEMENT_TYPES):
                for key, val in classify_ty(rec):
                    totals[key] += val
            for rec in self._pages(c.other_financials, s_dt, e_dt, ["PaymentOrder", "DeductionInvoices"]):
                amt = Decimal(str(rec.get("debt") or rec.get("credit") or 0))
                if rec.get("transactionType") == "PaymentOrder":
                    totals["bank_received"] += abs(amt)
                else:
                    totals["service_fees"] += abs(amt)
            out.append(str(upsert_settlement("trendyol", start, end, source="Trendyol cari hesap ekstresi", **totals)))
        return {"periods": out}

    @staticmethod
    def _pages(fn, start, end, types):
        page, pages = 0, 1
        while page < pages:
            res = fn(start, end, types, page=page)
            pages = int(res.get("totalPages") or 1)
            yield from res.get("content") or []
            page += 1


SETTLEMENT_TYPES = ["Sale", "Return", "Discount", "DiscountCancel", "Coupon", "CouponCancel", "DeliveryFee",
                    "DeliveryFeeCancel", "ManualRefund", "ManualRefundCancel"]


def classify_ty(rec):
    """Trendyol ekstre satırı → [(hakediş alanı, tutar)]. Komisyon satış/iade satırının commissionAmount alanından gelir."""
    t = rec.get("transactionType")
    debt, credit = Decimal(str(rec.get("debt") or 0)), Decimal(str(rec.get("credit") or 0))
    comm = Decimal(str(rec.get("commissionAmount") or 0))
    if t == "Sale":
        return [("gross_sales", credit), ("commission", comm)]
    if t == "Return":
        return [("returns", debt), ("commission", -comm)]
    if t in ("Discount", "Coupon"):
        return [("campaign_share", debt)]
    if t in ("DiscountCancel", "CouponCancel"):
        return [("campaign_share", -credit)]
    if t == "DeliveryFee":
        return [("shipping", debt)]
    if t == "DeliveryFeeCancel":
        return [("shipping", -credit)]
    if t == "ManualRefund":
        return [("returns", debt)]
    if t == "ManualRefundCancel":
        return [("returns", -credit)]
    return []

