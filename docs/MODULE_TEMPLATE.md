# Yeni modül şablonu

```
apps/<kod>/
  __init__.py
  module.py      MANIFEST = {"code": "<kod>", "name": "...", "version": "0.1.0", "depends": ["core", ...],
                             "urls": "apps.<kod>.urls", "menu": [("Etiket", "<kod>:url_adı")]}
  apps.py        class XConfig(AppConfig): name = "apps.<kod>"; label = "<kod>"; verbose_name = "..."
                 def ready(self): from . import handlers   # olay dinleyicisi varsa
  models.py      iş modelleri BaseModel'den türer
  services.py    iş kuralları ve formüller (docstring'de formül)
  handlers.py    @subscribe ile olay dinleyicileri
  dashboard.py   def widgets(request): return [{"title","value","url","level"}]   (isteğe bağlı)
  urls.py, views.py, forms.py, admin.py, templates/<kod>/
  tests/         her formül ve kural için test (müşteri dokümanındaki örnek sayılarla)
  MODULE.md      modeller, servisler, formüller, yayınlanan/dinlenen olaylar, ekranlar
```
Sonra: `config/modules.py` listesine ekle → `makemigrations <kod>` → `migrate` → `apps/core/roles.py` izinleri →
`setup_roles` → `ARCHITECTURE.md` olay tablosu ve `docs/ROADMAP.md` güncelle.
