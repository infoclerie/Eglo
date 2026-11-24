> 🤖 **Yapay zekâ ile çalışacaksanız:** önce [`PROJE_REHBERI_AI.md`](PROJE_REHBERI_AI.md) dosyasını okutun — projenin tamamı tek dosyada.

# Eglo ERP — Depo, Stok, Sipariş, Sevkiyat, CRM ve Muhasebe

Deterjan ve kozmetik firması için web tabanlı, modüler, entegre işletme yönetim sistemi.

- **Başlarken (insan veya yapay zekâ):** `AGENTS.md`
- **Mimari:** `ARCHITECTURE.md` · **Yol haritası:** `docs/ROADMAP.md` · **Kararlar:** `docs/DECISIONS.md`
- **Kurulum:** `docs/DEPLOY.md` · **Müşteri ihtiyaçları:** `docs/requirements/musteri-ihtiyac-dokumani.md`

Hızlı başlangıç (yerel):
```bash
pip install -r requirements.txt
python manage.py migrate && python manage.py setup_roles && python manage.py seed_demo
python manage.py createsuperuser && python manage.py runserver   # http://127.0.0.1:8000
python manage.py test
```
