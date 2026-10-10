(el) => {
  // As abas do mesmo tablist do elemento: estado e tabindex de cada uma. tablist = definicao do ARIA (role=tablist).
  const list = el.closest('[role=tablist]');
  const tabs = list ? Array.from(list.querySelectorAll('[role=tab]')) : [];
  let active = document.activeElement;
  while (active && active.shadowRoot && active.shadowRoot.activeElement) active = active.shadowRoot.activeElement;
  return {tablist: !!list, orientation: list ? list.getAttribute('aria-orientation') : null, tabs: tabs.map((t, i) => ({
    index: i, text: (t.innerText || t.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 30), selected: t.getAttribute('aria-selected'),
    tabindex: t.getAttribute('tabindex'), tabbable: t.tabIndex >= 0, controls: t.getAttribute('aria-controls'), focused: t === active, self: t === el}))};
}
