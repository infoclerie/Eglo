"""
Hepsiburada Merchant API (developers.hepsiburada.com, Kasım 2026).
Kimlik: HTTP Basic (kullanıcı adı = Merchant ID, şifre = Satıcı Paneli › Bilgilerim › Entegrasyon › Entegratör Bilgileri
› "Servis Anahtarı") + zorunlu User-Agent başlığı (entegratör kullanıcı adı). Test ortamı adresleri "-sit" ekli.
- Sipariş (OMS)   : https://oms-external[-sit].hepsiburada.com
    GET  /orders/merchantid/{m}?offset&limit(≤100, zorunlu)&begindate&enddate  → ödemesi tamamlanmış (paketlenecek) kalemler
         yanıt: {items:[{id, orderNumber, orderDate, merchantSKU, sku, barcode, productBarcode, quantity, unitPrice{amount},
                 totalPrice{amount}, vatRate, customerName, shippingAddress{...}, invoice{taxNumber,...}, status}], totalCount}
    POST /packages/merchantid/{m}  {"lineItemRequests":[{"id","quantity"}],"parcelQuantity":1}  → paket oluşturur
    POST /packages/merchantid/{m}/packagenumber/{p}/intransit  {"trackingNumber","trackingUrl","shippedDate"} (kendi kargonuzla)
    POST /packages/merchantid/{m}/packagenumber/{p}/deliver
- Listeleme       : https://listing-external[-sit].hepsiburada.com
    POST /listings/merchantid/{m}/inventory-uploads  [{"hepsiburadaSku"|"merchantSku","price","availableStock"}]
- Finans          : https://mpfinance-external[-sit].hepsiburada.com
    GET  /transactions/merchantid/{m}?Offset&Limit&RecordDateStart&RecordDateEnd
         → {count, items:[{transactionType, amount{value}, isIncome, orderNumber, paymentDate, ...}]}
Fiyatlar KDV DAHİL. NOT: Canlı hesapla ilk kurulumda doğrulanmalıdır (yazılım geliştirilirken hesap yoktu).
"""
import datetime as dt
from decimal import Decimal

import requests
from django.utils import timezone

from . import Field, Provider
from .common import ensure_channel, excl, incl, product_for, save_order, stock_rows

HOSTS = {"oms": "https://oms-external{env}.hepsiburada.com", "listing": "https://listing-external{env}.hepsiburada.com",
         "finance": "https://mpfinance-external{env}.hepsiburada.com"}


class HepsiburadaError(Exception):
    pass


class HepsiburadaClient:
    def __init__(self, merchant_id, password, user_agent, username="", environment="live", session=None, timeout=60):
        self.m = str(merchant_id).strip()
        self.env = "" if environment == "live" else "-sit"
        self.http = session or requests.Session()
        self.auth = ((username or self.m).strip(), password)
        self.headers = {"User-Agent": user_agent.strip() or "eglo_erp", "Content-Type": "application/json",
                        "Accept": "application/json"}
        self.timeout = timeout

    def _req(self, api, method, path, **kw):
        url = HOSTS[api].format(env=self.env) + path.format(m=self.m)
        try:
            r = self.http.request(method, url, auth=self.auth, headers=self.headers, timeout=self.timeout, **kw)
        except requests.RequestException as exc:
            raise HepsiburadaError(f"Hepsiburada'ya bağlanılamadı: {exc}") from exc
        if r.status_code == 401:
            raise HepsiburadaError("Hepsiburada: Merchant ID veya servis anahtarı hatalı (401).")
        if r.status_code == 403:
            raise HepsiburadaError("Hepsiburada: erişim reddedildi (403). User-Agent (entegratör adı) ve yetkileri kontrol edin.")
        if r.status_code == 429:
            raise HepsiburadaError("Hepsiburada: istek limiti aşıldı (429), sonra tekrar denenecek.")
        if r.status_code >= 400:
            raise HepsiburadaError(f"Hepsiburada HTTP {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else {}

    def open_items(self, start, end, offset=0, limit=100):
        fmt = "%Y-%m-%d %H:%M"
        return self._req("oms", "GET", "/orders/merchantid/{m}", params={
            "offset": offset, "limit": limit, "begindate": start.strftime(fmt), "enddate": end.strftime(fmt)})

    def create_package(self, lines, parcels=1):
        return self._req("oms", "POST", "/packages/merchantid/{m}", json={
            "lineItemRequests": [{"id": l["id"], "quantity": l["quantity"]} for l in lines], "parcelQuantity": parcels})

    def in_transit(self, package_number, tracking_number, tracking_url=""):
        return self._req("oms", "POST", f"/packages/merchantid/{{m}}/packagenumber/{package_number}/intransit", json={
            "trackingNumber": tracking_number, "trackingUrl": tracking_url,
            "shippedDate": timezone.localtime().strftime("%Y-%m-%dT%H:%M:%S")})

    def delivered(self, package_number):
        return self._req("oms", "POST", f"/packages/merchantid/{{m}}/packagenumber/{package_number}/deliver", json={})

    def inventory(self, items):
        return self._req("listing", "POST", "/listings/merchantid/{m}/inventory-uploads", json=items)

    def transactions(self, start, end, offset=0, limit=100):
        return self._req("finance", "GET", "/transactions/merchantid/{m}", params={
            "Offset": offset, "Limit": limit, "RecordDateStart": start.isoformat(), "RecordDateEnd": end.isoformat()})


def _amount(v):
    if isinstance(v, dict):
        v = v.get("amount", v.get("value"))
    return Decimal(str(v or 0))


def _package_number(res):
    """Paket oluşturma yanıtından paket numarasını bulur (yanıt şekli farklı olabilir)."""
    if isinstance(res, list):
        res = res[0] if res else {}
    if not isinstance(res, dict):
        return ""
    for k in ("packageNumber", "PackageNumber", "id"):
        if res.get(k):
            return str(res[k])
    for v in res.values():
        if isinstance(v, (dict, list)):
            found = _package_number(v)
            if found:
                return found
    return ""


def classify_hb(tx):
    """Hepsiburada finans kaydı → hakediş kalemi."""
    t = (tx.get("transactionType") or "").lower()
    if "commission" in t:
        return "commission"
    if any(k in t for k in ("cargo", "shipment", "delivery", "shipping")):
        return "shipping"
    if any(k in t for k in ("marketing", "adbalance", "ad", "studio")) and "refund" not in t:
        return "ads"
    if "return" in t or "refund" in t:
        return "returns"
    if tx.get("isIncome") and t in ("sale", "order", "bnplorder", "revenue", "salesrevenue"):
        return "gross_sales"
    if tx.get("isIncome") and "income" not in t and "compensation" not in t:
        return "gross_sales"
    return "service_fees"


class Hepsiburada(Provider):
    code = "hepsiburada"
    name = "Hepsiburada"
    category = "marketplace"
    description = "Siparişleri alır, stok ve fiyatı gönderir, paket/kargo durumunu bildirir, hakedişi (finans kayıtları) çeker."
    color = "#ff6000"
    icon = "cart"
    steps = [("credentials", "Bağlantı bilgileri"), ("test", "Bağlantı testi"), ("settings", "Ayarlar"),
             ("summary", "Özet ve etkinleştir")]
    fields = [
        Field("merchant_id", "Merchant ID", help="Satıcı Paneli › Bilgilerim › Entegrasyon sayfasında yazan mağaza kimliği (GUID)."),
        Field("service_key", "Servis anahtarı", kind="password", secret=True,
              help="Satıcı Paneli › Bilgilerim › Entegrasyon › Entegratör Bilgileri › 'Servis Anahtarı' butonundan kopyalayın."),
        Field("user_agent", "Entegratör kullanıcı adı (User-Agent)",
              help="Hepsiburada'nın entegratör olarak tanımladığı kullanıcı adı. Her istekte gönderilir; yanlışsa 403 alınır."),
        Field("username", "API kullanıcı adı (farklıysa)", required=False,
              help="Boş bırakın: Merchant ID kullanılır. Hepsiburada size ayrı bir API kullanıcı adı verdiyse yazın."),
        Field("environment", "Ortam", kind="choice", default="live",
              choices=[("live", "Canlı (gerçek mağaza)"), ("test", "Test (SIT — Hepsiburada test hesabı)")]),
        Field("import_orders", "Yeni siparişleri otomatik al", step="settings", kind="bool", default=True, required=False),
        Field("auto_confirm", "Gelen siparişte stoğu otomatik ayır (toplamaya düşsün)", step="settings", kind="bool", default=True, required=False),
        Field("order_interval", "Sipariş kontrol aralığı (dakika)", step="settings", kind="int", default=10),
        Field("push_stock", "Stok ve fiyatı Hepsiburada'ya gönder", step="settings", kind="bool", default=False, required=False,
              help="İlk kurulumda kapalı başlatın; ürün eşleştirmelerini kontrol ettikten sonra açın."),
        Field("stock_interval", "Stok/fiyat gönderim aralığı (dakika)", step="settings", kind="int", default=30),
        Field("stock_buffer", "Güvenlik payı (her üründen düşülecek adet)", step="settings", kind="int", default=0, required=False),
        Field("send_status", "Toplamaya başlanınca Hepsiburada'da paket oluştur", step="settings", kind="bool", default=True, required=False),
        Field("own_cargo", "Kendi kargo anlaşmamla gönderiyorum (takip no ve teslim bilgisini ilet)", step="settings", kind="bool",
              default=False, required=False, help="Hepsiburada'nın anlaşmalı kargosu (HepsiJet vb.) kullanılıyorsa kapalı kalsın."),
        Field("pull_settlement", "Hakediş / finans kayıtlarını çek", step="settings", kind="bool", default=True, required=False),
    ]

    @staticmethod
    def client(account=None, config=None, secrets=None, environment=None):
        if account is not None:
            config, secrets, environment = account.config, account.get_secrets(), account.environment
        return HepsiburadaClient(config.get("merchant_id", ""), secrets.get("service_key", ""), config.get("user_agent", ""),
                                 config.get("username", ""), environment or "live")

    def test_connection(self, config, secrets, environment):
        try:
            now = timezone.localtime()
            res = self.client(config=config, secrets=secrets, environment=environment).open_items(now - dt.timedelta(days=7), now, limit=1)
            return True, f"Hepsiburada'ya bağlanıldı. Paketlenmeyi bekleyen kalem: {res.get('totalCount', 0)}."
        except HepsiburadaError as exc:
            return False, str(exc)

    def periodic(self, account):
        c, jobs = account.config, []
        if c.get("import_orders"):
            jobs.append(("hepsiburada.import_orders", "siparişler", {"hours": 72}, c.get("order_interval") or 10))
        if c.get("push_stock"):
            jobs.append(("hepsiburada.push_stock", "stok-fiyat", {}, c.get("stock_interval") or 30))
        if c.get("pull_settlement"):
            jobs.append(("hepsiburada.pull_settlement", "hakediş", {}, 360))
        return jobs

    def handle(self, account, job):
        c = self.client(account)
        k = job.kind
        if k == "hepsiburada.import_orders":
            return self._import_orders(account, c, int(job.payload.get("hours", 72)))
        if k == "hepsiburada.push_stock":
            return self._push_stock(account, c)
        if k == "hepsiburada.pull_settlement":
            return self._pull_settlement(account, c, job.payload)
        from ..models import ExternalOrder
        ext = ExternalOrder.objects.get(pk=job.payload["external_order_id"])
        raw = dict(ext.raw)
        if k == "hepsiburada.create_package":
            if raw.get("package_number"):
                return {"package": raw["package_number"], "already": True}
            res = c.create_package(raw.get("lines", []))
            raw["package_number"] = _package_number(res)
            ext.raw, ext.status = raw, "Packaged"
            ext.save(update_fields=["raw", "status"])
            return {"package": raw["package_number"]}
        if k == "hepsiburada.in_transit":
            if not raw.get("package_number"):
                raise ValueError("Önce Hepsiburada'da paket oluşturulmalı (toplama başlatılınca otomatik oluşur).")
            c.in_transit(raw["package_number"], job.payload.get("tracking_no", ""))
            ext.status = "InTransit"
            ext.save(update_fields=["status"])
            return {"package": raw["package_number"], "tracking": job.payload.get("tracking_no", "")}
        if k == "hepsiburada.delivered":
            c.delivered(raw.get("package_number", ""))
            ext.status = "Delivered"
            ext.save(update_fields=["status"])
            return {"package": raw.get("package_number")}
        raise ValueError(f"Bilinmeyen iş türü: {k}")

    def _import_orders(self, account, c, hours):
        ensure_channel("hepsiburada", "Hepsiburada")
        from ..models import ExternalOrder
        end = timezone.localtime()
        start = end - dt.timedelta(hours=min(hours, 24 * 30))
        lines, offset, total = [], 0, 1
        while offset < total:
            res = c.open_items(start, end, offset=offset)
            items = res.get("items") or []
            total = int(res.get("totalCount") or len(items))
            lines += items
            if not items:
                break
            offset += len(items)
        orders = {}
        for l in lines:
            orders.setdefault(str(l.get("orderNumber")), []).append(l)
        created, skipped, errors, warnings = 0, 0, [], []
        for number, ls in orders.items():
            if ExternalOrder.objects.filter(account=account, external_id=number).exists():
                skipped += 1
                continue
            items = []
            for l in ls:
                p = product_for(account, l.get("sku"), l.get("merchantSKU"), l.get("productBarcode"), l.get("barcode"))
                if p is None:
                    errors.append(f"Sipariş {number}: '{l.get('merchantSKU') or l.get('sku')}' eşleşmedi ({l.get('name', '')})")
                    items = None
                    break
                items.append({"code": p.sku, "quantity": l.get("quantity", 1),
                              "unit_price": excl(_amount(l.get("unitPrice")), l.get("vatRate", p.vat_rate))})
            if not items:
                continue
            first = ls[0]
            addr = first.get("shippingAddress") or {}
            inv = first.get("invoice") or {}
            _, new, warn = save_order(
                account, "hepsiburada", number, items, status=first.get("status", "Open"),
                raw={"lines": [{"id": l.get("id"), "quantity": l.get("quantity", 1)} for l in ls], "orderNumber": number},
                customer_name=addr.get("name") or first.get("customerName", ""), email=addr.get("email", "") or "",
                phone=addr.get("phoneNumber", "") or "",
                tax_number=(inv.get("taxNumber") or inv.get("turkishIdentityNumber") or "")[:11],
                shipping_address=f"{addr.get('address', '')}\n{addr.get('district', '')} / {addr.get('city', '')}".strip(),
                billing_address=(inv.get("address") or {}).get("address", "") if isinstance(inv.get("address"), dict) else str(inv.get("address") or ""),
                note=f"Hepsiburada sipariş no: {number}")
            created += int(new)
            if warn:
                warnings.append(warn)
        if errors:
            raise ValueError(f"{created} sipariş alındı; eşleşmeyen ürünler var: " + " | ".join(errors[:5]))
        return {"new_orders": created, "already_imported": skipped, "not_confirmed": warnings[:10]}

    def _push_stock(self, account, c):
        items = []
        for p, ext_code, qty, price in stock_rows(account, "hepsiburada"):
            row = {"price": float(incl(price, p.vat_rate)), "availableStock": qty}
            row.update({"hepsiburadaSku": ext_code} if ext_code else {"merchantSku": p.sku})
            items.append(row)
        uploads = []
        for i in range(0, len(items), 500):
            res = c.inventory(items[i:i + 500])
            uploads.append(res.get("id", "") if isinstance(res, dict) else "")
        return {"products": len(items), "uploads": uploads}

    def _pull_settlement(self, account, c, payload):
        from apps.accounting.services import upsert_settlement
        today = timezone.localdate()
        out = []
        for start, end in weeks_back(today, int(payload.get("weeks", 2))):
            totals, offset, count = {}, 0, 1
            while offset < count:
                res = c.transactions(start, end, offset=offset)
                items = res.get("items") or []
                count = int(res.get("count") or len(items))
                for tx in items:
                    key = classify_hb(tx)
                    totals[key] = totals.get(key, Decimal("0")) + abs(_amount(tx.get("amount")))
                if not items:
                    break
                offset += len(items)
            s = upsert_settlement("hepsiburada", start, end, source="Hepsiburada finans servisi", **totals)
            out.append(str(s))
        return {"periods": out}


def weeks_back(today, weeks=2):
    """Pazartesi–pazar dönemleri: bu hafta + önceki (weeks-1) hafta."""
    monday = today - dt.timedelta(days=today.weekday())
    return [(monday - dt.timedelta(weeks=i), monday - dt.timedelta(weeks=i) + dt.timedelta(days=6)) for i in range(weeks)]
