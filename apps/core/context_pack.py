"""
"Yapay zekâ için proje rehberi": projenin tüm dokümanlarını + canlı sistem özetini TEK bir Markdown dosyasında toplar.
Bu dosya her yedeğe (PROJE_REHBERI_AI.md) eklenir ve Yedekler ekranından indirilebilir. Hangi yapay zekâya verilirse
verilsin (Claude, ChatGPT, Gemini...) projeyi, kuralları, modülleri ve kaldığımız yeri anlayabilsin diye.
Şifre, API anahtarı, müşteri bilgisi İÇERMEZ.
"""
from pathlib import Path

from django.conf import settings
from django.utils import timezone

DOC_ORDER = ["AGENTS.md", "docs/HANDOFF.md", "ARCHITECTURE.md", "docs/ROADMAP.md", "docs/DECISIONS.md", "docs/DEPLOY.md",
             "docs/MODULE_TEMPLATE.md"]

INTRO = """# EGLO ERP — Yapay zekâ için proje rehberi

> **Bu dosyayı okuyan yapay zekâya:** Bu, Eglo Kozmetik için yazılmış web tabanlı, modüler bir ERP + depo (WMS) + CRM +
> muhasebe sisteminin TAM tanımıdır. Kaynak kod: https://github.com/infoclerie/Eglo (main dalı).
> Önce "Bölüm 1 · Kurallar" ve "Bölüm 2 · Devir notları"nı okuyun; kod değiştirmeden önce ilgili modülün MODULE.md
> bölümüne bakın. Kullanıcı Türkçe konuşur, teknik olmayan bir işletme sahibidir: cevaplarınız Türkçe, sade ve adım adım olsun.
> Güncelleme: değişiklikleri GitHub main dalına gönderin; kullanıcı Ayarlar › Güncellemeler › «GitHub'dan güncelle» ile uygular
> (SSH gerekmez). GitHub'a erişiminiz yoksa `files/` + `meta.json` içeren zip paketi üretin (bkz. deploy/build-update.sh).
> Şifre / API anahtarı ASLA sohbette istenmez; kullanıcı bunları sistemdeki sihirbazlara kendisi girer.

Oluşturulma: {stamp} · Dosya sistem tarafından otomatik üretildi (Sistem › Yedekler › "Yapay zekâ rehberini indir").
"""


def _read(rel):
    p = Path(settings.BASE_DIR) / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def live_summary():
    """Canlı sistemin gizli bilgi içermeyen özeti: açık modüller, kayıt sayıları, kurulu bağlantı türleri."""
    from django.apps import apps

    from apps.core.registry import load_manifests
    lines = ["## Bölüm 0 · Bu sunucunun şu anki durumu", ""]
    mans = load_manifests()
    lines.append("**Açık modüller:** " + ", ".join(f"{m['name']} (`{c}`)" for c, m in mans.items()))
    counts = []
    for label, name in [("catalog.Product", "ürün"), ("partners.Partner", "cari"), ("sales.SalesOrder", "sipariş"),
                        ("accounting.Invoice", "fatura"), ("inventory.StockMove", "stok hareketi"),
                        ("production.ProductionOrder", "üretim emri"), ("auth.User", "kullanıcı")]:
        try:
            counts.append(f"{apps.get_model(label).objects.count()} {name}")
        except (LookupError, Exception):  # noqa: BLE001
            pass
    lines.append("**Kayıt sayıları:** " + ", ".join(counts))
    try:
        from apps.integrations.models import IntegrationAccount
        acc = [f"{a.name} ({a.provider}, {'aktif' if a.active else 'kapalı'}, {a.environment})" for a in IntegrationAccount.objects.all()]
        lines.append("**Kurulu entegrasyonlar:** " + (", ".join(acc) or "yok") + " — şifreler bu dosyada yoktur.")
    except Exception:  # noqa: BLE001
        pass
    import subprocess
    try:
        rev = subprocess.run(["git", "log", "-1", "--format=%h %cd %s", "--date=short"], cwd=settings.BASE_DIR,
                             capture_output=True, text=True, timeout=5).stdout.strip()
        if rev:
            lines.append(f"**Yazılım sürümü (git):** {rev}")
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(lines) + "\n"


def build_pack(include_live=True):
    parts = [INTRO.format(stamp=timezone.localtime().strftime("%d.%m.%Y %H:%M"))]
    if include_live:
        parts.append(live_summary())
    changes = _read("updates/changelog.md")
    if changes:
        parts.append("\n---\n\n## Son değişiklikler (sunucudaki son 40 commit, yeniden eskiye)\n\n" + changes.strip() + "\n")
    titles = {"AGENTS.md": "Bölüm 1 · Kurallar (AGENTS.md)", "docs/HANDOFF.md": "Bölüm 2 · Devir notları ve kaldığımız yer (HANDOFF.md)"}
    for n, rel in enumerate(DOC_ORDER, start=1):
        text = _read(rel)
        if text:
            parts.append(f"\n---\n\n## {titles.get(rel, f'Bölüm {n} · {rel}')}\n\n<!-- kaynak: {rel} -->\n\n{text.strip()}\n")
    mods = sorted((Path(settings.BASE_DIR) / "apps").glob("*/MODULE.md"))
    parts.append("\n---\n\n## Bölüm 9 · Modüller (her modülün MODULE.md dosyası)\n")
    for m in mods:
        parts.append(f"\n### Modül `{m.parent.name}`\n\n{m.read_text(encoding='utf-8').strip()}\n")
    req = _read("docs/requirements/musteri-ihtiyac-dokumani.md")
    if req:
        parts.append(f"\n---\n\n## Bölüm 10 · Müşterinin ilk ihtiyaç dokümanı\n\n{req.strip()}\n")
    return "".join(parts)
