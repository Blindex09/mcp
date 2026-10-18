/**
 * Focus management patterns (2026) — the core of SPA & dynamic accessibility.
 *
 * Principle: when the UI changes in a way that affects what users should
 * interact with next, move focus to where it logically belongs.
 *
 * Sources: WAI-ARIA APG (2026), TPGi, Deque, A11yFlow, OneUptime (2026),
 * frontendpatterns.dev, Next.js docs.
 */

/* ===================================================================
 * 1. ROUTE CHANGE — move focus to the new <h1> / <main>
 * =================================================================== */
// The browser's focus handling is tied to page loads; SPAs removed page loads.
// On a client-side route change, focus stays on the trigger (now gone) and
// the screen reader's virtual cursor resets to <body> with no announcement.
//
// Fix: move focus to the new page heading. Give <h1> tabindex="-1" so it
// can receive programmatic focus, then .focus() after the route renders.
//   71.6% of screen reader users navigate by headings (WebAIM 2024).
function onRouteChange() {
  setTimeout(() => {
    const heading = document.querySelector('h1');
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      heading.focus();
    }
  }, 100);
}
// NOTE: Next.js includes an aria-live route announcer that names each
// client-side navigation, but does NOT move keyboard focus (issue #49386).
// Focus movement is your responsibility — don't assume the framework does it.
// Use focus move OR live region announcement, not both (redundant = intrusive).

/* ===================================================================
 * 2. MODAL OPEN — move focus in; CLOSE — restore to trigger
 * =================================================================== */
// APG contract: on open, move focus into the dialog; Tab/Shift+Tab wrap
// inside; Escape closes; on close, focus returns to the element that
// opened it.
//
// For new projects, the native <dialog> + .showModal() does ALL of this
// for you (Baseline since March 2022): initial focus inside, rest of page
// inert, top layer, Escape to close, focus returned to opener.
//   <dialog id="d"><button autofocus>OK</button></dialog>
//   document.getElementById('d').showModal();
//
// Custom modal focus management (when <dialog> can't be used):
let triggerEl = null;
function openModal(trigger, modal) {
  triggerEl = trigger; // remember what had focus
  document.getElementById('app-root').inert = true; // hide background
  // Move focus to the first focusable inside the modal
  const first = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  (first || modal).focus();
}
function closeModal(modal) {
  document.getElementById('app-root').inert = false;
  triggerEl?.focus(); // restore focus to the trigger
}

/* ===================================================================
 * 3. React: focus trap + restore (useEffect/useRef)
 * =================================================================== */
// import { useEffect, useRef } from 'react';
function useFocusTrap(isOpen, onClose) {
  const modalRef = useRef(null);
  const triggerRef = useRef(null);
  useEffect(() => {
    if (!isOpen) return;
    triggerRef.current = document.activeElement; // store trigger
    const focusable = modalRef.current?.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (focusable?.length) focusable[0].focus();

    function onKey(e) {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.key !== 'Tab' || !focusable) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      triggerRef.current?.focus(); // restore on close
    };
  }, [isOpen, onClose]);
  return modalRef;
}

/* ===================================================================
 * 4. Angular: LiveAnnouncer + cdkTrapFocus for route changes & modals
 * =================================================================== */
// import { Injectable } from '@angular/core';
// import { Router, NavigationEnd } from '@angular/router';
// import { LiveAnnouncer } from '@angular/cdk/a11y';
// import { filter } from 'rxjs';
//
// @Injectable({ providedIn: 'root' })
// export class A11yService {
//   constructor(router: Router, announcer: LiveAnnouncer) {
//     router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe(() => {
//       announcer.announce('Navigated to ' + document.title);
//       setTimeout(() => {
//         const h = document.querySelector('h1');
//         if (h) { h.setAttribute('tabindex', '-1'); (h as HTMLElement).focus(); }
//       }, 100);
//     });
//   }
// }
//
// Modal focus trap via CDK:
//   <div role="dialog" aria-modal="true" cdkTrapFocus [cdkTrapFocusAutoCapture]="true">
//     <h2 id="t">Title</h2>
//     <button (click)="close()">Close</button>
//   </div>

/* ===================================================================
 * 5. DYNAMIC CONTENT — move focus to the new content
 * =================================================================== */
// When deleting a list item, focus often vanishes. Move focus to the
// next logical item or a status message.
//
// When async content loads into a region, move focus to the new heading
// OR announce via aria-live (not both).
//
// Infinite scroll: provide a "Load more" button as fallback; keep footer
// reachable; announce loaded chunks via aria-live.

/* ===================================================================
 * 6. SKIP LINK — first focusable element, target needs tabindex="-1"
 * =================================================================== */
//   <a class="skip-link" href="#main">Skip to main content</a>
//   <main id="main" tabindex="-1">...</main>
// CSS: hide off-screen until :focus (never display:none).
// On click, the browser focuses #main only if it's focusable (tabindex="-1").
// Some browsers need JS to force focus:
document.querySelectorAll('.skip-link').forEach((link) => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const target = document.getElementById(new URL(link.href).hash.slice(1));
    target?.focus();
  });
});

/* ===================================================================
 * 7. tabindex rules
 * =================================================================== */
// tabindex="0"  — add to natural tab order (for custom focusable elements)
// tabindex="-1" — programmatically focusable only (skip-link targets, route h1, dialog)
// tabindex > 0  — NEVER. Creates a separate fragile tab order that drifts from layout.
//                 Reorder the DOM instead; keep tabindex to 0 and -1.

/* ===================================================================
 * 8. Focus indicators — never remove without replacement
 * =================================================================== */
// :focus-visible styles keyboard focus only (not mouse clicks).
//   :focus-visible { outline: 3px solid #1a73e8; outline-offset: 2px; }
// WCAG 2.4.7 (AA) and the newer 2.4.13 Focus Appearance.
// 3:1 minimum contrast for focused states.

/* ===================================================================
 * 9. Cypress: verify focus management on route change
 * =================================================================== */
// describe('SPA Navigation', () => {
//   it('manages focus on route change', () => {
//     cy.visit('/');
//     cy.get('a[href="/about"]').click();
//     cy.focused().should('have.attr', 'tabindex', '-1'); // or role heading
//     cy.injectAxe();
//     cy.checkA11y();
//   });
// });