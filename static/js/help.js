/* Açıklama metinlerini etiketin yanında ⓘ simgesine dönüştürür (masaüstünde üzerine gel, mobilde dokun). */
(function () {
  function tip(label, text) {
    if (!label || !text || label.querySelector(".info-tip")) return;
    const b = document.createElement("button");
    b.type = "button"; b.className = "info-tip"; b.setAttribute("aria-label", "Açıklama: " + text);
    b.innerHTML = '<span aria-hidden="true">i</span><span class="info-pop" role="tooltip"></span>';
    b.querySelector(".info-pop").textContent = text;
    b.addEventListener("click", e => { e.preventDefault(); e.stopPropagation();
      document.querySelectorAll(".info-tip.open").forEach(x => x !== b && x.classList.remove("open")); b.classList.toggle("open"); });
    label.appendChild(b);
  }
  function run() {
    // uygulama formları
    document.querySelectorAll(".helptext").forEach(h => {
      const box = h.parentElement, label = box && box.querySelector("label");
      if (label) { tip(label, h.textContent.trim()); h.style.display = "none"; }
    });
    // yönetim paneli
    document.querySelectorAll(".form-row .help, .fieldBox .help").forEach(h => {
      const row = h.closest(".fieldBox") || h.closest(".form-row"), label = row && row.querySelector("label");
      if (label && h.textContent.trim()) { tip(label, h.textContent.trim()); h.style.display = "none"; }
    });
  }
  document.addEventListener("click", () => document.querySelectorAll(".info-tip.open").forEach(x => x.classList.remove("open")));
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", run) : run();
})();
