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
