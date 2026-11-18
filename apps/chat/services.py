"""
Canlı sohbet. Sunucuya ek kurulum gerektirmez: tarayıcı açık sohbette 3 sn'de, kapalıyken 15 sn'de bir sorar (kısa yoklama).
- Çevrimiçi (yeşil) = son 60 sn içinde sinyal; değilse kırmızı.
- Personel: tüm aktif personelle birebir sohbet; müşteri/bayi destek sohbetlerini görür (Satış ekibi + yöneticiler katılımcıdır).
- Bayi portalı kullanıcısı: yalnızca kendi "Destek" sohbetini görür.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from .models import ONLINE_SECONDS, Conversation, Message, Participant, Presence


def is_portal(user):
    return hasattr(user, "portal") and not user.is_staff


def touch(user):
    Presence.objects.update_or_create(user=user, defaults={"last_seen": timezone.now()})


def online_ids():
    since = timezone.now() - timedelta(seconds=ONLINE_SECONDS)
    return set(Presence.objects.filter(last_seen__gte=since).values_list("user_id", flat=True))


def staff_users():
    from django.contrib.auth.models import Group
    User = get_user_model()
    return User.objects.filter(is_active=True).exclude(portal__isnull=False, is_staff=False).order_by("first_name", "username")


def support_team():
    User = get_user_model()
    return User.objects.filter(Q(is_superuser=True) | Q(groups__name__in=["Satış ekibi", "E-ticaret ekibi"]), is_active=True).distinct()


def direct_with(user, other):
    if is_portal(user) or is_portal(other):
        raise PermissionDenied
    conv = (Conversation.objects.filter(kind="direct", participants__user=user).filter(participants__user=other).first())
    if conv is None:
        conv = Conversation.objects.create(kind="direct")
        Participant.objects.bulk_create([Participant(conversation=conv, user=user), Participant(conversation=conv, user=other)])
    return conv


def support_for(user):
    partner = user.portal.partner
    conv = Conversation.objects.filter(kind="support", partner=partner).first()
    if conv is None:
        conv = Conversation.objects.create(kind="support", partner=partner, title=f"{partner.name} (bayi)")
    ids = {user.pk} | set(support_team().values_list("pk", flat=True))
    existing = set(conv.participants.values_list("user_id", flat=True))
    Participant.objects.bulk_create([Participant(conversation=conv, user_id=i) for i in ids - existing])
    return conv


def get_conv(user, conv_id):
    conv = Conversation.objects.filter(pk=conv_id, participants__user=user).first()
    if conv is None:
        raise PermissionDenied
    return conv


def send(user, conv, body):
    body = (body or "").strip()[:4000]
    if not body:
        return None
    m = Message.objects.create(conversation=conv, sender=user, body=body)
    Conversation.objects.filter(pk=conv.pk).update(updated_at=timezone.now())
    Participant.objects.filter(conversation=conv, user=user).update(last_read_id=m.pk)
    return m


def _name(u):
    return (u.get_full_name() or u.username) if u else "?"


def conversations(user):
    online = online_ids()
    out = []
    for p in Participant.objects.filter(user=user).select_related("conversation", "conversation__partner"):
        c = p.conversation
        others = [x.user for x in c.participants.select_related("user") if x.user_id != user.pk]
        last = c.messages.order_by("-id").first()
        if c.kind == "direct":
            other = others[0] if others else None
            title, is_online = _name(other), bool(other and other.pk in online)
        elif c.kind == "support" and is_portal(user):
            title, is_online = "Eglo destek", any(o.pk in online for o in others)
        else:
            portal_users = [o for o in others if is_portal(o)]
            title = c.title or ", ".join(_name(o) for o in others[:3])
            is_online = any(o.pk in online for o in (portal_users or others))
        out.append({"id": c.pk, "title": title, "kind": c.kind, "online": is_online,
                    "unread": c.messages.filter(id__gt=p.last_read_id).exclude(sender=user).count(),
                    "last": (last.body[:60] if last else ""), "at": last.created_at.strftime("%H:%M") if last else "",
                    "ts": c.updated_at.timestamp()})
    return sorted(out, key=lambda x: -x["ts"])


def messages_after(user, conv, after=0):
    msgs = list(conv.messages.filter(id__gt=after).select_related("sender").order_by("id")[:200])
    if msgs:
        Participant.objects.filter(conversation=conv, user=user).update(last_read_id=msgs[-1].pk)
    return [{"id": m.pk, "me": m.sender_id == user.pk, "name": _name(m.sender), "body": m.body,
             "at": timezone.localtime(m.created_at).strftime("%d.%m %H:%M")} for m in msgs]
