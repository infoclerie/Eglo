/* Fotoğraf seçicide seçilen görsellerin küçük önizlemesi (yüklemeden önce kontrol için). */
document.addEventListener("change", e => {
  const inp = e.target;
  if (!inp.matches || !inp.matches('.photo-input input[type="file"]')) return;
  const box = inp.closest(".photo-input"), wrap = box.querySelector(".photo-previews");
  wrap.innerHTML = "";
  box.querySelectorAll('input[type="file"]').forEach(i => [...i.files].forEach(f => {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(f); img.alt = f.name; img.onload = () => URL.revokeObjectURL(img.src);
    wrap.appendChild(img);
  }));
});
