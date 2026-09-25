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
      if (!samples[key]) samples[key] = el.tagName.toLowerCase() + ': ' + (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 40);
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
