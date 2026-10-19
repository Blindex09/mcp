(el) => {
  // FATOS de um gatilho de dica (tooltip): o que o aria-describedby aponta, se ha um role=tooltip visivel na pagina e se o gatilho so tem title.
  const root = el.getRootNode();
  const byId = (id) => (id ? (root.getElementById ? root.getElementById(id) : document.getElementById(id)) : null);
  const vis = (e) => { if (!e) return false; const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0'; };
  const desc = (el.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean).map(byId).filter(Boolean);
  const tips = Array.from(document.querySelectorAll('[role=tooltip]'));
  return {
    describedby_ids: (el.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean),
    described_by_tooltip: desc.some((d) => d.getAttribute('role') === 'tooltip'),
    described_text: desc.map((d) => (d.textContent || '').trim()).join(' ').slice(0, 80),
    tooltip_visible: tips.some(vis), tooltip_count: tips.length,
    tooltip_text: (tips.find(vis)?.textContent || '').trim().slice(0, 80),
    has_title: el.hasAttribute('title'), title: el.getAttribute('title'),
  };
}
