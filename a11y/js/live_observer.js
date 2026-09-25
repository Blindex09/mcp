(() => {
  if (window.__a11yLive) return;
  window.__a11yLive = [];
  const sel = '[aria-live]:not([aria-live=off]),[role=alert],[role=status],[role=log],[role=alertdialog]';
  const rec = (n) => {
    const el = n && n.nodeType === 3 ? n.parentElement : n;
    if (!el || !el.closest) return;
    const r = el.closest(sel);
    if (!r) return;
    const t = (r.innerText || '').trim().slice(0, 200);
    if (t) window.__a11yLive.push({role: r.getAttribute('role') || ('aria-live=' + r.getAttribute('aria-live')), text: t});
  };
  new MutationObserver(ms => ms.forEach(m => { rec(m.target); m.addedNodes.forEach(rec); }))
    .observe(document, {subtree: true, childList: true, characterData: true});
})()
