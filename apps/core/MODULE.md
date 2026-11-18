# core — Çekirdek

Her zaman açıktır. Diğer bütün modüllerin kullandığı ortak altyapı.

| Parça | Dosya | Kullanım |
|---|---|---|
| Modül kayıt sistemi | `registry.py` | `module.py → MANIFEST`; bağımlılık kontrolü, URL ve menü toplama |
| Olay yolu | `events.py` | `@subscribe("olay")`, `publish("olay", **yük)` |
| İşlem logu | `audit.py`, `AuditLog` | ERP modüllerindeki her kayıt değişikliği otomatik (kim, ne zaman, ne) |
| Onay akışı | `approvals.py`, `ApprovalRequest` | `request_approval(action, obj, title, user)`; onay → `approval.approved.<action>` olayı. Kendi talebini onaylama yasak; `core.decide_approval` izni gerekir. |
| Numara serisi | `Sequence.next(code, prefix)` | SAY-000001 gibi belge numaraları (kilitli, çakışmasız) |
| Ayarlar | `Setting.get/put` | Yöneticinin değiştirebildiği parametreler |
| Temel model | `BaseModel` | created_at, updated_at, created_by |
| Roller | `roles.py` + `setup_roles` komutu | Doküman §12 rolleri |
| Ana panel | `views.dashboard` | Her modülün `dashboard.py → widgets(request)` kartları |
