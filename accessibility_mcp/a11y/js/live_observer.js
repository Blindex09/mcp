(() => {
  if (window.__a11yLive) return;
  window.__a11yLive = [];
  const sel = '[aria-live]:not([aria-live=off]),[role=alert],[role=status],[role=log],[role=alertdialog]';
  const regionOf = (n) => {
    const el = n && n.nodeType === 3 ? n.parentElement : n;
    return el && el.closest ? el.closest(sel) : null;
  };
  // Uma entrada por regiao a cada LOTE de mudancas (uma troca de textContent gera varios registros; o leitor de tela anuncia uma vez).
  new MutationObserver((records) => {
    const regions = new Set();
    const fresh = new Set();  // regioes inseridas neste mesmo lote: nasceram junto com o texto (a regiao nao existia antes)
    const inserted = (n) => { if (n.nodeType !== 1) return; if (n.matches(sel)) fresh.add(n); n.querySelectorAll(sel).forEach(x => fresh.add(x)); };
    for (const m of records) {
      const r = regionOf(m.target); if (r) regions.add(r);
      m.addedNodes.forEach(n => { inserted(n); const a = regionOf(n); if (a) regions.add(a); });
    }
    regions.forEach(r => {
      const t = (r.innerText || '').trim().slice(0, 200);
      if (t) window.__a11yLive.push({role: r.getAttribute('role') || ('aria-live=' + r.getAttribute('aria-live')), text: t, fresh: fresh.has(r)});
    });
  }).observe(document, {subtree: true, childList: true, characterData: true});
})()
