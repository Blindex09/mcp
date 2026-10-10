({start, limit}) => {
  // Descoberta SEM CDP (Firefox/WebKit), atravessando Shadow DOM aberto: e' o que o navegador diz ser focavel
  // (tabIndex calculado por ele) OU o que TEM listener de clique registrado (gancho em addEventListener e
  // propriedades on*), OU cursor:pointer (sinal MAIS FRACO). Nenhuma lista de tags.
  const out = []; let total = 0; let n = start;
  const roots = [document.body]; const all = [];
  const walk = (node) => { for (const el of node.querySelectorAll('*')) { all.push(el); if (el.shadowRoot) walk(el.shadowRoot); } };
  walk(document.body);
  const handlerProps = ['onclick', 'onmousedown', 'onmouseup', 'onpointerdown', 'ontouchstart', 'onkeydown'];
  for (const el of all) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (!(r.width > 0 && r.height > 0) || cs.visibility === 'hidden' || cs.display === 'none') continue;
    const focusable = el.tabIndex >= 0 && !el.disabled;
    const listener = !!(el.__a11yL && el.__a11yL.size) || handlerProps.some(p => typeof el[p] === 'function');
    const pointer = cs.cursor === 'pointer';
    if (!focusable && !listener && !pointer) continue;
    total++;
    if (out.length >= limit) continue;
    if (!el.getAttribute('data-a11y-id')) el.setAttribute('data-a11y-id', 'e' + (++n));
    out.push({id: el.getAttribute('data-a11y-id'), focusable: focusable, listener: listener, pointer_cursor: pointer});
  }
  return {found: out, total: total, next: n};
}
