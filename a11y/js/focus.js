() => {
  const e = document.activeElement;
  if (!e || e === document.body || e === document.documentElement) return null;
  const name = (e.getAttribute('aria-label') || (e.labels && e.labels[0] && e.labels[0].innerText)
    || e.innerText || e.getAttribute('title') || e.getAttribute('alt') || e.getAttribute('placeholder') || '')
    .trim().replace(/\s+/g, ' ').slice(0, 80);
  const cs = getComputedStyle(e);
  return {
    id: e.getAttribute('data-a11y-id'), tag: e.tagName.toLowerCase(), role: e.getAttribute('role'),
    name: name, type: e.getAttribute('type'),
    focus_style: {outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor + ' offset ' + cs.outlineOffset, box_shadow: cs.boxShadow},
  };
}
