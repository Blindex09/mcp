(scope) => {
  // MAPA DA PAGINA: FATOS de todo o conteudo (nao so o interativo), atravessando Shadow DOM aberto.
  // Nada aqui classifica ou opina: aritmetica sobre o DOM/CSS. O modelo julga (alt faz sentido? hierarquia
  // reflete o visual? ordem de leitura esta certa?).
  const clean = (t) => (t || '').replace(/\s+/g, ' ').trim();
  const rootEl = scope ? document.querySelector(scope) : document.body;
  if (!rootEl) return {error: 'scope nao encontrado: ' + scope};

  // Todas as raizes (documento + shadow roots abertos) e todos os elementos, em ordem de documento.
  const roots = [rootEl]; const all = []; const hosts = [];
  const walk = (node) => {
    for (const el of node.querySelectorAll('*')) {
      all.push(el);
      if (el.shadowRoot) { hosts.push({tag: el.tagName.toLowerCase(), mode: 'open'}); roots.push(el.shadowRoot); walk(el.shadowRoot); }
    }
  };
  walk(rootEl);
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const q = (sel) => all.filter(e => e.matches(sel));
  const tag = (e) => e.tagName.toLowerCase();
  const byId = (e, ids) => (ids || '').split(/\s+/).filter(Boolean).map(i => (e.getRootNode().getElementById ? e.getRootNode().getElementById(i) : document.getElementById(i))).filter(Boolean);
  const nameOf = (e) => e.getAttribute('aria-label') || clean(byId(e, e.getAttribute('aria-labelledby')).map(x => x.textContent).join(' ')) || null;
  const rectOf = (e) => { const r = e.getBoundingClientRect(); return {x: Math.round(r.x), y: Math.round(r.y + window.scrollY), w: Math.round(r.width), h: Math.round(r.height)}; };
  const cap = (arr, n) => ({total: arr.length, items: arr.slice(0, n)});
  const LANDMARK = '[role=banner],[role=navigation],[role=main],[role=contentinfo],[role=complementary],[role=search],[role=form],[role=region],header,nav,main,footer,aside,search,form,section[aria-label],section[aria-labelledby]';
  const insideLandmark = (e) => !!e.closest(LANDMARK);

  // --- documento
  const doc = {lang: document.documentElement.getAttribute('lang'), title: document.title, dir: document.documentElement.getAttribute('dir'),
    viewport_meta: (document.querySelector('meta[name=viewport]') || {}).content || null, elements: all.length,
    shadow_hosts_open: hosts.length, parts_with_other_lang: q('[lang]').filter(e => e !== document.documentElement).length};

  // --- titulos (na ordem do documento) e saltos de nivel (aritmetica sobre a sequencia)
  const hs = q('h1,h2,h3,h4,h5,h6,[role=heading]').map(e => ({level: e.getAttribute('aria-level') ? +e.getAttribute('aria-level') : (/^h[1-6]$/.test(tag(e)) ? +tag(e)[1] : null),
    text: clean(e.textContent).slice(0, 80), visible: visible(e), in_landmark: insideLandmark(e), size: getComputedStyle(e).fontSize}));
  const jumps = []; let prev = null;
  for (const h of hs) { if (h.level && prev && h.level > prev + 1) jumps.push({from: prev, to: h.level, text: h.text}); if (h.level) prev = h.level; }
  const headings = {total: hs.length, h1_count: hs.filter(h => h.level === 1).length, first_level: hs.length ? hs[0].level : null, level_jumps: jumps, outline: hs.slice(0, 80)};

  // --- landmarks
  const lms = q(LANDMARK).map(e => ({role: e.getAttribute('role') || tag(e), name: nameOf(e), tag: tag(e)}));
  const counts = {}; lms.forEach(l => { const k = l.role + '|' + (l.name || ''); counts[k] = (counts[k] || 0) + 1; });
  const landmarks = {total: lms.length, items: lms.slice(0, 40), repeated_without_distinct_name: Object.entries(counts).filter(([, n]) => n > 1).map(([k, n]) => ({role_and_name: k, count: n}))};
  let textAll = 0, textOut = 0;
  for (const el of all) { for (const n of el.childNodes) if (n.nodeType === 3) { const l = clean(n.textContent).length; if (l && visible(el)) { textAll += l; if (!insideLandmark(el)) textOut += l; } } }
  landmarks.text_chars_total = textAll; landmarks.text_chars_outside_landmarks = textOut;

  // --- imagens e graficos
  const imgEls = q('img,svg,canvas,picture,[role=img],input[type=image],area').filter(e => !e.closest('svg') || tag(e) === 'svg');
  const images = cap(imgEls.map(e => ({tag: tag(e), role: e.getAttribute('role'),
    alt: e.hasAttribute('alt') ? e.getAttribute('alt') : null, aria_label: e.getAttribute('aria-label'), aria_hidden: e.getAttribute('aria-hidden'),
    title_attr: tag(e) === 'svg' ? clean((e.querySelector('title') || {}).textContent || '') || null : e.getAttribute('title'),
    src: (e.currentSrc || e.getAttribute('src') || '').split('/').pop().slice(0, 50) || null, natural: e.naturalWidth ? [e.naturalWidth, e.naturalHeight] : null,
    in_link_or_button: !!e.closest('a,button'), figcaption: !!(e.closest('figure') && e.closest('figure').querySelector('figcaption')), visible: visible(e), rect: rectOf(e)})), 80);

  // --- links
  const links = q('a[href]').map(e => ({text: clean(e.textContent).slice(0, 60), aria_label: e.getAttribute('aria-label'), href: (e.getAttribute('href') || '').slice(0, 80),
    target: e.getAttribute('target'), rel: e.getAttribute('rel'), has_img_only: !clean(e.textContent) && !!e.querySelector('img,svg'), visible: visible(e)}));
  const byText = {}; links.forEach(l => { const k = (l.aria_label || l.text).toLowerCase(); if (k) (byText[k] = byText[k] || new Set()).add(l.href); });
  const dupText = Object.entries(byText).filter(([, s]) => s.size > 1).map(([text, s]) => ({text, distinct_destinations: s.size}));
  const linkInfo = {total: links.length, items: links.slice(0, 60), same_text_different_destination: dupText.slice(0, 20), empty_text: links.filter(l => !l.text && !l.aria_label).length};

  // --- formularios e campos
  const fieldOf = (e) => ({tag: tag(e), type: e.getAttribute('type'), name: e.getAttribute('name'), id: e.id || null,
    label: e.labels && e.labels.length ? clean(Array.from(e.labels).map(l => l.textContent).join(' ')).slice(0, 60) : null,
    aria_label: e.getAttribute('aria-label'), labelledby: clean(byId(e, e.getAttribute('aria-labelledby')).map(x => x.textContent).join(' ')) || null,
    placeholder: e.getAttribute('placeholder'), autocomplete: e.getAttribute('autocomplete'), required: e.required === true || e.getAttribute('aria-required') === 'true',
    invalid: e.getAttribute('aria-invalid'), describedby: clean(byId(e, e.getAttribute('aria-describedby')).map(x => x.textContent).join(' ')).slice(0, 80) || null,
    fieldset_legend: e.closest('fieldset') && e.closest('fieldset').querySelector('legend') ? clean(e.closest('fieldset').querySelector('legend').textContent) : null});
  const fieldSel = 'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]),select,textarea';
  const forms = q('form,[role=form]').map(f => ({name: nameOf(f) || f.id || null, method: f.getAttribute('method'), fields: Array.from(f.querySelectorAll(fieldSel)).map(fieldOf).slice(0, 30)}));
  const outside = q(fieldSel).filter(e => !e.closest('form,[role=form]')).map(fieldOf);
  const formInfo = {forms: forms.slice(0, 12), fields_outside_forms: outside.slice(0, 30), fields_total: q(fieldSel).length,
    fields_without_any_name: q(fieldSel).map(fieldOf).filter(f => !f.label && !f.aria_label && !f.labelledby).length};

  // --- tabelas
  const tables = cap(q('table').map(t => ({caption: t.caption ? clean(t.caption.textContent).slice(0, 60) : null, aria_label: nameOf(t), role: t.getAttribute('role'),
    rows: t.rows.length, header_cells: t.querySelectorAll('th').length, scoped_headers: t.querySelectorAll('th[scope]').length, has_thead: !!t.tHead,
    cols: t.rows[0] ? t.rows[0].cells.length : 0, nested_tables: t.querySelectorAll('table').length, visible: visible(t)})), 20);

  // --- listas
  const lists = {ul: q('ul').length, ol: q('ol').length, dl: q('dl').length, role_list: q('[role=list]').length};

  // --- midia
  const media = q('video,audio').map(m => ({tag: tag(m), controls: m.controls, autoplay: m.autoplay, muted: m.muted, loop: m.loop,
    tracks: Array.from(m.querySelectorAll('track')).map(t => ({kind: t.kind, srclang: t.srclang, label: t.label})), duration: isFinite(m.duration) ? Math.round(m.duration) : null, aria_label: nameOf(m)}));

  // --- iframes
  const iframes = q('iframe,frame').map(f => ({src: (f.getAttribute('src') || (f.hasAttribute('srcdoc') ? 'srcdoc' : '')).slice(0, 80), title: f.getAttribute('title'), name: f.getAttribute('name'),
    sandbox: f.getAttribute('sandbox'), loading: f.getAttribute('loading'), rect: rectOf(f), visible: visible(f)}));

  // --- regioes vivas
  const live = q('[aria-live]:not([aria-live=off]),[role=alert],[role=status],[role=log],[role=alertdialog]').map(e => ({role: e.getAttribute('role'), live: e.getAttribute('aria-live'), atomic: e.getAttribute('aria-atomic'), text_length: clean(e.textContent).length}));

  // --- ordem de leitura x ordem visual: inversoes EXATAS entre pares (aritmetica; sem limiar nem lista de tags)
  const ownText = (e) => Array.from(e.childNodes).some(n => n.nodeType === 3 && clean(n.textContent));
  const flow = all.filter(e => visible(e) && (ownText(e) || e.matches('img,input,select,textarea,button,a[href],[role=button],[role=img]'))).slice(0, 400);
  const rtl = (document.documentElement.getAttribute('dir') || getComputedStyle(document.body).direction) === 'rtl';
  const visualSorted = flow.map((e, i) => ({e, i, r: e.getBoundingClientRect()})).sort((a, b) => {
    const ya = Math.round((a.r.top + scrollY) / 8), yb = Math.round((b.r.top + scrollY) / 8);
    return ya !== yb ? ya - yb : (rtl ? b.r.left - a.r.left : a.r.left - b.r.left); });
  const rank = new Array(flow.length); visualSorted.forEach((x, vi) => { rank[x.i] = vi; });
  let inversions = 0; const adjacent = [];
  for (let i = 0; i < flow.length; i++) for (let j = i + 1; j < flow.length; j++) if (rank[i] > rank[j]) { inversions++; if (j === i + 1 && adjacent.length < 8) adjacent.push({first_in_dom: clean(flow[i].textContent || flow[i].getAttribute('alt') || '').slice(0, 40), appears_visually_first: clean(flow[j].textContent || flow[j].getAttribute('alt') || '').slice(0, 40)}); }
  const pairs = flow.length * (flow.length - 1) / 2;
  const reading = {items_compared: flow.length, inverted_pairs: inversions, inverted_ratio: pairs ? +(inversions / pairs).toFixed(4) : 0, adjacent_inversions_examples: adjacent,
    tabindex_positive: q('[tabindex]').filter(e => +e.getAttribute('tabindex') > 0).length, css_order_used: all.filter(e => { const o = getComputedStyle(e).order; return o && o !== '0'; }).length};

  // --- regras :hover que revelam conteudo (dados das folhas de estilo; so leitura)
  const hover = [];
  const scan = (rules) => { for (const r of Array.from(rules || [])) {
    if (r.cssRules && !r.selectorText) scan(r.cssRules);
    if (!r.selectorText || !r.selectorText.includes(':hover')) continue;
    const st = r.style; const touches = ['display', 'visibility', 'opacity', 'height', 'max-height', 'transform', 'clip'].filter(p => st.getPropertyValue(p));
    if (!touches.length) continue;
    const base = r.selectorText.split(',')[0].replace(/:hover/g, '');
    let n = 0; try { n = document.querySelectorAll(base).length; } catch (e) {}
    const trigger = r.selectorText.split(',')[0].split(':hover')[0];
    let trigCount = 0; try { trigCount = document.querySelectorAll(trigger).length; } catch (e) {}
    hover.push({rule: r.selectorText.slice(0, 80), changes: touches, trigger_selector: trigger.slice(0, 60), triggers_in_page: trigCount, targets_in_page: n});
  } };
  try { for (const sheet of Array.from(document.styleSheets)) { try { scan(sheet.cssRules); } catch (e) {} } } catch (e) {}
  const hoverRules = {total: hover.length, items: hover.slice(0, 20), note: 'regras CSS :hover que mudam exibicao/visibilidade; o gatilho pode nao ser focavel nem ter listener'};

  return {url: location.href, document: doc, headings, landmarks, images, links: linkInfo, forms: formInfo, tables, lists, media, iframes, live_regions: live, reading_order: reading, hover_reveals: hoverRules};
}
