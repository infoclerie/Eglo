"""
Asistan: kullanıcının sorusunu yapay zekâya iletir; yapay zekâ gerekli veriyi tools.py'deki salt okunur sorgularla ister,
sonuçlara bakarak Türkçe cevap yazar. En fazla MAX_STEPS sorgu turu. Konuşma bağlamı için son HISTORY mesaj gönderilir.
"""
import json

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.models import Setting

from . import tools as T
from .models import AssistantMessage

MAX_STEPS = 6
HISTORY = 8


def account():
    from apps.integrations.services import active_account
    return active_account("ai")


def system_prompt(user):
    company = (Setting.get("accounting.company", {}) or {}).get("title") or "Eglo Kozmetik"
    today = timezone.localdate()
    return (
        f"Sen {company} şirketinin ERP asistanısın (deterjan/kozmetik üreticisi, marka Clerie). Bugün {today:%d.%m.%Y} "
        f"({['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar'][today.weekday()]}). "
        f"Soran kişi: {user.get_full_name() or user.get_username()}.\n"
        "Kurallar:\n"
        "- Rakamları YALNIZCA araçlardan (veri sorgularından) gelen sonuçlara dayandır. Tahmin etme, uydurma. Veri yoksa açıkça söyle.\n"
        "- Gerekirse birden fazla aracı çağır (ör. kıyas için iki dönem). Tarihleri YYYY-AA-GG gönder; 'bu ay', 'geçen hafta' gibi ifadeleri bugüne göre hesapla.\n"
        "- Bir araç 'yetki yok' derse kullanıcıya bu bilgiye yetkisinin olmadığını söyle.\n"
        "- Kısa ve net Türkçe cevap ver: önce sonuç, sonra gerekiyorsa kısa madde listesi veya küçük tablo (Markdown). "
        "Para birimi TL, binlik ayırıcı nokta, ondalık virgül (ör. 12.450,75 TL). KDV hariç/dahil olduğunu belirt.\n"
        "- Kayıt değiştiremezsin; sipariş, stok, fatura işlemi istenirse ilgili ekranı tarif et.\n"
        "- Müşteri telefon/e-posta/adres bilgisine erişimin yok; isteyene ilgili ekranı söyle.\n"
        "- Konu dışı sorularda kibarca işletme verilerine yardımcı olabileceğini söyle."
    )


def used_today(user):
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return AssistantMessage.objects.filter(user=user, role="user", created_at__gte=start).count()


def ask(user, question, client=None):
    """Döner: AssistantMessage (cevap). Hata durumunda ValidationError."""
    question = (question or "").strip()
    if not question:
        raise ValidationError("Bir soru yazın.")
    if len(question) > 2000:
        raise ValidationError("Soru en fazla 2000 karakter olabilir.")
    acc = account()
    if acc is None:
        raise ValidationError("Yapay zekâ bağlantısı kurulmamış. Yönetici: Entegrasyonlar › Yeni bağlantı › Yapay zekâ asistanı.")
    if not acc.config.get("kvkk_ok"):
        raise ValidationError("Yapay zekâ bağlantısının ayarlarında veri aktarımı onayı işaretli değil.")
    limit = int(acc.config.get("daily_limit") or 50)
    if used_today(user) >= limit:
        raise ValidationError(f"Bugünkü soru sınırınız ({limit}) doldu. Yarın tekrar deneyin veya yöneticiden sınırı artırmasını isteyin.")
    provider = acc.provider_obj
    client = client or provider.client(acc)
    past = list(AssistantMessage.objects.filter(user=user).order_by("-created_at")[:HISTORY])[::-1]
    msgs = [{"role": m.role, "content": m.content} for m in past] + [{"role": "user", "content": question}]
    while msgs and msgs[0]["role"] != "user":  # sağlayıcılar kullanıcı mesajıyla başlamayı ister
        msgs.pop(0)
    AssistantMessage.objects.create(user=user, role="user", content=question, provider=acc.provider)
    tool_defs = [{"name": t["name"], "description": t["description"], "schema": t["schema"]} for t in T.tools_for(user)]
    client.start(msgs)
    used, tin, tout, text = [], 0, 0, ""
    from apps.integrations.providers.ai import AIError
    try:
        for _ in range(MAX_STEPS):
            res = client.chat(system_prompt(user), tool_defs)
            tin += res.usage.get("input", 0)
            tout += res.usage.get("output", 0)
            text = res.text or text
            if not res.tool_calls:
                break
            results = []
            for call in res.tool_calls:
                out = T.run_tool(user, call["name"], call["input"])
                used.append({"tool": T.LABELS.get(call["name"], call["name"]), "name": call["name"], "input": call["input"]})
                results.append({"id": call["id"], "content": json.dumps(out, ensure_ascii=False, default=str)[:15000]})
            client.add_tool_results(results)
        else:
            text = text or "Soru çok fazla veri sorgusu gerektirdi; lütfen daha dar bir soru sorun."
    except AIError as exc:
        raise ValidationError(str(exc))
    return AssistantMessage.objects.create(user=user, role="assistant", content=text or "Cevap üretilemedi.", tools_used=used,
                                           tokens_in=tin, tokens_out=tout, provider=acc.provider)


SUGGESTIONS = [
    ("sales.view_salesorder", "Bu ayın kanal bazında cirosu ne, geçen ayla kıyasla?"),
    ("sales.view_salesorder", "Son 30 günde en çok satan 10 ürün hangisi?"),
    ("inventory.view_quant", "Stoğu minimumun altına düşen ürünler ve ne kadar sipariş vermeliyim?"),
    ("inventory.view_quant", "Önümüzdeki 90 günde SKT'si dolacak ürünler hangileri?"),
    ("accounting.view_invoice", "Vadesi geçmiş alacaklarımız kimlerde?"),
    ("reports.view_report", "Hangi ürünler durgun, stokta bekliyor?"),
]


def suggestions(user):
    return [q for perm, q in SUGGESTIONS if user.has_perm(perm)][:4]
