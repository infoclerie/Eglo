"""
ikas e-ticaret (builders.ikas.com, Admin API v2 — Kasım 2026).
- Kimlik: ikas panel › Uygulamalar › Özel uygulama (Private App) → client_id + client_secret (izinler: read/write orders,
  read/write products, read/write inventories).
  Token: POST https://api.myikas.com/api/admin/oauth/token  (form: grant_type=client_credentials, client_id, client_secret)
         → {"access_token", "expires_in": 14400}
- GraphQL: POST https://api.myikas.com/api/v2/admin/graphql  (Authorization: Bearer <token>)
    listOrder(orderedAt:{gte}, pagination:{page,limit}) { data { id orderNumber status orderedAt ... orderLineItems { ... } } hasNext }
    fulfillOrder(input:{orderId, markAsReadyForShipment, sendNotificationToCustomer, trackingInfoDetail{cargoCompany,trackingNumber}})
    listProduct { data { id variants { id sku barcodeList } } }, listStockLocation { id name }
    saveVariantStocks(input:{stockInputs:[{productId, variantId, stockLocationId, stockCount}]})
    updateVariantPrices(input:{variantPriceInputs:[{productId, variantId, price:{sellPrice}}]})
Fiyatlar KDV DAHİL. NOT: Canlı mağaza ile ilk kurulumda doğrulanmalıdır (alan adları dokümandan alındı).
"""
import datetime as dt
from decimal import Decimal

import requests
from django.core.cache import cache
from django.utils import timezone

from . import Field, Provider
from .common import ensure_channel, excl, incl, product_for, save_order, stock_rows

TOKEN_URL = "https://api.myikas.com/api/admin/oauth/token"
GQL_URL = "https://api.myikas.com/api/v2/admin/graphql"

ADDRESS = "firstName lastName company addressLine1 addressLine2 phone taxNumber taxOffice identityNumber city { name } district { name }"
ORDERS_Q = """query ListOrder($orderedAt: DateFilterInput, $pagination: PaginationInput) {
  listOrder(orderedAt: $orderedAt, pagination: $pagination) {
    hasNext page
    data { id orderNumber status orderPaymentStatus orderedAt totalFinalPrice currencyCode note
      customer { email firstName lastName phone }
      shippingAddress { %s } billingAddress { %s }
      orderLineItems { id quantity finalPrice finalUnitPrice taxValue variant { id sku barcodeList name productId } } } } }""" % (ADDRESS, ADDRESS)
PRODUCTS_Q = """query ListProduct($pagination: PaginationInput) {
  listProduct(pagination: $pagination) { hasNext data { id variants { id sku barcodeList } } } }"""
LOCATIONS_Q = "query { listStockLocation { id name } }"
PRODUCTS_FULL_Q = """query ListProduct($pagination: PaginationInput) {
  listProduct(pagination: $pagination) { hasNext data { id name description brand { name } categories { name }
    variants { id sku barcodeList isActive prices { sellPrice discountPrice buyPrice currency } stocks { stockCount stockLocationId }
      images { imageId isMain order } } } } }"""
MERCHANT_Q = "query { getMerchant { id } }"
# v2'de varyant stokları ürün listesinde dolu gelmeyebilir → ayrı sorgu (düz liste döner)
STOCKS_Q = "query { listProductStockLocation { variantId stockCount stockLocationId deleted } }"
STOCK_M = """mutation SaveVariantStocks($input: SaveVariantStocksInput!) {
  saveVariantStocks(input: $input) { errors { errorCode inputArrayIndex } } }"""
PRICE_M = """mutation UpdateVariantPrices($input: UpdateVariantPricesInput!) {
  updateVariantPrices(input: $input) { errors { errorCode inputArrayIndex } } }"""
FULFILL_M = """mutation FulfillOrder($input: PublicFulFillOrderInput!) { fulfillOrder(input: $input) { id status } }"""

SKIP_STATUS = {"CANCELLED", "DRAFT", "REFUNDED", "WAITING_UPSELL_ACTION", "REFUND_REQUESTED"}
CARRIER_NAMES = {"yurtici": "Yurtiçi Kargo", "aras": "Aras Kargo", "mng": "MNG Kargo", "surat": "Sürat Kargo",
                 "ptt": "PTT Kargo", "hepsijet": "HepsiJet", "tex": "Trendyol Express"}


class IkasError(Exception):
    pass


class IkasClient:
    def __init__(self, client_id, client_secret, session=None, timeout=60):
        self.cid, self.secret = client_id.strip(), client_secret
        self.http = session or requests.Session()
        self.timeout = timeout

    def token(self):
        key = f"ikas-token:{self.cid}"
        tok = cache.get(key)
        if tok:
            return tok
        try:
            r = self.http.post(TOKEN_URL, data={"grant_type": "client_credentials", "client_id": self.cid,
                                                "client_secret": self.secret}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise IkasError(f"ikas'a bağlanılamadı: {exc}") from exc
        if r.status_code >= 400:
            raise IkasError("ikas: Client ID veya Client Secret hatalı ya da uygulama kaldırılmış "
                            f"(HTTP {r.status_code}).")
        data = r.json()
        tok = data.get("access_token")
        if not tok:
            raise IkasError("ikas: erişim anahtarı alınamadı.")
        cache.set(key, tok, max(int(data.get("expires_in", 14400)) - 120, 60))
        return tok

    def gql(self, query, variables=None):
        try:
            r = self.http.post(GQL_URL, json={"query": query, "variables": variables or {}}, timeout=self.timeout,
                               headers={"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"})
        except requests.RequestException as exc:
            raise IkasError(f"ikas'a bağlanılamadı: {exc}") from exc
        if r.status_code == 401:
            cache.delete(f"ikas-token:{self.cid}")
            raise IkasError("ikas: yetki hatası (401). Özel uygulamanın izinlerini kontrol edin.")
        if r.status_code == 429:
            raise IkasError("ikas: istek limiti aşıldı (429), sonra tekrar denenecek.")
        if r.status_code >= 400:
            raise IkasError(f"ikas HTTP {r.status_code}: {r.text[:300]}")
        body = r.json()
        if body.get("errors"):
            raise IkasError("ikas: " + "; ".join(e.get("message", str(e)) for e in body["errors"])[:400])
        return body.get("data") or {}

    def orders(self, since, page=1, limit=50):
        return self.gql(ORDERS_Q, {"orderedAt": {"gte": int(since.timestamp() * 1000)},
                                   "pagination": {"page": page, "limit": limit}})["listOrder"]


def _addr(a):
    a = a or {}
    city, district = (a.get("city") or {}).get("name", ""), (a.get("district") or {}).get("name", "")
    return f"{a.get('addressLine1', '')} {a.get('addressLine2') or ''}".strip() + f"\n{district} / {city}".rstrip(" /")


class Ikas(Provider):
    code = "ikas"
    name = "ikas (web mağaza)"
    category = "ecommerce"
    description = "ikas mağazanızın siparişlerini alır, stok ve fiyatı gönderir, kargoya verilince takip numarasını müşteriye iletir."
    color = "#5b4ff5"
    icon = "cart"
    steps = [("credentials", "Bağlantı bilgileri"), ("test", "Bağlantı testi"), ("settings", "Ayarlar"),
             ("summary", "Özet ve etkinleştir")]
    fields = [
        Field("client_id", "Client ID", help="ikas paneli › Uygulamalar › Özel Uygulama Oluştur. Sipariş, ürün ve stok izinlerini verin."),
        Field("client_secret", "Client Secret", kind="password", secret=True, help="Özel uygulama oluşturulurken bir kez gösterilir."),
        Field("channel", "Sistemdeki satış kanalı", kind="choice", default="web",
              choices=[("web", "Web sitesi"), ("ikas", "ikas (ayrı kanal)")],
              help="ikas siparişleri hangi kanalın fiyat ve raporlarına yazılsın?"),
        Field("import_orders", "Yeni siparişleri otomatik al", step="settings", kind="bool", default=True, required=False),
        Field("auto_confirm", "Gelen siparişte stoğu otomatik ayır (toplamaya düşsün)", step="settings", kind="bool", default=True, required=False),
        Field("order_interval", "Sipariş kontrol aralığı (dakika)", step="settings", kind="int", default=5),
        Field("push_stock", "Stok ve fiyatı ikas'a gönder", step="settings", kind="bool", default=False, required=False,
              help="Ürünler ikas'ta SKU veya barkod ile eşleşir. İlk kurulumda kapalı başlatın."),
        Field("push_price", "Fiyatı da gönder (kapalıysa yalnız stok)", step="settings", kind="bool", default=False, required=False),
        Field("stock_interval", "Stok gönderim aralığı (dakika)", step="settings", kind="int", default=15),
        Field("stock_location_id", "ikas stok lokasyonu ID (boşsa ilk lokasyon)", step="settings", required=False),
        Field("stock_buffer", "Güvenlik payı (her üründen düşülecek adet)", step="settings", kind="int", default=0, required=False),
        Field("send_status", "Kargoya verilince ikas'ta 'kargolandı' yap ve müşteriye takip bilgisini gönder", step="settings",
              kind="bool", default=True, required=False),
    ]

    @staticmethod
    def client(account=None, config=None, secrets=None):
        if account is not None:
            config, secrets = account.config, account.get_secrets()
        return IkasClient(config.get("client_id", ""), secrets.get("client_secret", ""))

    def test_connection(self, config, secrets, environment):
        try:
            c = self.client(config=config, secrets=secrets)
            res = c.orders(timezone.now() - dt.timedelta(days=7), limit=1)
            locs = c.gql(LOCATIONS_Q).get("listStockLocation") or []
            return True, (f"ikas'a bağlanıldı. Son 7 günde sipariş var: {'evet' if res.get('data') else 'hayır'}. "
                          f"Stok lokasyonları: {', '.join(l['name'] + ' (' + l['id'] + ')' for l in locs[:5]) or '-'}")
        except IkasError as exc:
            return False, str(exc)

    def periodic(self, account):
        c, jobs = account.config, []
        if c.get("import_orders"):
            jobs.append(("ikas.import_orders", "siparişler", {"hours": 48}, c.get("order_interval") or 5))
        if c.get("push_stock"):
            jobs.append(("ikas.push_stock", "stok-fiyat", {}, c.get("stock_interval") or 15))
        return jobs

    def handle(self, account, job):
        c = self.client(account)
        if job.kind == "ikas.import_orders":
            return self._import_orders(account, c, int(job.payload.get("hours", 48)))
        if job.kind == "ikas.push_stock":
            return self._push_stock(account, c)
        if job.kind == "ikas.import_products":
            return self._import_products(account, c, job.payload)
        if job.kind == "ikas.fulfill":
            from ..models import ExternalOrder
            ext = ExternalOrder.objects.get(pk=job.payload["external_order_id"])
            carrier = job.payload.get("carrier", "")
            c.gql(FULFILL_M, {"input": {
                "orderId": ext.raw.get("id") or ext.external_id, "markAsReadyForShipment": True, "lines": None,
                "sendNotificationToCustomer": True,
                "trackingInfoDetail": {"cargoCompany": CARRIER_NAMES.get(carrier, carrier), "trackingNumber": job.payload.get("tracking_no") or None,
                                       "barcode": job.payload.get("tracking_no") or None, "isSendNotification": True}}})
            ext.status = "FULFILLED"
            ext.save(update_fields=["status"])
            return {"order": ext.external_id, "tracking": job.payload.get("tracking_no", "")}
        raise ValueError(f"Bilinmeyen iş türü: {job.kind}")

    def _import_orders(self, account, c, hours):
        from ..models import ExternalOrder
        ch = account.config.get("channel") or "web"
        ensure_channel(ch, "Web sitesi" if ch == "web" else "ikas")
        since = timezone.now() - dt.timedelta(hours=min(hours, 24 * 30))
        created, skipped, errors, warnings, page = 0, 0, [], [], 1
        while True:
            res = c.orders(since, page=page)
            for o in res.get("data") or []:
                ext_id = str(o.get("orderNumber") or o.get("id"))
                if o.get("status") in SKIP_STATUS:
                    continue
                if ExternalOrder.objects.filter(account=account, external_id=ext_id).exists():
                    skipped += 1
                    continue
                items = []
                for l in o.get("orderLineItems") or []:
                    v = l.get("variant") or {}
                    p = product_for(account, v.get("sku"), *(v.get("barcodeList") or []))
                    if p is None:
                        errors.append(f"Sipariş {ext_id}: '{v.get('sku') or v.get('name')}' eşleşmedi")
                        items = None
                        break
                    qty = Decimal(str(l.get("quantity") or 1))
                    unit = l.get("finalUnitPrice")
                    if unit is None:
                        unit = Decimal(str(l.get("finalPrice") or 0)) / (qty or 1)
                    items.append({"code": p.sku, "quantity": qty, "unit_price": excl(unit, p.vat_rate)})
                if not items:
                    continue
                cust = o.get("customer") or {}
                sh, bill = o.get("shippingAddress") or {}, o.get("billingAddress") or o.get("shippingAddress") or {}
                name = (bill.get("company") or f"{bill.get('firstName', '')} {bill.get('lastName', '')}".strip()
                        or f"{cust.get('firstName', '')} {cust.get('lastName', '')}".strip() or "ikas müşterisi")
                _, new, warn = save_order(
                    account, ch, ext_id, items, status=o.get("status", ""), raw={"id": o.get("id"), "orderNumber": o.get("orderNumber")},
                    customer_name=name, email=cust.get("email") or "", phone=sh.get("phone") or cust.get("phone") or "",
                    tax_number=(bill.get("taxNumber") or bill.get("identityNumber") or "")[:11],
                    shipping_address=_addr(sh), billing_address=_addr(bill),
                    note=f"ikas sipariş no: {o.get('orderNumber')}" + (f" · Not: {o['note']}" if o.get("note") else ""))
                created += int(new)
                if warn:
                    warnings.append(warn)
            if not res.get("hasNext"):
                break
            page += 1
        if errors:
            raise ValueError(f"{created} sipariş alındı; eşleşmeyen ürünler var: " + " | ".join(errors[:5]))
        return {"new_orders": created, "already_imported": skipped, "not_confirmed": warnings[:10]}

    def _variant_map(self, c):
        """ikas SKU/barkod → (productId, variantId)"""
        out, page = {}, 1
        while True:
            res = c.gql(PRODUCTS_Q, {"pagination": {"page": page, "limit": 100}})["listProduct"]
            for p in res.get("data") or []:
                for v in p.get("variants") or []:
                    for code in [v.get("sku")] + list(v.get("barcodeList") or []):
                        if code:
                            out[str(code)] = (p["id"], v["id"])
            if not res.get("hasNext"):
                return out
            page += 1

    def _push_stock(self, account, c):
        loc = account.config.get("stock_location_id")
        if not loc:
            locs = c.gql(LOCATIONS_Q).get("listStockLocation") or []
            if not locs:
                raise ValueError("ikas'ta stok lokasyonu bulunamadı.")
            loc = locs[0]["id"]
        vmap = self._variant_map(c)
        stocks, prices, missing = [], [], 0
        ch = account.config.get("channel") or "web"
        for p, ext_code, qty, price in stock_rows(account, ch):
            ids = vmap.get(ext_code or "") or vmap.get(p.sku) or vmap.get(p.barcode or "")
            if not ids:
                missing += 1
                continue
            stocks.append({"productId": ids[0], "variantId": ids[1], "stockLocationId": loc, "stockCount": qty})
            prices.append({"productId": ids[0], "variantId": ids[1], "price": {"sellPrice": float(incl(price, p.vat_rate))}})
        errors = []
        for i in range(0, len(stocks), 200):
            res = c.gql(STOCK_M, {"input": {"stockInputs": stocks[i:i + 200]}})
            errors += (res.get("saveVariantStocks") or {}).get("errors") or []
            if account.config.get("push_price"):
                res = c.gql(PRICE_M, {"input": {"variantPriceInputs": prices[i:i + 200]}})
                errors += (res.get("updateVariantPrices") or {}).get("errors") or []
        return {"products": len(stocks), "not_in_ikas": missing, "errors": errors[:10]}

    def _import_products(self, account, c, payload):
        """ikas ürünleri (her varyant ayrı kart) + görseller + isteğe bağlı açılış stoğu. Fiyatlar KDV dahil."""
        from .common import import_options, new_stats, upsert_product
        ch_code = account.config.get("channel") or "web"
        channel = ensure_channel(ch_code, "Web sitesi" if ch_code == "web" else "ikas")
        opts = import_options(account, payload)
        loc_filter = account.config.get("stock_location_id") or None
        merchant = ""
        if opts["import_images"]:
            try:
                merchant = (c.gql(MERCHANT_Q).get("getMerchant") or {}).get("id", "")
            except IkasError:
                merchant = ""
        stock_map = {}
        if opts["location"] is not None:
            for row in c.gql(STOCKS_Q).get("listProductStockLocation") or []:
                if row.get("deleted") or (loc_filter and row.get("stockLocationId") != loc_filter):
                    continue
                stock_map[row.get("variantId")] = stock_map.get(row.get("variantId"), Decimal(0)) + Decimal(str(row.get("stockCount") or 0))
        stats, page = new_stats(), 1
        while True:
            res = c.gql(PRODUCTS_FULL_Q, {"pagination": {"page": page, "limit": 50}})["listProduct"]
            for prod in res.get("data") or []:
                variants = [v for v in (prod.get("variants") or []) if not v.get("deleted")]
                for n, v in enumerate(variants, start=1):
                    barcodes = [b for b in (v.get("barcodeList") or []) if b]
                    price = (v.get("prices") or [{}])[0] or {}
                    name = prod.get("name") or v.get("sku") or ""
                    if len(variants) > 1:
                        name = f"{name} ({v.get('sku') or n})"
                    imgs = sorted(v.get("images") or [], key=lambda im: (not im.get("isMain"), im.get("order") or 0))
                    try:
                        upsert_product(account, channel, {
                            "sku": v.get("sku") or (barcodes[0] if barcodes else f"IKAS-{v['id'][:8]}"),
                            "barcode": barcodes[0] if barcodes else "", "external": v.get("sku") or (barcodes[0] if barcodes else ""),
                            "name": name, "description": prod.get("description"), "brand": ((prod.get("brand") or {}).get("name") or "").strip(),
                            "category": (((prod.get("categories") or [{}])[0] or {}).get("name") or "").strip(),
                            "list_incl": price.get("sellPrice"), "sale_incl": price.get("discountPrice"), "cost": price.get("buyPrice"),
                            "active": v.get("isActive", True),
                            "stock": stock_map.get(v["id"]) if v["id"] in stock_map else sum(
                                Decimal(str(x.get("stockCount") or 0)) for x in (v.get("stocks") or [])
                                if not loc_filter or x.get("stockLocationId") == loc_filter),
                            "images": [ikas_image_url(merchant, im["imageId"]) for im in imgs if im.get("imageId") and merchant],
                        }, opts, stats)
                    except Exception as exc:  # noqa: BLE001
                        stats["problems"].append(f"{v.get('sku')}: {exc}")
            if not res.get("hasNext"):
                break
            page += 1
        stats["problems"] = stats["problems"][:20]
        return stats


def ikas_image_url(merchant_id, image_id, size=1080):
    """ikas CDN görsel adresi (ikas'ın yaygın kullanılan adres kalıbı; dokümanda yok — canlı mağazada doğrulanmalı)."""
    return f"https://cdn.myikas.com/images/{merchant_id}/{image_id}/image_{size}.webp"
