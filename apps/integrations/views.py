"""Entegrasyon ekranları ve kurulum sihirbazı (adım adım: bilgiler → şirket → test → ayarlar → etkinleştir)."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import services
from .models import IntegrationAccount, IntegrationJob
from .providers import CATEGORY_LABELS, all_providers, get_provider

PERM = "integrations.change_integrationaccount"


def _form_class(provider, step, secrets_known=False):
    fields = {}
    for f in provider.fields_for(step):
        common = {"label": f.label, "help_text": f.help, "required": f.required and not (f.secret and secrets_known)}
        if f.kind == "password":
            fields[f.name] = forms.CharField(widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
                                             **{**common, "help_text": (f.help + " — boş bırakılırsa kayıtlı şifre korunur.")
                                                if secrets_known else f.help})
        elif f.kind == "choice":
            fields[f.name] = forms.ChoiceField(choices=f.choices, **common)
        elif f.kind == "bool":
            fields[f.name] = forms.BooleanField(**{**common, "required": False})
        elif f.kind == "int":
            fields[f.name] = forms.IntegerField(min_value=1, **common)
        elif f.kind == "email":
            fields[f.name] = forms.EmailField(**common)
        else:
            fields[f.name] = forms.CharField(max_length=200, **common)
    form = type("WizardForm", (forms.Form,), fields)

    def clean(self):
        data = super(form, self).clean()
        for key in ("series_efatura", "series_earsiv"):
            v = (data.get(key) or "").upper()
            if key in data and (len(v) != 3 or not v.isalpha()):
                self.add_error(key, "Tam 3 harf olmalı (ör. EGL).")
            elif key in data:
                data[key] = v
        if data.get("series_efatura") and data.get("series_efatura") == data.get("series_earsiv"):
            self.add_error("series_earsiv", "e-Arşiv serisi e-Fatura serisinden farklı olmalı.")
        vkn = data.get("vkn")
        if vkn is not None and (not vkn.isdigit() or len(vkn) not in (10, 11)):
            self.add_error("vkn", "VKN 10, TCKN 11 haneli olmalı.")
        return data

    form.clean = clean
    return form


def _state(request, provider):
    return request.session.setdefault(f"wiz_{provider.code}", {"config": {}, "secrets": {}, "edit": None, "test": None})


def _save_state(request, provider, state):
    request.session[f"wiz_{provider.code}"] = state
    request.session.modified = True


@login_required
@permission_required(PERM, raise_exception=True)
def home(request):
    accounts = IntegrationAccount.objects.all().order_by("-active", "name")
    stats = {s: IntegrationJob.objects.filter(status=s).count() for s in ("pending", "failed", "success")}
    return render(request, "integrations/home.html", {"accounts": accounts, "stats": stats})


@login_required
@permission_required(PERM, raise_exception=True)
def choose(request):
    groups = {}
    for p in all_providers():
        groups.setdefault(CATEGORY_LABELS.get(p.category, p.category), []).append(p)
    return render(request, "integrations/choose.html", {"groups": groups})


@login_required
@permission_required(PERM, raise_exception=True)
def wizard(request, provider, step):
    p = get_provider(provider)
    if p is None or not p.available:
        raise Http404
    steps = [s for s, _ in p.steps]
    if step not in steps:
        raise Http404
    state = _state(request, p)
    if request.GET.get("edit"):
        acc = get_object_or_404(IntegrationAccount, pk=request.GET["edit"], provider=p.code)
        state = {"config": {**acc.config, "environment": acc.environment}, "secrets": {}, "edit": acc.pk, "test": None,
                 "has_secrets": bool(acc.secret)}
        _save_state(request, p, state)
    elif request.GET.get("reset"):
        state = {"config": {}, "secrets": {}, "edit": None, "test": None}
        _save_state(request, p, state)
    idx = steps.index(step)
    nxt = steps[idx + 1] if idx + 1 < len(steps) else None
    prev = steps[idx - 1] if idx > 0 else None
    ctx = {"p": p, "steps": p.steps, "step": step, "idx": idx, "prev": prev, "state": state}

    if step in ("credentials", "company", "settings"):
        Form = _form_class(p, step, secrets_known=state.get("has_secrets"))
        initial = {f.name: state["config"].get(f.name, f.default) for f in p.fields_for(step) if not f.secret}
        form = Form(request.POST or None, initial=initial)
        if request.method == "POST" and form.is_valid():
            for f in p.fields_for(step):
                val = form.cleaned_data.get(f.name)
                if f.secret:
                    if val:
                        state["secrets"][f.name] = val
                else:
                    state["config"][f.name] = val
            state["test"] = None if step != "settings" else state.get("test")
            _save_state(request, p, state)
            return redirect("integrations:wizard", provider=p.code, step=nxt)
        ctx["form"] = form
        return render(request, "integrations/wizard.html", ctx)

    if step == "test":
        if request.method == "POST" or state.get("test") is None:
            secrets = dict(state["secrets"])
            if state.get("edit") and not secrets:
                secrets = IntegrationAccount.objects.get(pk=state["edit"]).get_secrets()
            ok, msg = p.test_connection(state["config"], secrets, state["config"].get("environment", "test"))
            state["test"] = {"ok": ok, "message": msg, "at": timezone.now().strftime("%d.%m.%Y %H:%M:%S")}
            _save_state(request, p, state)
            if request.method == "POST":
                return redirect(request.path)
        return render(request, "integrations/wizard.html", ctx)

    if step == "summary":
        if request.method == "POST":
            if not (state.get("test") or {}).get("ok"):
                messages.error(request, "Bağlantı testi başarılı olmadan etkinleştirilemez.")
                return redirect("integrations:wizard", provider=p.code, step="test")
            cfg = dict(state["config"])
            env = cfg.pop("environment", "test")
            acc = IntegrationAccount.objects.filter(pk=state.get("edit")).first() or IntegrationAccount(provider=p.code)
            acc.name = f"{p.name} ({'Test' if env == 'test' else 'Canlı'})"
            acc.environment, acc.config, acc.active = env, cfg, True
            if state["secrets"]:
                acc.set_secrets({**(acc.get_secrets() if acc.pk else {}), **state["secrets"]})
            acc.last_test_at, acc.last_test_ok, acc.last_message = timezone.now(), True, state["test"]["message"]
            acc.save()
            IntegrationAccount.objects.filter(provider=p.code).exclude(pk=acc.pk).update(active=False)
            p.on_activate(acc)
            services.log(acc, "activate", True, "Sihirbaz tamamlandı, bağlantı etkinleştirildi.")
            request.session.pop(f"wiz_{p.code}", None)
            messages.success(request, f"{acc.name} etkinleştirildi.")
            return redirect("integrations:account", pk=acc.pk)
        ctx["summary"] = [(f.label, "••••••" if f.secret else _display(f, state["config"].get(f.name)))
                          for f in p.fields if not f.secret or state["secrets"].get(f.name) or state.get("has_secrets")]
        return render(request, "integrations/wizard.html", ctx)
    raise Http404


def _display(field, value):
    if field.kind == "bool":
        return "Evet" if value else "Hayır"
    if field.kind == "choice":
        return dict(field.choices).get(value, value)
    return value if value not in (None, "") else "—"


@login_required
@permission_required(PERM, raise_exception=True)
def account_detail(request, pk):
    acc = get_object_or_404(IntegrationAccount, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "test":
            ok, msg = services.test_account(acc)
            (messages.success if ok else messages.error)(request, msg)
        elif action == "fetch":
            job = services.enqueue(acc, "einvoice.fetch_inbox", "gelen (manuel)", {"days": int(request.POST.get("days", 30))},
                                   key=f"{acc.pk}:inbox:manual:{timezone.now().timestamp()}")
            services.run_job(job)
            job.refresh_from_db()
            (messages.success if job.status == "success" else messages.error)(
                request, f"Gelen faturalar: {job.result or job.last_error}")
        elif action == "status":
            job = services.enqueue(acc, "einvoice.refresh_status", "durum (manuel)", key=f"{acc.pk}:status:manual:{timezone.now().timestamp()}")
            services.run_job(job)
            job.refresh_from_db()
            (messages.success if job.status == "success" else messages.error)(request, f"Durum sorgusu: {job.result or job.last_error}")
        elif action in ("orders", "stock"):
            kind = "trendyol.import_orders" if action == "orders" else "trendyol.push_stock"
            job = services.enqueue(acc, kind, "manuel", {"hours": 72}, key=f"{acc.pk}:{kind}:manual:{timezone.now().timestamp()}")
            services.run_job(job)
            job.refresh_from_db()
            (messages.success if job.status == "success" else messages.error)(request, f"{job.result or job.last_error}")
        elif action == "toggle":
            acc.active = not acc.active
            acc.save(update_fields=["active", "updated_at"])
            messages.success(request, "Bağlantı " + ("etkinleştirildi." if acc.active else "durduruldu."))
        return redirect(request.path)
    return render(request, "integrations/account.html", {
        "acc": acc, "p": acc.provider_obj, "jobs": acc.jobs.all()[:30], "logs": acc.logs.all()[:30]})


@login_required
@permission_required(PERM, raise_exception=True)
def jobs(request):
    if request.method == "POST":
        qs = IntegrationJob.objects.filter(status="failed")
        if request.POST.get("job"):
            qs = qs.filter(pk=request.POST["job"])
        n = 0
        for j in qs:
            services.retry(j)
            n += 1
        messages.success(request, f"{n} iş yeniden kuyruğa alındı. Arka plan işçisi kısa süre içinde çalıştıracak.")
        return redirect(request.get_full_path())
    status = request.GET.get("status", "")
    qs = IntegrationJob.objects.select_related("account")
    if status:
        qs = qs.filter(status=status)
    counts = {s: IntegrationJob.objects.filter(status=s).count() for s, _ in IntegrationJob.STATUS}
    return render(request, "integrations/jobs.html", {"jobs": qs[:200], "status": status, "statuses": IntegrationJob.STATUS,
                                                      "counts": counts})


@login_required
@permission_required(PERM, raise_exception=True)
def listings(request, pk):
    """Ürün eşleştirme: pazaryeri barkodu farklıysa girilir, stok gönderimi ürün bazında kapatılabilir."""
    from apps.catalog.models import Product
    from .models import ChannelListing
    acc = get_object_or_404(IntegrationAccount, pk=pk)
    products = Product.objects.filter(active=True).exclude(kind__in=["raw", "packaging"]).order_by("sku")
    existing = {l.product_id: l for l in acc.listings.all()}
    if request.method == "POST":
        n = 0
        for p in products:
            ext = request.POST.get(f"bc_{p.pk}", "").strip()
            sync = request.POST.get(f"sync_{p.pk}") == "on"
            l = existing.get(p.pk)
            if l is None and not ext and sync:
                continue  # varsayılan: kendi barkodu, stok gönder
            l = l or ChannelListing(account=acc, product=p)
            l.external_barcode, l.sync_stock = ext, sync
            l.save()
            n += 1
        messages.success(request, f"Eşleştirmeler kaydedildi ({n} ürün özel ayarlı).")
        return redirect(request.path)
    rows = [{"p": p, "l": existing.get(p.pk)} for p in products]
    return render(request, "integrations/listings.html", {"acc": acc, "rows": rows})
