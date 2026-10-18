/**
 * Accessible tooltip — vanilla JS (2026)
 *
 * A tooltip provides SUPPLEMENTARY info on hover/focus of a control.
 * It never replaces an accessible name; never hides essential
 * instructions or errors. Use aria-describedby to associate, role="tooltip"
 * on the popup, and show on BOTH hover and keyboard focus.
 *
 * Source: WAI-ARIA 1.2 Tooltip Pattern, GetWCAG (2026), Eleven Ways (2026).
 * WCAG: 1.3.1, 4.1.2.
 */

/* HTML structure:
   <button class="tip-trigger" aria-describedby="tip-help">Help</button>
   <span id="tip-help" role="tooltip" class="tooltip" hidden>
     Opens the help center in a new tab.
   </span>
*/

const triggers = document.querySelectorAll('.tip-trigger');

triggers.forEach((trigger) => {
  const tipId = trigger.getAttribute('aria-describedby');
  const tip = tipId ? document.getElementById(tipId) : null;
  if (!tip) return;

  let hideTimer = null;
  const show = () => {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    tip.hidden = false;
    tip.setAttribute('aria-hidden', 'false');
  };
  // Delay the hide so the pointer has time to move from the trigger onto the
  // tooltip itself (APG: hover-triggered content must stay open while hovered).
  const scheduleHide = () => { hideTimer = setTimeout(() => { tip.hidden = true; tip.setAttribute('aria-hidden', 'true'); }, 200); };
  const hideNow = () => { if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; } tip.hidden = true; tip.setAttribute('aria-hidden', 'true'); };

  // Show on hover AND focus (keyboard users must see it too).
  trigger.addEventListener('mouseenter', show);
  trigger.addEventListener('mouseleave', scheduleHide);
  trigger.addEventListener('focus', show);
  trigger.addEventListener('blur', hideNow);

  // Keep it open if the pointer moves onto the tooltip itself; hide once it leaves.
  tip.addEventListener('mouseenter', show);
  tip.addEventListener('mouseleave', scheduleHide);

  // Esc dismisses when focused.
  trigger.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideNow(); });
});

/* ------------------------------------------------------------------ */
/* CSS:
   .tooltip {
     position: absolute; background: #333; color: #fff;
     padding: 4px 8px; border-radius: 4px; font-size: 0.875rem;
     z-index: 1000; max-width: 20em;
   }
   .tooltip[hidden] { display: none; }
*/
/* ------------------------------------------------------------------ */
/* React version with React Aria (recommended — handles positioning,
   dismissal, cross-browser quirks):
/*
/*   <TooltipTrigger>
/*     <Button>Help</Button>
/*     <OverlayArrow>
/*       <Tooltip>Opens the help center in a new tab.</Tooltip>
/*     </OverlayArrow>
/*   </TooltipTrigger>
*/
/* ------------------------------------------------------------------ */
/* Gotchas (2026):
 * 1. Never use the HTML title attribute as the only tooltip — it is
 *    inconsistently announced by AT and not keyboard-focusable.
 * 2. aria-describedby IDs must point to EXISTING elements (one per
 *    trigger — reusing one id for many tooltips makes every trigger
 *    read the same text).
 * 3. If the tooltip contains interactive content (links), aria-describedby
 *    will not let users reach them (focus leaves the trigger → connection
 *    severed). Use a non-modal popover instead.
 * 4. role="tooltip" support in screen readers is still uneven; aria-describedby
 *    is the reliable mechanism — the role is a nice-to-have.
 */