/* Yapay zekâ asistanı: soru gönderir, cevabı güvenli biçimde (önce HTML kaçışı) basit Markdown ile gösterir. */
(function () {
  const esc = s => s.replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  function inline(s) { return s.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>"); }
  function md(src) {
    const lines = esc(src || "").split(/\r?\n/), out = [];
    let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < lines.length && /^\s*\|[\s:\-|]+\|\s*$/.test(lines[i + 1])) {
        const row = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => inline(c.trim()));
        let h = "<div class='table-wrap'><table class='table'><thead><tr>" + row(l).map(c => "<th>" + c + "</th>").join("") + "</tr></thead><tbody>";
        i += 2;
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { h += "<tr>" + row(lines[i]).map(c => "<td>" + c + "</td>").join("") + "</tr>"; i++; }
        out.push(h + "</tbody></table></div>"); continue;
      }
      if (/^\s*[-*•]\s+/.test(l)) {
        let h = "<ul>";
        while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) { h += "<li>" + inline(lines[i].replace(/^\s*[-*•]\s+/, "")) + "</li>"; i++; }
        out.push(h + "</ul>"); continue;
      }
      if (/^\s*\d+[.)]\s+/.test(l)) {
        let h = "<ol>";
        while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) { h += "<li>" + inline(lines[i].replace(/^\s*\d+[.)]\s+/, "")) + "</li>"; i++; }
        out.push(h + "</ol>"); continue;
      }
      const hm = l.match(/^#{1,4}\s+(.*)/);
      if (hm) { out.push("<p><b>" + inline(hm[1]) + "</b></p>"); i++; continue; }
      if (l.trim()) out.push("<p>" + inline(l) + "</p>");
      i++;
    }
    return out.join("");
  }
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
  function setup(box) {
    const form = box.querySelector(".ai-form"), q = box.querySelector(".ai-q"), btn = form.querySelector("button");
    const thread = box.querySelector(".ai-thread"), out = box.querySelector(".ai-out");
    box.querySelectorAll("[data-md]").forEach(el => { el.innerHTML = md(el.textContent); });
    if (thread) thread.scrollTop = thread.scrollHeight;
    function add(role, html, meta) {
      const target = thread || out;
      if (!thread) target.innerHTML = "";
      const empty = target.querySelector(".ai-empty"); if (empty) empty.remove();
      const d = document.createElement("div"); d.className = "ai-msg " + role;
      d.innerHTML = "<div class='ai-bubble'>" + html + "</div>" + (meta ? "<div class='ai-meta'>" + esc(meta) + "</div>" : "");
      target.appendChild(d); if (thread) thread.scrollTop = thread.scrollHeight; return d;
    }
    async function send(text) {
      text = (text || "").trim(); if (!text) return;
      if (thread) add("user", esc(text));
      const wait = add("assistant", "<span class='ai-typing'>Veriler inceleniyor…</span>");
      q.value = ""; btn.disabled = true;
      try {
        const r = await fetch("/assistant/api/sor/", {method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": csrf()}, body: JSON.stringify({q: text})});
        const d = await r.json();
        wait.remove();
        if (d.error) add("assistant error", esc(d.error));
        else add("assistant", (thread ? "" : "<div class='ai-qtext'>" + esc(text) + "</div>") + md(d.answer.content),
                 d.answer.tools.length ? "Bakılan veriler: " + d.answer.tools.join(", ") : "");
      } catch (e) { wait.remove(); add("assistant error", "Bağlantı hatası, tekrar deneyin."); }
      btn.disabled = false; q.focus();
    }
    form.addEventListener("submit", e => { e.preventDefault(); send(q.value); });
    box.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => send(c.textContent)));
  }
  document.addEventListener("DOMContentLoaded", () => document.querySelectorAll("[data-ai]").forEach(setup));
})();
