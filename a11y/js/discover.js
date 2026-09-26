(limit) => {
  // Descoberta SEM CDP (Firefox/WebKit): o que o navegador diz ser focavel (tabIndex calculado por ele)
  // ou que tem cursor:pointer (sinal MAIS FRACO: nao enxerga listeners, so o estilo). Nenhuma lista de tags.
  const out = []; let total = 0;
  for (const el of document.body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (!(r.width > 0 && r.height > 0) || cs.visibility === 'hidden' || cs.display === 'none') continue;
    const focusable = el.tabIndex >= 0 && !el.disabled;
    const pointer = cs.cursor === 'pointer';
    if (!focusable && !pointer) continue;
    total++;
    if (out.length >= limit) continue;
    if (!el.getAttribute('data-a11y-id')) el.setAttribute('data-a11y-id', 'e' + (window.__a11yNext = (window.__a11yNext || 0) + 1));
    out.push({id: el.getAttribute('data-a11y-id'), focusable: focusable, pointer_cursor: pointer});
  }
  return {found: out, total: total};
}
