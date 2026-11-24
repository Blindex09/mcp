(args) => {
  const OVERLAY_ID = '__a11y_annotate_overlay__';
  const prev = document.getElementById(OVERLAY_ID);
  if (prev) prev.remove();
  const colors = {
    critical: '#dc2626',
    serious: '#ea580c',
    moderate: '#d97706',
    minor: '#2563eb',
  };
  const wrap = document.createElement('div');
  wrap.id = OVERLAY_ID;
  wrap.setAttribute('aria-hidden', 'true');
  wrap.style.cssText = 'position:absolute;top:0;left:0;width:0;height:0;overflow:visible;pointer-events:none;z-index:2147483647;';

  const resolve = (selector) => {
    try {
      if (Array.isArray(selector)) {
        let root = document;
        let el = null;
        for (const part of selector) {
          el = root && root.querySelector ? root.querySelector(part) : null;
          if (!el) return null;
          root = el.shadowRoot || null;
        }
        return el;
      }
      return typeof selector === 'string' ? document.querySelector(selector) : null;
    } catch (e) {
      return null;
    }
  };

  const marked = [];
  let skipped = 0;
  const items = Array.isArray(args && args.items) ? args.items : [];
  for (const item of items) {
    const el = resolve(item.selector);
    if (!el || typeof el.getBoundingClientRect !== 'function') {
      skipped += 1;
      continue;
    }
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) {
      skipped += 1;
      continue;
    }
    const color = colors[item.impact] || '#2563eb';
    const top = r.top + window.scrollY;
    const left = r.left + window.scrollX;
    const box = document.createElement('div');
    box.style.cssText = (
      `position:absolute;left:${left}px;top:${top}px;` +
      `width:${Math.max(r.width, 4)}px;height:${Math.max(r.height, 4)}px;` +
      `border:3px solid ${color};background:${color}1a;box-sizing:border-box;pointer-events:none;`
    );
    const badge = document.createElement('div');
    badge.textContent = `#${item.index}`;
    const badgeTop = Math.max(0, top - 20);
    badge.style.cssText = (
      `position:absolute;left:${Math.max(0, left)}px;top:${badgeTop}px;` +
      `background:${color};color:#fff;font:700 11px/1.2 monospace;padding:2px 5px;` +
      `border-radius:3px;white-space:nowrap;pointer-events:none;`
    );
    wrap.appendChild(box);
    wrap.appendChild(badge);
    marked.push({index: item.index, id: item.id, impact: item.impact});
  }

  if (marked.length > 0) {
    const legend = document.createElement('div');
    legend.style.cssText = (
      'position:fixed;top:8px;right:8px;max-width:340px;background:rgba(17,24,39,0.92);' +
      'color:#f9fafb;font:12px/1.35 system-ui,sans-serif;padding:8px 10px;border-radius:6px;' +
      'border:1px solid rgba(255,255,255,0.2);pointer-events:none;z-index:2147483647;'
    );
    const cap = 15;
    const rows = marked.slice(0, cap).map((m) => `#${m.index} ${m.id} (${m.impact || 'n/a'})`);
    if (marked.length > cap) rows.push(`+${marked.length - cap} mais`);
    legend.textContent = rows.join(' | ');
    wrap.appendChild(legend);
  }

  document.documentElement.appendChild(wrap);
  return {marked, skipped};
}
