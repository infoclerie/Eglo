/* El terminali / USB barkod okuyucu (klavye modu) desteği.
   Okuyucu karakterleri çok hızlı yazıp Enter gönderir. Hiçbir kutu seçili değilken okutulan barkod
   sayfadaki .scan-input kutusuna (yoksa üst arama kutusuna) yazılır ve gönderilir. Telefon kamerası ile okuma: sonraki sürüm. */
(function () {
  let buf = "", last = 0;
  function target() { return document.querySelector(".scan-input") || document.querySelector(".top-search"); }
  document.addEventListener("keydown", e => {
    const el = document.activeElement, typing = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
    if (typing || e.ctrlKey || e.metaKey || e.altKey) { buf = ""; return; }
    const now = Date.now();
    if (now - last > 400) buf = "";
    last = now;
    if (e.key === "Enter") {
      if (buf.length >= 4) { const t = target(); if (t) { e.preventDefault(); t.value = buf; t.form ? t.form.requestSubmit() : null; } }
      buf = ""; return;
    }
    if (e.key.length === 1) buf += e.key;
  });
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".scan-input").forEach(i => {
      i.setAttribute("autocomplete", "off"); i.setAttribute("autocapitalize", "off"); i.setAttribute("spellcheck", "false");
      i.addEventListener("focus", () => i.select());
    });
  });
})();
