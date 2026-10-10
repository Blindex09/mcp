(el) => {
  // Estado de um formulario depois de uma tentativa de envio: cada campo, se e' valido segundo o navegador, o que o descreve.
  const form = el.form || el.closest('form');
  if (!form) return {form: false};
  const byIds = (ids) => (ids || '').split(/\s+/).filter(Boolean).map((i) => document.getElementById(i)).filter(Boolean);
  let active = document.activeElement;
  while (active && active.shadowRoot && active.shadowRoot.activeElement) active = active.shadowRoot.activeElement;
  const fields = Array.from(form.elements).filter((f) => f.type !== 'hidden' && f.type !== 'submit' && f.type !== 'button' && f.tagName !== 'FIELDSET').map((f) => {
    const lab = f.labels && f.labels.length ? Array.from(f.labels).map((l) => l.textContent.trim()).join(' ') : (f.getAttribute('aria-label') || null);
    return {name: (lab || f.name || f.id || f.tagName.toLowerCase()).slice(0, 40), required: f.required === true || f.getAttribute('aria-required') === 'true',
      valid: f.checkValidity(), validation_message: f.validationMessage ? f.validationMessage.slice(0, 80) : null, aria_invalid: f.getAttribute('aria-invalid'),
      described_by: byIds(f.getAttribute('aria-describedby')).map((d) => d.textContent.trim()).join(' ').slice(0, 120) || null, focused: f === active};
  });
  const alerts = Array.from(document.querySelectorAll('[role=alert],[role=status],[aria-live]')).map((a) => (a.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean).map((t) => t.slice(0, 100)).slice(0, 5);
  return {form: true, novalidate: form.noValidate, all_valid: form.checkValidity(), fields, live_text: alerts};
}
