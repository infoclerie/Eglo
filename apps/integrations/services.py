"""
Entegrasyon iş kuyruğu. Kurallar:
- Her iş bir tekillik anahtarı taşır → aynı iş iki kez kuyruğa girmez (mükerrer kayıt engeli).
- Hata olursa yeniden deneme aralığı: 2^deneme dakika (2, 4, 8, 16 ...), en fazla `max_attempts`.
- Tüm denemeler bitince iş "Başarısız" olur; ekrandan "Yeniden dene" ile tekrar kuyruğa alınır.
- `run_due` arka plan işçisi (python manage.py run_jobs --loop) tarafından sürekli çalıştırılır.
"""
import traceback
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import IntegrationAccount, IntegrationJob, SyncLog


def active_account(category):
    for acc in IntegrationAccount.objects.filter(active=True):
        p = acc.provider_obj
        if p and p.category == category:
            return acc
    return None


def enqueue(account, kind, ref="", payload=None, key=None, max_attempts=5):
    key = key or f"{account.pk}:{kind}:{ref}"
    job, created = IntegrationJob.objects.get_or_create(
        idempotency_key=key,
        defaults={"account": account, "kind": kind, "ref": ref, "payload": payload or {}, "max_attempts": max_attempts})
    if not created and job.status == "failed":
        retry(job)
    return job


def retry(job):
    job.status, job.attempts, job.next_run_at, job.last_error = "pending", 0, timezone.now(), ""
    job.save(update_fields=["status", "attempts", "next_run_at", "last_error"])
    return job


def log(account, action, ok, message, detail=""):
    return SyncLog.objects.create(account=account, action=action, ok=ok, message=message[:500], detail=detail[:20000])


def run_job(job):
    with transaction.atomic():
        job = IntegrationJob.objects.select_for_update().get(pk=job.pk)
        if job.status not in ("pending",):
            return job
        job.status = "running"
        job.attempts += 1
        job.save(update_fields=["status", "attempts"])
    account, provider = job.account, job.account.provider_obj
    try:
        with transaction.atomic():
            result = provider.handle(account, job)
        job.status, job.result, job.last_error, job.finished_at = "success", result or {}, "", timezone.now()
        job.save(update_fields=["status", "result", "last_error", "finished_at"])
        log(account, job.kind, True, f"{job.ref or job.kind}: başarılı {result or ''}")
    except Exception as exc:  # noqa: BLE001 — dış sistem hataları kuyrukta yönetilir
        err = str(exc) or exc.__class__.__name__
        if job.attempts >= job.max_attempts:
            job.status, job.finished_at = "failed", timezone.now()
            provider.on_final_failure(account, job, err)
        else:
            job.status, job.next_run_at = "pending", timezone.now() + timedelta(minutes=2 ** job.attempts)
        job.last_error = err[:2000]
        job.save(update_fields=["status", "next_run_at", "last_error", "finished_at"])
        log(account, job.kind, False, f"{job.ref or job.kind}: {err[:300]}", traceback.format_exc())
    return job


def run_due(limit=25):
    jobs = list(IntegrationJob.objects.filter(status="pending", next_run_at__lte=timezone.now(),
                                              account__active=True).order_by("next_run_at")[:limit])
    for job in jobs:
        run_job(job)
    return len(jobs)


def schedule_periodic(now=None):
    """Her aktif bağlantının periyodik işlerini (sağlayıcı tanımlar) zaman dilimi başına bir kez kuyruğa alır."""
    now = now or timezone.now()
    created = 0
    for acc in IntegrationAccount.objects.filter(active=True):
        p = acc.provider_obj
        if not p:
            continue
        for kind, ref, payload, every in p.periodic(acc):
            bucket = int(now.timestamp() // (max(1, int(every)) * 60))
            created += _once(acc, kind, ref, payload, f"{acc.pk}:{kind}:{bucket}")
    return created


def _once(acc, kind, ref, payload, key):
    if IntegrationJob.objects.filter(idempotency_key=key).exists():
        return 0
    enqueue(acc, kind, ref, payload, key=key)
    return 1


def test_account(account):
    ok, msg = account.provider_obj.test_connection(account.config, account.get_secrets(), account.environment)
    account.last_test_at, account.last_test_ok, account.last_message = timezone.now(), ok, msg
    account.save(update_fields=["last_test_at", "last_test_ok", "last_message", "updated_at"])
    log(account, "connection_test", ok, msg)
    return ok, msg
