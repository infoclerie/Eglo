# production — Üretim ve fason (§10)

- Reçete (BillOfMaterials + BomLine): mamul, parti büyüklüğü, malzeme miktarı, fire payı %. Yönetim › Reçeteler.
- Üretim emri akışı (`services.py`):
  taslak → `confirm` (malzemeyi FEFO ile AYIRIR; eksik varsa hiçbir şey ayırmaz) → `start` (sarf: `production_consume`;
  fason ise "Fasoncuda") → `finish(üretilen)` (mamul KARANTİNA lokasyonuna LOT + SKT ile girer, `production_in`)
  → `quality_check(onay)` karantinadan rafa / `red` karantinada kalır. `cancel` ayrılanı serbest bırakır.
- Formüller: ihtiyaç = reçete miktarı × (planlanan ÷ parti) × (1 + fire%/100), yukarı yuvarlanır.
  birim maliyet = (sarf edilen malzeme maliyeti + fason işçilik × üretilen) ÷ üretilen. Kayıp % = (planlanan − üretilen) ÷ planlanan.
- Açık emirlerin planlanan miktarı stok ekranında "gelecek" olarak görünür (`inventory.collect_incoming`).
- Olaylar: production.confirmed / started / finished / completed / rejected. `production.completed` pazaryeri stok gönderimini tetikler.
- Hammadde (tür: Hammadde / Ambalaj) satış kanallarına gönderilmez. Hammaddede yakın SKT'li parti kullanılabilir (süresi geçmiş olamaz).
