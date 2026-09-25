// Accessible modal with a custom focus trap — vanilla JS
// Use when you need behavior the native <dialog> element cannot provide
// or you must support older browsers. For new projects, prefer <dialog>.

function openModal(triggerId, modalId) {
  const trigger = document.getElementById(triggerId);
  const modal = document.getElementById(modalId);
  // Selectors match every natively focusable element, excluding disabled and tabindex="-1"
  const focusableSelectors =
    'a[href], button:not([disabled]), textarea, input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

  // 1. Show the modal
  modal.style.display = 'block';
  modal.setAttribute('aria-hidden', 'false');

  // 2. Hide the rest of the page from assistive tech (and disable interaction)
  //    The inert attribute (Baseline 2026) replaces aria-hidden + tabindex + pointer-events juggling.
  const root = document.getElementById('app-root');
  root.inert = true;

  // 3. Query focusable elements inside the modal
  let focusableElements = modal.querySelectorAll(focusableSelectors);
  let firstFocusable = focusableElements[0];
  let lastFocusable = focusableElements[focusableElements.length - 1];

  // 4. Move focus into the modal immediately
  firstFocusable.focus();

  function trapFocus(e) {
    if (e.key === 'Escape') {
      closeModal();
      return;
    }
    if (e.key !== 'Tab') return;

    // Re-query in case content changed dynamically (lazy-loaded form fields, async data)
    focusableElements = modal.querySelectorAll(focusableSelectors);
    firstFocusable = focusableElements[0];
    lastFocusable = focusableElements[focusableElements.length - 1];

    if (e.shiftKey) {
      // Shift+Tab on the first → loop to the last
      if (document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable.focus();
      }
    } else {
      // Tab on the last → loop to the first
      if (document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable.focus();
      }
    }
  }

  modal.addEventListener('keydown', trapFocus);

  function closeModal() {
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    root.inert = false;
    modal.removeEventListener('keydown', trapFocus);
    // 5. Restore focus to the element that opened the modal — WCAG 2.4.3 Focus Order
    trigger.focus();
  }

  // Close button + backdrop click
  modal.querySelector('[data-close]')?.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  return closeModal;
}