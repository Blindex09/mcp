(el) => {
  // FATOS de UM elemento para as sondas de contrato (estado ARIA, o que ele controla, onde esta o foco). Nao classifica nada.
  const g = (a) => el.getAttribute(a);
  const root = el.getRootNode();
  const byId = (id) => (id ? (root.getElementById ? root.getElementById(id) : document.getElementById(id)) : null);
  const vis = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const text = (e) => (e ? (e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60) : null);
  const ctrl = byId((g('aria-controls') || '').split(/\s+/)[0]);
  const ad = byId(g('aria-activedescendant'));
  // <summary> de <details>: o estado aberto/fechado e' nativo (details.open), sem atributo aria-expanded; o navegador o expoe ao leitor de tela.
  const det = el.tagName === 'SUMMARY' && el.parentElement && el.parentElement.tagName === 'DETAILS' ? el.parentElement : null;
  let active = document.activeElement;
  while (active && active.shadowRoot && active.shadowRoot.activeElement) active = active.shadowRoot.activeElement;
  return {
    tag: el.tagName.toLowerCase(), role_attr: g('role'), expanded: det ? String(det.open) : g('aria-expanded'), native_disclosure: !!det, selected: g('aria-selected'), checked: g('aria-checked'),
    pressed: g('aria-pressed'), tabindex: g('tabindex'), haspopup: g('aria-haspopup'), invalid: g('aria-invalid'),
    controls: g('aria-controls'), controls_present: !!ctrl || !!det, controls_visible: det ? det.open : vis(ctrl),
    focus_in_controls: ctrl ? ctrl.contains(active) : null,
    activedescendant: ad ? ((ad.id || '') + ' ' + (text(ad) || '')).trim() : null, activedescendant_attr: g('aria-activedescendant'),
    native_popup: !!el.list || el.tagName === 'SELECT',
    value: el.value !== undefined && el.type !== 'password' ? String(el.value).slice(0, 80) : null,
    focused: active === el, text: text(el),
  };
}
