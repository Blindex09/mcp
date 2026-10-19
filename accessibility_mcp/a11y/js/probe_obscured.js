() => {
  // O elemento em foco esta coberto por outro? Amostra 5 pontos do retangulo e pergunta ao navegador quem esta por cima.
  let e = document.activeElement;
  while (e && e.shadowRoot && e.shadowRoot.activeElement) e = e.shadowRoot.activeElement;
  if (!e || e === document.body || e === document.documentElement) return null;
  const r = e.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return {zero_size: true};
  const vw = window.innerWidth, vh = window.innerHeight;
  const pts = [[0.5, 0.5], [0.1, 0.1], [0.9, 0.1], [0.1, 0.9], [0.9, 0.9]].map(([fx, fy]) => [r.left + r.width * fx, r.top + r.height * fy]);
  let covered = 0, offscreen = 0, by = null;
  for (const [x, y] of pts) {
    if (x < 0 || y < 0 || x >= vw || y >= vh) { offscreen++; continue; }
    // elementFromPoint devolve o hospedeiro de um Shadow DOM aberto, nao o elemento de dentro: desce ate o mais profundo.
    let top = document.elementFromPoint(x, y);
    while (top && top.shadowRoot) { const dentro = top.shadowRoot.elementFromPoint(x, y); if (!dentro || dentro === top) break; top = dentro; }
    if (!top) continue;
    if (top === e || e.contains(top) || top.contains(e)) continue;
    covered++;
    if (!by) {
      let pos = getComputedStyle(top).position;
      for (let p = top; p && p !== document.body; p = p.parentElement) { const ps = getComputedStyle(p).position; if (ps === 'fixed' || ps === 'sticky') { pos = ps; break; } }
      by = {tag: top.tagName.toLowerCase(), id: top.id || null, role: top.getAttribute('role'), position: pos, text: (top.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 40)};
    }
  }
  return {points: pts.length, covered, offscreen, covered_by: by, rect: {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}};
}
