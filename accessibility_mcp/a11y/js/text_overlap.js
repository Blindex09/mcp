() => {
  const boxes = [];
  const clean = (t) => (t || '').replace(/\s+/g, ' ').trim();
  for (const el of document.querySelectorAll('body *')) {
    const tag = el.tagName.toLowerCase();
    if (tag === 'script' || tag === 'style' || tag === 'noscript') continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
    const er = el.getBoundingClientRect();
    if (er.width <= 1 || er.height <= 1) continue;
    if (cs.overflow === 'hidden' && (er.width <= 2 || er.height <= 2)) continue;
    if (typeof el.checkVisibility === 'function' && !el.checkVisibility({visibilityProperty: true, contentVisibilityAuto: true})) continue;
    for (const node of el.childNodes) {
      if (node.nodeType !== 3) continue;
      const text = clean(node.textContent);
      if (!text) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      const r = range.getBoundingClientRect();
      if (r.width <= 1 || r.height <= 1) continue;
      boxes.push({
        el,
        tag,
        text: text.slice(0, 50),
        left: r.left + window.scrollX,
        top: r.top + window.scrollY,
        right: r.right + window.scrollX,
        bottom: r.bottom + window.scrollY,
      });
    }
  }
  boxes.sort((a, b) => (a.top - b.top) || (a.left - b.left));
  const out = [];
  const tol = 2;
  for (let i = 0; i < boxes.length && out.length < 30; i++) {
    const a = boxes[i];
    for (let j = i + 1; j < boxes.length && out.length < 30; j++) {
      const b = boxes[j];
      if (b.top >= a.bottom - tol) break;
      if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const ow = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const oh = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ow > tol && oh > tol) {
        out.push({
          first_tag: a.tag,
          first_text: a.text,
          second_tag: b.tag,
          second_text: b.text,
          overlap_px: [Math.round(ow), Math.round(oh)],
        });
      }
    }
  }
  return out;
}
