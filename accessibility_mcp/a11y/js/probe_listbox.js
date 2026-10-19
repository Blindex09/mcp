(el) => {
  // FATOS de um listbox (role=listbox ou select): nome, opcoes, quem esta na ordem de Tab, quem tem o foco ou e' o aria-activedescendant.
  const box = el.closest('[role=listbox]') || el;
  const opts = Array.from(box.querySelectorAll('[role=option]'));
  const root = box.getRootNode();
  const byId = (id) => (id ? (root.getElementById ? root.getElementById(id) : document.getElementById(id)) : null);
  let active = document.activeElement;
  while (active && active.shadowRoot && active.shadowRoot.activeElement) active = active.shadowRoot.activeElement;
  const labelledby = (box.getAttribute('aria-labelledby') || '').split(/\s+/).map((i) => byId(i)).filter(Boolean).map((e) => (e.textContent || '').trim()).join(' ');
  const text = (e) => (e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40);
  return {
    listbox: box.getAttribute('role') === 'listbox', tag: box.tagName.toLowerCase(),
    name: (box.getAttribute('aria-label') || labelledby || '').trim(), multiselectable: box.getAttribute('aria-multiselectable'),
    box_tabbable: box.tabIndex >= 0, box_focused: box === active, activedescendant: box.getAttribute('aria-activedescendant'),
    options: opts.map((o, i) => ({index: i, id: o.id || null, text: text(o), selected: o.getAttribute('aria-selected'), focused: o === active, tabbable: o.tabIndex >= 0})),
  };
}
