(args) => {
  // Descreve (FATOS) os elementos que o NAVEGADOR apontou como focaveis ou clicaveis.
  // Nao decide o que e interativo: a descoberta vem do Chromium (arvore de acessibilidade + DOMSnapshot).
  const max = args.max || 60;
  const root = args.scope ? document.querySelector(args.scope) : document.body;
  if (!root) return {error: 'scope nao encontrado: ' + args.scope};
  const clean = (t) => (t || '').replace(/\s+/g, ' ').trim();
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const effBg = (el) => {
    for (let n = el; n; n = n.parentElement) {
      const c = getComputedStyle(n).backgroundColor;
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (m) { const p = m[1].split(',').map(x => parseFloat(x)); if (p.length < 4 || p[3] > 0) return c; }
    }
    return 'rgb(255, 255, 255)';
  };
  const byIds = (ids) => (ids || '').split(/\s+/).filter(Boolean).map(i => document.getElementById(i)).filter(Boolean);
  const textOf = (els) => clean(els.map(e => e.innerText || e.textContent).join(' ')).slice(0, 120);
  const landmarkOf = (el) => {
    const m = el.closest('[role=navigation],[role=main],[role=banner],[role=contentinfo],[role=search],[role=complementary],[role=form],[role=region],nav,main,header,footer,aside,form,search');
    return m ? (m.getAttribute('role') || m.tagName.toLowerCase()) : null;
  };
  const headingOf = (el) => {
    let best = null;
    for (const h of document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role=heading]')) {
      if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) best = h; else break;
    }
    return best ? clean(best.innerText).slice(0, 60) : null;
  };
  const out = []; let skippedByScope = 0; let overLimit = 0;
  for (const id of args.ids) {
    const el = document.querySelector('[data-a11y-id="' + id + '"]');
    if (!el || !root.contains(el)) { skippedByScope++; continue; }
    if (out.length >= max) { overLimit++; continue; }
    const g = (a) => el.getAttribute(a);
    const controlled = byIds(g('aria-controls') || g('aria-owns'));
    const pop = controlled[0];
    const popItems = pop ? Array.from(pop.querySelectorAll('[role],a,button,li,option')) : [];
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    const isPw = el.tagName === 'INPUT' && el.type === 'password';
    out.push({
      id: id, tag: el.tagName.toLowerCase(), type: g('type'), role_attr: g('role'),
      attrs: {aria_label: g('aria-label'), labelledby: textOf(byIds(g('aria-labelledby'))) || null,
        label: el.labels && el.labels.length ? textOf(Array.from(el.labels)) : null,
        placeholder: g('placeholder'), title: g('title'), alt: g('alt')},
      text: clean(el.innerText).slice(0, 80) || null,
      icon_only: !clean(el.innerText) && !!el.querySelector('svg,img,i'),
      value_length: (el.value !== undefined && !isPw) ? String(el.value).length : null,
      states: {disabled: el.disabled === true || g('aria-disabled') === 'true', required: el.required === true || g('aria-required') === 'true',
        readonly: el.readOnly === true, checked: el.checked === true ? true : g('aria-checked'),
        expanded: g('aria-expanded'), haspopup: g('aria-haspopup'), selected: g('aria-selected'), pressed: g('aria-pressed'),
        current: g('aria-current'), invalid: g('aria-invalid'), autocomplete: g('aria-autocomplete') || g('autocomplete'),
        modal: g('aria-modal'), multiselectable: g('aria-multiselectable')},
      relations: {controls: g('aria-controls'), owns: g('aria-owns'), describedby: textOf(byIds(g('aria-describedby'))) || null,
        datalist_options: el.list ? el.list.options.length : null, native_options: el.tagName === 'SELECT' ? el.options.length : null,
        popup_items: pop ? popItems.length : null,
        popup_item_kinds: pop ? Array.from(new Set(popItems.map(i => i.getAttribute('role') || i.tagName.toLowerCase()))).slice(0, 6) : null,
        popup_links: pop ? pop.querySelectorAll('a[href]').length : null, popup_visible: pop ? visible(pop) : null},
      context: {landmark: landmarkOf(el), heading: headingOf(el),
        form: el.form ? (el.form.getAttribute('aria-label') || el.form.id || 'form') : null,
        ancestors: (() => { const a = []; for (let p = el.parentElement; p && p !== document.body && a.length < 4; p = p.parentElement) a.push(p.tagName.toLowerCase() + (p.getAttribute('role') ? '[' + p.getAttribute('role') + ']' : '')); return a; })()},
      tabindex: g('tabindex'), rect: {x: Math.round(r.x), y: Math.round(r.y + window.scrollY), w: Math.round(r.width), h: Math.round(r.height)},
      style: {font: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(), size: cs.fontSize, weight: cs.fontWeight, line_height: cs.lineHeight,
        letter_spacing: cs.letterSpacing, color: cs.color, background: effBg(el), radius: cs.borderRadius, padding: cs.padding, cursor: cs.cursor},
    });
  }
  return {url: location.href, title: document.title, elements: out, not_in_scope: skippedByScope, not_listed_over_limit: overLimit};
}
