# chat — Canlı sohbet

- Ofis içi birebir sohbet + bayi/müşteri (portal kullanıcısı) ↔ "Eglo destek" sohbeti.
- Modeller: Conversation (direct/group/support), Participant (last_read_id), Message, Presence (last_seen).
- Çevrimiçi = son 60 sn içinde sinyal (yeşil nokta), değilse kırmızı.
- Taşıma: kısa aralıklı yoklama (panel açıkken 3 sn, kapalıyken 15 sn) → sunucuya ek kurulum (Redis/WebSocket) gerekmez.
  Kullanıcı sayısı çok artarsa Django Channels + Redis'e geçilebilir; API (`/chat/api/poll|people|start|send/`) aynı kalır.
- Destek ekibi: süper kullanıcılar + "Satış ekibi" + "E-ticaret ekibi" grupları.
- Arayüz: `static/js/chat.js` (sağ alttaki 💬 düğmesi), base.html ve portal/base.html içinde yüklenir.
