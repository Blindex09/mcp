function (scope) {
  // Dossie de UM elemento (this): FATOS. Funciona dentro de Shadow DOM (aberto ou fechado, via CDP) e de iframes,
  // porque a raiz e o documento do proprio elemento. Nao classifica nada.
  const el = this;
  if (!el || el.nodeType !== 1) return null;
  if (scope && !(el.closest && el.closest(scope))) return null;
  const clean = (t) => (t || '').replace(/\s+/g, ' ').trim();
  const doc = el.ownerDocument; const root = el.getRootNode();
  const visible = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const effBg = (e) => {
    for (let n = e; n; n = n.parentElement || (n.getRootNode() && n.getRootNode().host)) {
      const c = getComputedStyle(n).backgroundColor;
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (m) { const p = m[1].split(',').map(x => parseFloat(x)); if (p.length < 4 || p[3] > 0) return c; }
    }
    return 'rgb(255, 255, 255)';
  };
  const byIds = (ids) => (ids || '').split(/\s+/).filter(Boolean).map(i => (root.getElementById ? root.getElementById(i) : doc.getElementById(i))).filter(Boolean);
  const textOf = (els) => clean(els.map(e => e.innerText || e.textContent).join(' ')).slice(0, 120);
  const landmarkOf = (e) => {
    const m = e.closest('[role=navigation],[role=main],[role=banner],[role=contentinfo],[role=search],[role=complementary],[role=form],[role=region],nav,main,header,footer,aside,form,search');
    return m ? (m.getAttribute('role') || m.tagName.toLowerCase()) : null;
  };
  const headingOf = (e) => {
    let best = null;
    for (const h of (root.querySelectorAll ? root : doc).querySelectorAll('h1,h2,h3,h4,h5,h6,[role=heading]')) {
      if (h.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING) best = h; else break;
    }
    return best ? clean(best.innerText).slice(0, 60) : null;
  };
  // Regras :hover das folhas de estilo cujo gatilho e' este elemento (dado das folhas; so leitura).
  const hoverRules = () => {
    if (doc.__a11yHoverRules) return doc.__a11yHoverRules;
    const out = [];
    const scan = (rules) => { for (const r of Array.from(rules || [])) {
      if (r.cssRules && !r.selectorText) scan(r.cssRules);
      if (!r.selectorText || !r.selectorText.includes(':hover')) continue;
      if (!['display', 'visibility', 'opacity', 'height', 'max-height', 'transform', 'clip'].some(p => r.style.getPropertyValue(p))) continue;
      const trig = r.selectorText.split(',')[0].split(':hover')[0].trim();
      if (trig) out.push({trigger: trig, rule: r.selectorText.slice(0, 80)});
    } };
    for (const sh of Array.from(doc.styleSheets)) { try { scan(sh.cssRules); } catch (e) {} }
    return (doc.__a11yHoverRules = out);
  };
  const g = (a) => el.getAttribute(a);
  const controlled = byIds(g('aria-controls') || g('aria-owns'));
  const pop = controlled[0];
  const popItems = pop ? Array.from(pop.querySelectorAll('[role],a,button,li,option')) : [];
  const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
  const isPw = el.tagName === 'INPUT' && el.type === 'password';
  let hover = null; for (const h of hoverRules()) { try { if (el.matches(h.trigger)) { hover = h.rule; break; } } catch (e) {} }
  const listeners = el.__a11yL ? Array.from(el.__a11yL) : [];
  const handlerProps = ['onclick', 'onmousedown', 'onmouseup', 'onpointerdown', 'ontouchstart', 'onkeydown'].filter(p => typeof el[p] === 'function');
  return {
    id: g('data-a11y-id'), tag: el.tagName.toLowerCase(), type: g('type'), role_attr: g('role'),
    where: {frame_url: (doc.URL || '').slice(0, 80), in_shadow: root instanceof ShadowRoot, shadow_host: root instanceof ShadowRoot ? root.host.tagName.toLowerCase() : null},
    attrs: {aria_label: g('aria-label'), labelledby: textOf(byIds(g('aria-labelledby'))) || null,
      label: el.labels && el.labels.length ? textOf(Array.from(el.labels)) : null, placeholder: g('placeholder'), title: g('title'), alt: g('alt')},
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
    behavior_hints: {click_listeners: listeners, handler_properties: handlerProps, hover_reveals_rule: hover},
    context: {landmark: landmarkOf(el), heading: headingOf(el), form: el.form ? (el.form.getAttribute('aria-label') || el.form.id || 'form') : null,
      ancestors: (() => { const a = []; for (let p = el.parentElement; p && p !== doc.body && a.length < 4; p = p.parentElement) a.push(p.tagName.toLowerCase() + (p.getAttribute('role') ? '[' + p.getAttribute('role') + ']' : '')); return a; })()},
    tabindex: g('tabindex'), rect: {x: Math.round(r.x), y: Math.round(r.y + window.scrollY), w: Math.round(r.width), h: Math.round(r.height)},
    style: {font: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(), size: cs.fontSize, weight: cs.fontWeight, line_height: cs.lineHeight,
      letter_spacing: cs.letterSpacing, color: cs.color, background: effBg(el), radius: cs.borderRadius, padding: cs.padding, cursor: cs.cursor},
  };
}
