# partners — Cari Kartlar

Bağımlılık: core, catalog. Müşteri dokümanı §5.1, §8.1, §8.2.

Tek model `Partner`: müşteri, bayi, tedarikçi, fason üretici (tür + grup). Kod otomatik (C-000001 müşteri, T-000001 tedarikçi).
Müşteriye özel indirim, fiyat kanalı (bayi/kurumsal fiyat listesi), vade, kredi limiti, İYS/KVKK izinleri.

Servisler: `open_balance(partner)` — `partners.collect_balance` olayından (muhasebe modülü doldurur);
`credit_check(partner, amount)` — limit 0 ise kontrol yok.
