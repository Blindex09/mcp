"""Scripts que rodam DENTRO da pagina para coletar FATOS (nunca classificam).

Quem decide "isso e uma combobox / um menu / um acordeao" e o modelo, lendo estes fatos junto
com o comportamento observado. Nada aqui usa palavra-chave para adivinhar categoria.
"""

# Instalado a cada documento novo: registra o texto que entra em regioes vivas (o que um
# leitor de tela anunciaria) para que as acoes possam devolver "o que foi anunciado".
LIVE_OBSERVER_JS = """
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
"""

# Descritor curto do elemento em foco (usado nos relatorios de efeito).
FOCUS_JS = """
() => {
  const e = document.activeElement;
  if (!e || e === document.body || e === document.documentElement) return null;
  const name = (e.getAttribute('aria-label') || (e.labels && e.labels[0] && e.labels[0].innerText)
    || e.innerText || e.getAttribute('title') || e.getAttribute('alt') || e.getAttribute('placeholder') || '')
    .trim().replace(/\\s+/g, ' ').slice(0, 80);
  const cs = getComputedStyle(e);
  return {
    id: e.getAttribute('data-a11y-id'), tag: e.tagName.toLowerCase(), role: e.getAttribute('role'),
    name: name, type: e.getAttribute('type'),
    focus_indicator: (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== 'none',
  };
}
"""

# Dossie: inventario de fatos dos elementos interativos / com cara de widget.
DOSSIER_JS = """
(args) => {
  const max = args.max || 60;
  const root = args.scope ? document.querySelector(args.scope) : document.body;
  if (!root) return {error: 'scope nao encontrado: ' + args.scope};
  const SEL = 'a[href],button,input,select,textarea,summary,details,dialog,[role],[tabindex],' +
    '[contenteditable],[aria-haspopup],[aria-expanded],[aria-controls],[onclick],[draggable=true]';
  const visible = (el) => {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
  };
  const clean = (t) => (t || '').replace(/\\s+/g, ' ').trim();
  const cands = new Set(root.querySelectorAll(SEL));
  root.querySelectorAll('div,span,li,img,svg').forEach(el => {
    if (!cands.has(el) && getComputedStyle(el).cursor === 'pointer' && !el.closest('a[href],button')) cands.add(el);
  });
  const effBg = (el) => {
    for (let n = el; n; n = n.parentElement) {
      const c = getComputedStyle(n).backgroundColor;
      const m = c.match(/rgba?\\(([^)]+)\\)/);
      if (m) { const p = m[1].split(',').map(x => parseFloat(x)); if (p.length < 4 || p[3] > 0) return c; }
    }
    return 'rgb(255, 255, 255)';
  };
  const byIds = (ids) => (ids || '').split(/\\s+/).filter(Boolean).map(i => document.getElementById(i)).filter(Boolean);
  const textOf = (els) => clean(els.map(e => e.innerText || e.textContent).join(' ')).slice(0, 120);
  const landmarkOf = (el) => {
    const m = el.closest('[role=navigation],[role=main],[role=banner],[role=contentinfo],[role=search],[role=complementary],[role=form],nav,main,header,footer,aside,form,search');
    return m ? (m.getAttribute('role') || m.tagName.toLowerCase()) : null;
  };
  const headingOf = (el) => {
    const hs = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role=heading]'));
    let best = null;
    for (const h of hs) { if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) best = h; else break; }
    return best ? clean(best.innerText).slice(0, 60) : null;
  };
  const list = []; let hidden = 0; let n = 0;
  for (const el of cands) {
    if (!visible(el)) { hidden++; continue; }
    if (list.length >= max) { n++; continue; }
    if (!el.getAttribute('data-a11y-id')) el.setAttribute('data-a11y-id', 'e' + (window.__a11yNext = (window.__a11yNext || 0) + 1));
    const g = (a) => el.getAttribute(a);
    const controlled = byIds(g('aria-controls') || g('aria-owns'));
    const pop = controlled[0];
    const popItems = pop ? Array.from(pop.querySelectorAll('[role],a,button,li,option')) : [];
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    const isPw = el.tagName === 'INPUT' && el.type === 'password';
    list.push({
      id: g('data-a11y-id'), tag: el.tagName.toLowerCase(), type: g('type'), role_attr: g('role'),
      name_sources: {
        aria_label: g('aria-label'), labelledby: textOf(byIds(g('aria-labelledby'))) || null,
        label: el.labels && el.labels.length ? textOf(Array.from(el.labels)) : null,
        placeholder: g('placeholder'), title: g('title'), alt: g('alt'),
      },
      text: clean(el.innerText).slice(0, 80) || null,
      icon_only: !clean(el.innerText) && !!el.querySelector('svg,img,i'),
      value_length: (el.value !== undefined && !isPw) ? String(el.value).length : null,
      states: {
        disabled: el.disabled === true || g('aria-disabled') === 'true', required: el.required === true || g('aria-required') === 'true',
        readonly: el.readOnly === true, checked: el.checked === true ? true : g('aria-checked'),
        expanded: g('aria-expanded'), haspopup: g('aria-haspopup'), selected: g('aria-selected'), pressed: g('aria-pressed'),
        current: g('aria-current'), invalid: g('aria-invalid'), autocomplete: g('aria-autocomplete') || g('autocomplete'),
        modal: g('aria-modal'), multiselectable: g('aria-multiselectable'),
      },
      editable: el.isContentEditable || (el.tagName === 'INPUT' && !['button','submit','reset','checkbox','radio','range','color','file','image'].includes(el.type)) || el.tagName === 'TEXTAREA',
      relations: {
        controls: g('aria-controls'), owns: g('aria-owns'), describedby: textOf(byIds(g('aria-describedby'))) || null,
        datalist_options: el.list ? el.list.options.length : null,
        native_options: el.tagName === 'SELECT' ? el.options.length : null,
        popup_items: pop ? popItems.length : null,
        popup_item_kinds: pop ? Array.from(new Set(popItems.map(i => i.getAttribute('role') || i.tagName.toLowerCase()))).slice(0, 6) : null,
        popup_links: pop ? pop.querySelectorAll('a[href]').length : null,
        popup_visible: pop ? visible(pop) : null,
      },
      context: {landmark: landmarkOf(el), heading: headingOf(el), form: el.form ? (el.form.getAttribute('aria-label') || el.form.id || 'form') : null,
        ancestors: (() => { const a = []; for (let p = el.parentElement; p && p !== document.body && a.length < 4; p = p.parentElement) a.push(p.tagName.toLowerCase() + (p.getAttribute('role') ? '[' + p.getAttribute('role') + ']' : '')); return a; })()},
      focusable: el.tabIndex >= 0, tabindex: g('tabindex'),
      rect: {x: Math.round(r.x), y: Math.round(r.y + window.scrollY), w: Math.round(r.width), h: Math.round(r.height)},
      style: {font: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(), size: cs.fontSize, weight: cs.fontWeight, line_height: cs.lineHeight,
        letter_spacing: cs.letterSpacing, color: cs.color, background: effBg(el), radius: cs.borderRadius, padding: cs.padding, cursor: cs.cursor},
    });
  }
  return {url: location.href, title: document.title, count: list.length, not_listed_over_limit: n, hidden_interactive: hidden, elements: list};
}
"""

# Linguagem de design do site: o que ele REALMENTE usa (contagens), para a critica se apoiar nisso.
DESIGN_JS = """
() => {
  const tally = (m, k) => { m[k] = (m[k] || 0) + 1; };
  const top = (m, n) => Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, n).map(([value, count]) => ({value, count}));
  const type = {}, samples = {}, fonts = {}, sizes = {}, weights = {}, colors = {}, bgs = {}, radii = {}, gaps = {}, shadows = {};
  const els = Array.from(document.querySelectorAll('body *')).slice(0, 4000);
  let seen = 0;
  for (const el of els) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (!(r.width > 0 && r.height > 0) || cs.display === 'none' || cs.visibility === 'hidden') continue;
    seen++;
    const hasText = Array.from(el.childNodes).some(c => c.nodeType === 3 && c.textContent.trim());
    if (hasText) {
      const font = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
      const lh = cs.lineHeight === 'normal' ? 'normal' : (parseFloat(cs.lineHeight) / parseFloat(cs.fontSize)).toFixed(2);
      const key = [font, cs.fontSize, cs.fontWeight, lh, cs.letterSpacing].join(' | ');
      tally(type, key); tally(fonts, font); tally(sizes, cs.fontSize); tally(weights, cs.fontWeight); tally(colors, cs.color);
      if (!samples[key]) samples[key] = el.tagName.toLowerCase() + ': ' + (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40);
    }
    const bg = cs.backgroundColor; if (bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') tally(bgs, bg);
    if (cs.borderRadius !== '0px') tally(radii, cs.borderRadius);
    if (cs.boxShadow !== 'none') tally(shadows, cs.boxShadow.slice(0, 60));
    for (const p of ['paddingTop', 'paddingLeft', 'marginTop', 'marginBottom', 'rowGap', 'columnGap']) {
      const v = cs[p]; if (v && v !== '0px' && v !== 'normal' && !v.startsWith('-')) tally(gaps, v);
    }
  }
  const vars = {};
  try {
    for (const sheet of Array.from(document.styleSheets)) {
      let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
      for (const rule of Array.from(rules || [])) {
        if (rule.selectorText && rule.selectorText.includes(':root')) {
          for (const name of Array.from(rule.style)) if (name.startsWith('--')) vars[name] = rule.style.getPropertyValue(name).trim();
        }
      }
    }
  } catch (e) {}
  const body = getComputedStyle(document.body); const html = getComputedStyle(document.documentElement);
  const paras = Array.from(document.querySelectorAll('p')).slice(0, 30).map(p => Math.round(p.getBoundingClientRect().width)).filter(w => w > 0);
  return {
    url: location.href, elements_measured: seen,
    base: {html_font_size: html.fontSize, body_font: body.fontFamily.split(',')[0].replace(/["']/g, '').trim(), body_size: body.fontSize,
      body_line_height: body.lineHeight, body_color: body.color, body_background: body.backgroundColor},
    type_styles: top(type, 14).map(t => ({style: t.value, count: t.count, example: samples[t.value]})),
    font_families: top(fonts, 6), font_sizes: top(sizes, 12), font_weights: top(weights, 6),
    text_colors: top(colors, 10), background_colors: top(bgs, 10),
    spacing_values: top(gaps, 14), border_radii: top(radii, 8), shadows: top(shadows, 5),
    css_variables: vars, paragraph_widths_px: paras.slice(0, 10),
  };
}
"""

# Estresse: reflow em 320 px de largura (WCAG 1.4.10).
REFLOW_JS = """
(width) => {
  const de = document.documentElement;
  const over = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (r.width > 0 && cs.display !== 'none' && r.right > width + 1) {
      over.push({tag: el.tagName.toLowerCase(), id: el.getAttribute('data-a11y-id'), text: (el.innerText || '').trim().slice(0, 40), right: Math.round(r.right), width: Math.round(r.width)});
    }
  }
  return {viewport_width: width, document_scroll_width: de.scrollWidth, horizontal_scroll: de.scrollWidth > width + 1, overflowing_elements: over.slice(0, 15), overflowing_total: over.length};
}
"""

# Estresse: espacamento de texto do usuario (WCAG 1.4.12) - texto cortado/sobreposto.
CLIPPED_JS = """
() => {
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || cs.display === 'none') continue;
    const clips = ['hidden', 'clip', 'auto', 'scroll'].includes(cs.overflowY) || ['hidden', 'clip'].includes(cs.overflowX);
    const hasText = Array.from(el.childNodes).some(c => c.nodeType === 3 && c.textContent.trim());
    if (clips && hasText && (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1)) {
      out.push({tag: el.tagName.toLowerCase(), id: el.getAttribute('data-a11y-id'), text: (el.innerText || '').trim().slice(0, 50),
        client: el.clientWidth + 'x' + el.clientHeight, scroll: el.scrollWidth + 'x' + el.scrollHeight});
    }
  }
  return out;
}
"""
