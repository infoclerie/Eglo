/* Canlı sohbet penceresi. Yeşil nokta = çevrimiçi, kırmızı = çevrimdışı. Açıkken 3 sn, kapalıyken 15 sn'de bir yenilenir. */
(function () {
  if (window.__chat) return; window.__chat = 1;
  const csrf = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "";
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const post = (u, d) => fetch(u, {method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": csrf}, body: JSON.stringify(d)}).then(r => r.json());
  const root = document.createElement("div"); root.className = "chat-root";
  root.innerHTML = `<button class="chat-fab" aria-label="Canlı sohbet">💬<span class="chat-badge" hidden></span></button>
    <div class="chat-panel" hidden><header><b class="chat-title">Sohbet</b><span style="flex:1"></span>
      <button class="chat-back" hidden>←</button><button class="chat-close">×</button></header>
      <div class="chat-tabs"><button data-t="convs" class="on">Sohbetler</button><button data-t="people">Kişiler</button></div>
      <div class="chat-body"></div>
      <form class="chat-form" hidden><input placeholder="Mesaj yazın…" maxlength="4000" autocomplete="off"><button>Gönder</button></form></div>`;
  document.body.appendChild(root);
  const $ = s => root.querySelector(s), body = $(".chat-body"), panel = $(".chat-panel");
  let open = false, tab = "convs", conv = null, after = 0, timer = null, lastConvs = [];
  const dot = on => `<i class="dot ${on ? "on" : "off"}" title="${on ? "Çevrimiçi" : "Çevrimdışı"}"></i>`;
  function renderConvs(list) {
    body.innerHTML = list.length ? list.map(c => `<button class="chat-row" data-c="${c.id}">${dot(c.online)}<span><b>${esc(c.title)}</b><small>${esc(c.last)}</small></span>
      <em>${c.at}${c.unread ? `<span class="chat-badge">${c.unread}</span>` : ""}</em></button>`).join("") : '<p class="chat-empty">Henüz sohbet yok. "Kişiler" sekmesinden başlatın.</p>';
  }
  function loadPeople() {
    fetch("/chat/api/people/").then(r => r.json()).then(d => {
      if (d.support) { body.innerHTML = '<button class="chat-row" data-support="1">' + dot(true) + '<span><b>Eglo destek ekibi</b><small>Sorunuz için yazın</small></span></button>'; return; }
      body.innerHTML = d.people.map(p => `<button class="chat-row" data-u="${p.id}">${dot(p.online)}<span><b>${esc(p.name)}</b><small>${p.online ? "Çevrimiçi" : "Çevrimdışı"}</small></span></button>`).join("") || '<p class="chat-empty">Kullanıcı yok.</p>';
    });
  }
  function openConv(id, title) {
    conv = id; after = 0; body.innerHTML = ""; $(".chat-form").hidden = false; $(".chat-back").hidden = false; $(".chat-tabs").hidden = true;
    $(".chat-title").textContent = title || "Sohbet"; poll(); $(".chat-form input").focus();
  }
  function back() { conv = null; $(".chat-form").hidden = true; $(".chat-back").hidden = true; $(".chat-tabs").hidden = false; $(".chat-title").textContent = "Sohbet"; show(); }
  function show() { if (tab === "people") loadPeople(); else renderConvs(lastConvs); }
  function poll() {
    const q = conv ? `?conv=${conv}&after=${after}` : "";
    fetch("/chat/api/poll/" + q).then(r => r.ok ? r.json() : null).then(d => {
      if (!d) return;
      lastConvs = d.conversations;
      const b = $(".chat-fab .chat-badge"); b.hidden = !d.unread; b.textContent = d.unread;
      if (conv && d.messages) {
        const atBottom = body.scrollTop + body.clientHeight >= body.scrollHeight - 30;
        d.messages.forEach(m => { after = m.id; body.insertAdjacentHTML("beforeend", `<div class="msg ${m.me ? "me" : ""}">${m.me ? "" : `<small>${esc(m.name)}</small>`}${esc(m.body).replace(/\n/g, "<br>")}<time>${m.at}</time></div>`); });
        if (d.messages.length && atBottom || after && d.messages.length === after) body.scrollTop = body.scrollHeight;
        const c = lastConvs.find(x => x.id == conv); if (c) $(".chat-title").innerHTML = dot(c.online) + " " + esc(c.title);
      } else if (open && !conv && tab === "convs") renderConvs(lastConvs);
    }).catch(() => {});
  }
  function schedule() { clearInterval(timer); timer = setInterval(poll, open ? 3000 : 15000); }
  $(".chat-fab").onclick = () => { open = !open; panel.hidden = !open; root.classList.toggle("open", open); if (open) { show(); poll(); } schedule(); };
  $(".chat-close").onclick = () => { open = false; panel.hidden = true; root.classList.remove("open"); schedule(); };
  $(".chat-back").onclick = back;
  root.querySelectorAll(".chat-tabs button").forEach(b => b.onclick = () => { tab = b.dataset.t; root.querySelectorAll(".chat-tabs button").forEach(x => x.classList.toggle("on", x === b)); show(); });
  body.addEventListener("click", e => {
    const r = e.target.closest(".chat-row"); if (!r) return;
    if (r.dataset.c) openConv(r.dataset.c, r.querySelector("b").textContent);
    else if (r.dataset.u) post("/chat/api/start/", {user: r.dataset.u}).then(d => openConv(d.id, r.querySelector("b").textContent));
    else if (r.dataset.support) post("/chat/api/start/", {support: 1}).then(d => openConv(d.id, "Eglo destek"));
  });
  $(".chat-form").onsubmit = e => { e.preventDefault(); const i = $(".chat-form input"); const t = i.value.trim(); if (!t || !conv) return;
    i.value = ""; post("/chat/api/send/", {conv, body: t}).then(poll); };
  poll(); schedule();
})();
