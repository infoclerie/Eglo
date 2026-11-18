/* Yönetim listeleri: sağdaki süzgeçleri tablonun üstünde açılır filtre çubuğuna çevirir + Excel'e aktar düğmesi. */
(function () {
  function run() {
    const nav = document.getElementById("changelist-filter");
    const cl = document.getElementById("changelist");
    if (!cl) return;
    const bar = document.createElement("div");
    bar.className = "grid-bar";
    if (nav) {
      nav.querySelectorAll("details[data-filter-title]").forEach(d => {
        const title = (d.querySelector("summary")?.textContent || d.dataset.filterTitle || "").trim().replace(/\s*süzgecine göre$/i, "");
        const sel = document.createElement("select");
        let active = false;
        d.querySelectorAll("li a").forEach((a, i) => {
          const o = document.createElement("option");
          o.value = a.getAttribute("href"); o.textContent = i === 0 ? title + ": Tümü" : a.textContent.trim();
          if (a.parentElement.classList.contains("selected")) { o.selected = true; if (i > 0) active = true; }
          sel.appendChild(o);
        });
        sel.onchange = () => { location.href = sel.value; };
        const wrap = document.createElement("label");
        wrap.className = "grid-filter" + (active ? " on" : "");
        wrap.appendChild(sel);
        bar.appendChild(wrap);
      });
      const clear = [...nav.querySelectorAll("a")].find(a => /temizle|clear/i.test(a.textContent));
      if (clear) { const c = document.createElement("a"); c.href = clear.getAttribute("href"); c.className = "btn btn-sm"; c.textContent = "Filtreleri temizle"; bar.appendChild(c); }
      nav.style.display = "none";
      cl.classList.add("no-side-filter");
    }
    const sp = document.createElement("span"); sp.style.flex = "1"; bar.appendChild(sp);
    const ex = document.createElement("a");
    const q = new URLSearchParams(location.search); q.set("_export", "xlsx");
    ex.href = "?" + q.toString(); ex.className = "btn btn-sm btn-excel"; ex.textContent = "Excel'e aktar (filtreli liste)";
    bar.appendChild(ex);
    const anchor = cl.querySelector("#toolbar") || cl.querySelector(".changelist-form-container") || cl.firstElementChild;
    anchor.parentNode.insertBefore(bar, anchor);
  }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", run) : run();
})();
