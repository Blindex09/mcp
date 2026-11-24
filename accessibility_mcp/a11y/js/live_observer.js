(() => {
  if (window.__a11yLive) return;
  window.__a11yLive = [];
  const sel = '[aria-live]:not([aria-live=off]),[role=alert],[role=status],[role=log],[role=alertdialog]';
  const regionOf = (n) => {
    const el = n && n.nodeType === 3 ? n.parentElement : n;
    return el && el.closest ? el.closest(sel) : null;
  };
  // Uma entrada por regiao a cada LOTE de mudancas (uma troca de textContent gera varios registros; isto mede mutacoes, nao a fala do leitor).
  new MutationObserver((records) => {
    const regions = new Set();
    const fresh = new Set();  // regioes inseridas neste mesmo lote: nasceram junto com o texto (a regiao nao existia antes)
    const inserted = (n) => { if (n.nodeType !== 1) return; if (n.matches(sel)) fresh.add(n); n.querySelectorAll(sel).forEach(x => fresh.add(x)); };
    for (const m of records) {
      const r = regionOf(m.target); if (r) regions.add(r);
      m.addedNodes.forEach(n => { inserted(n); const a = regionOf(n); if (a) regions.add(a); });
    }
    regions.forEach(r => {
      const t = (r.innerText || '').trim();
      if (t) window.__a11yLive.push({role: r.getAttribute('role') || ('aria-live=' + r.getAttribute('aria-live')), text: t, fresh: fresh.has(r)});
    });
  }).observe(document, {subtree: true, childList: true, characterData: true});

  const wrapAriaNotify = (proto) => {
    if (!proto || typeof proto.ariaNotify !== 'function' || proto.ariaNotify.__a11yWrapped) return;
    const orig = proto.ariaNotify;
    const wrapped = function ariaNotify(message, options) {
      try {
        const text = String(message == null ? '' : message).trim();
        if (text) {
          window.__a11yLive.push({
            role: 'ariaNotify',
            priority: (options && options.priority) || 'normal',
            text,
            fresh: false,
          });
        }
      } catch (e) {}
      return orig.apply(this, arguments);
    };
    wrapped.__a11yWrapped = true;
    proto.ariaNotify = wrapped;
  };
  wrapAriaNotify(typeof Element !== 'undefined' && Element.prototype);
  wrapAriaNotify(typeof Document !== 'undefined' && Document.prototype);
})()
