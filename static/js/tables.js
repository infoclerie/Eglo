/* Uygulama tabloları: her sütunun üstünde Excel tarzı filtre kutusu + "Excel'e aktar" (görünen satırlar, Türkçe Excel uyumlu CSV). */
(function () {
  function txt(c) { return (c.innerText || "").replace(/\s+/g, " ").trim(); }
  function enhance(table) {
    const head = table.tHead, body = table.tBodies[0];
    if (!head || !body || body.rows.length < 3 || table.dataset.grid === "off") return;
    const cols = head.rows[0].cells.length;
    const fr = head.insertRow(-1); fr.className = "filter-row";
    for (let i = 0; i < cols; i++) {
      const th = document.createElement("th"); fr.appendChild(th);
      if (!txt(head.rows[0].cells[i])) continue;
      const inp = document.createElement("input"); inp.type = "search"; inp.placeholder = "Filtre…"; inp.dataset.col = i;
      inp.setAttribute("aria-label", txt(head.rows[0].cells[i]) + " filtresi");
      th.appendChild(inp);
    }
    const apply = () => {
      const f = [...fr.querySelectorAll("input")].map(x => [+x.dataset.col, x.value.toLocaleLowerCase("tr")]).filter(x => x[1]);
      [...body.rows].forEach(r => { r.style.display = f.every(([c, v]) => r.cells[c] && txt(r.cells[c]).toLocaleLowerCase("tr").includes(v)) ? "" : "none"; });
    };
    fr.addEventListener("input", apply);
    const btn = document.createElement("button"); btn.type = "button"; btn.className = "btn btn-sm btn-excel"; btn.textContent = "Excel'e aktar";
    btn.onclick = () => {
      const rows = [[...head.rows[0].cells].map(txt)];
      [...body.rows].filter(r => r.style.display !== "none" && r.cells.length === cols).forEach(r => rows.push([...r.cells].map(txt)));
      const csv = "﻿" + rows.map(r => r.map(v => '"' + v.replace(/"/g, '""') + '"').join(";")).join("\r\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
      a.download = (document.querySelector("h1")?.innerText || "liste").trim().replace(/[^\wçğıöşüÇĞİÖŞÜ]+/g, "-") + ".csv";
      a.click();
    };
    const holder = document.createElement("div"); holder.className = "table-tools"; holder.appendChild(btn);
    const card = table.closest(".card") || table;
    card.parentNode.insertBefore(holder, card);
  }
  function run() { document.querySelectorAll("body.erp table.table").forEach(enhance); }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", run) : run();
})();
