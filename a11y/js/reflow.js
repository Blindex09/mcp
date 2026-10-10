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
