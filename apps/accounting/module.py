MANIFEST = {
    "code": "accounting",
    "name": "Finans ve Muhasebe",
    "version": "0.1.0",
    "depends": ["core", "catalog", "inventory", "partners", "sales", "purchase"],
    "urls": "apps.accounting.urls",
    "icon": "chart",
    "color": "#128a52",
    "menu": [
        ("Faturalar", "accounting:invoices", "inbox"),
        ("Cari Bakiyeler", "accounting:balances", "users"),
        ("Tahsilat / Ödeme", "admin:accounting_payment_add", "check"),
        ("Nakit Akışı", "accounting:cashflow", "chart"),
        ("Ürün Kârlılığı", "accounting:profitability", "chart"),
        ("Pazaryeri Hakediş", "admin:accounting_marketplacesettlement_changelist", "cart"),
    ],
    "reset_data": [{'label': 'Faturalar (kesilen + gelen e-faturalar), tahsilatlar, cari hareketler', 'desc': "Satış/iade faturaları, Uyumsoft'tan çekilen gelen e-faturalar, ödemeler, cari hareketler, hakedişler. Uyumsoft'ta 'gelen faturaları otomatik çek' açıksa son 7 günün faturaları yeniden gelir. DİKKAT: GİB'e canlı gönderilmiş fatura varsa seçmeyin.", 'models': ['accounting.LedgerEntry', 'accounting.Payment', 'accounting.InvoiceLine', 'accounting.Invoice', 'accounting.MarketplaceSettlement'], 'sequences': ['invoice.']}],
    "reset_master": [{'label': 'Kasa/banka hesapları ve maliyet profilleri', 'desc': 'Kasa ve banka hesapları, kanal maliyet profilleri, ürün ek maliyetleri.', 'models': ['accounting.ProductCostExtra', 'accounting.ChannelCostProfile', 'accounting.Account']}],
}
