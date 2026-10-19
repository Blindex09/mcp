(el) => {
  // FATOS de uma arvore (role=tree): itens visiveis, nivel, estado aberto/fechado, quem esta na ordem de Tab e quem tem o foco.
  const tree = el.closest('[role=tree]');
  let active = document.activeElement;
  while (active && active.shadowRoot && active.shadowRoot.activeElement) active = active.shadowRoot.activeElement;
  if (!tree) return {tree: false, items: []};
  const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const all = Array.from(tree.querySelectorAll('[role=treeitem]'));
  const labelledby = (tree.getAttribute('aria-labelledby') || '').split(/\s+/).map((i) => document.getElementById(i)).filter(Boolean).map((e) => (e.textContent || '').trim()).join(' ');
  return {
    tree: true, name: (tree.getAttribute('aria-label') || labelledby || '').trim(), tree_tabbable: tree.tabIndex >= 0, activedescendant: tree.getAttribute('aria-activedescendant'),
    items: all.filter(vis).map((t, i) => ({
      index: i, id: t.id || null, text: (t.firstChild && t.firstChild.nodeType === 3 ? t.firstChild.textContent : (t.innerText || '')).replace(/\s+/g, ' ').trim().slice(0, 30),
      level: t.getAttribute('aria-level'), expanded: t.getAttribute('aria-expanded'), has_group: !!t.querySelector(':scope > [role=group]'),
      tabbable: t.tabIndex >= 0, focused: t === active,
    })),
    total_items: all.length,
  };
}
