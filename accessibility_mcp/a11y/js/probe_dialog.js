(sel) => {
  // Acha o dialogo ABERTO (papel dialog/alertdialog ou <dialog open>, definicoes do ARIA/HTML) e marca-o para as sondas.
  const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  document.querySelectorAll('[data-a11y-probe-dialog]').forEach((e) => e.removeAttribute('data-a11y-probe-dialog'));
  const all = Array.from(document.querySelectorAll(sel || 'dialog[open],[role=dialog],[role=alertdialog]'));
  const shown = all.filter(vis);
  let active = document.activeElement;
  while (active && active.shadowRoot && active.shadowRoot.activeElement) active = active.shadowRoot.activeElement;
  const c = shown.find((e) => e.contains(active)) || shown[shown.length - 1] || null;
  if (!c) return {found: false, candidates: all.length};
  c.setAttribute('data-a11y-probe-dialog', '1');
  let modal = null; try { modal = c.matches(':modal'); } catch (e) { modal = null; }
  const lab = (c.getAttribute('aria-labelledby') || '').split(/\s+/).map((i) => document.getElementById(i)).filter(Boolean).map((e) => e.textContent.trim()).join(' ');
  return {found: true, tag: c.tagName.toLowerCase(), role_attr: c.getAttribute('role'), aria_modal: c.getAttribute('aria-modal'), native_modal: modal,
    label: c.getAttribute('aria-label') || lab || null, focus_inside: c.contains(active), visible: true};
}
