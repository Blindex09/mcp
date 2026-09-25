/**
 * Accessible forms, notifications, and live regions (2026)
 * Consolidated reference with copy-paste HTML, React, and Angular.
 *
 * Sources: MDN live regions, Sara Soueidan, W3C ARIA21, accessibility.build,
 * A11yPath, WebAbility, OneUptime (2026), ngx-signal-forms (2026).
 */

/* ===================================================================
 * 1. FORM LABELING — decision order
 * =================================================================== */
// 1. <label for>  — most reliable; gives click-target for free
// 2. aria-labelledby — when visible text exists but can't be a <label>
// 3. aria-label — last resort, no visible label possible (icon buttons)
// 4. aria-describedby — supplementary (hints, errors), NOT the name

/* WCAG 2.5.3 Label in Name: the visible text must appear at the START of
   the accessible name. Don't overwrite visible text with aria-label that
   omits it. */

// --- Native label (best) ---
//   <label for="email">Email address</label>
//   <input type="email" id="email" name="email" autocomplete="email" required>

// --- aria-labelledby when visible text lives elsewhere ---
//   <span id="pw-label">Password</span>
//   <input id="pw" type="password" aria-labelledby="pw-label">

// --- aria-label only when no visible label ---
//   <button type="button" aria-label="Search">🔍</button>

/* ===================================================================
 * 2. FIELDSET / LEGEND — group radio/checkbox sets
 * =================================================================== */
// The legend announces with each control in the group. Keep it brief.
//   <fieldset>
//     <legend>Preferred contact method</legend>
//     <input id="c-email" name="contact" type="radio" value="email">
//     <label for="c-email">Email</label>
//   </fieldset>

/* ===================================================================
 * 3. REQUIRED FIELDS — mark TWO ways (native + visible indicator)
 * =================================================================== */
//   <p aria-hidden="true">Fields marked with * are required.</p>
//   <label for="name">Full name <span aria-hidden="true">*</span>
//     <span class="sr-only">(required)</span>
//   </label>
//   <input id="name" name="name" required aria-required="true" autocomplete="name">

/* ===================================================================
 * 4. AUTOCOMPLETE (WCAG 1.3.5) — personal data MUST have tokens
 * =================================================================== */
//   <input autocomplete="given-name">  <input autocomplete="family-name">
//   <input autocomplete="email">       <input autocomplete="tel">
//   <input autocomplete="street-address">  <input autocomplete="address-level2">
//   <input autocomplete="postal-code"> <input autocomplete="country-name">
//   <input type="date" autocomplete="bday">

/* ===================================================================
 * 5. ERROR HANDLING — aria-invalid + aria-describedby + role="alert"
 * =================================================================== */
// Set aria-invalid="true" ONLY after a validation attempt (never pre-set).
// Tie error text with aria-describedby. Announce with role="alert"
// (implicit aria-live="assertive" + aria-atomic="true").
//
//   <label for="pin4">PIN * (4 digits)</label>
//   <input id="pin4" pattern="\d{4}" type="text"
//          aria-describedby="pin4-errormsg" aria-invalid="true" class="error">
//   <span id="pin4-errormsg" role="alert">Error: PIN must be 4 digits.</span>
//
// JS helper to add an error programmatically:
function addFieldError(field, message) {
  const errId = field.id + '-errormsg';
  const errDiv = document.createElement('div');
  errDiv.id = errId;
  errDiv.textContent = message;
  field.parentNode.appendChild(errDiv);
  field.setAttribute('aria-describedby', errId);
  field.setAttribute('aria-invalid', 'true');
}
// To remove: clear aria-invalid, remove the error div, restore aria-describedby.

/* Don't combine role="alert" with aria-live="assertive" on inline errors —
   double-speaks in VoiceOver iOS. role="alert" alone covers it. */

/* ===================================================================
 * 6. FOCUSABLE ERROR SUMMARY on submit (longer forms)
 * =================================================================== */
// The summary needs tabindex="-1" to receive programmatic focus.
//
//   <div id="error-summary" role="alert" tabindex="-1" aria-labelledby="es-title">
//     <h2 id="es-title">There are 2 errors in your submission</h2>
//     <ul>
//       <li><a href="#email">Email is required</a></li>
//       <li><a href="#password">Password must be at least 8 characters</a></li>
//     </ul>
//   </div>
//
// On invalid submit:
//   form.addEventListener('submit', (e) => {
//     if (!form.checkValidity()) { e.preventDefault(); document.getElementById('error-summary').focus(); }
//   });

/* ===================================================================
 * 7. LIVE REGIONS — politeness
 * =================================================================== */
// off (default)  — not a live region; changes only announce when focused
// polite         — announce at next idle pause (most common)
// assertive      — interrupt current speech (use sparingly: errors, security)
//
// role="status"  = implicit aria-live="polite" + aria-atomic="true"
// role="alert"   = implicit aria-live="assertive" + aria-atomic="true"
// role="log"     = implicit aria-live="polite" (only when sequential
//                   additions are intentionally meant to auto-announce)

/* ===================================================================
 * 8. CRITICAL: prime the live region BEFORE content changes
 * =================================================================== */
// The region must exist in the DOM before you mutate it. Injecting the
// element already-populated is NOT a content change and won't announce.
// Pre-populated regions are mostly silent on load (except role="alert").

// Clear → deferred write is a common compatibility technique, not a guarantee.
// Test the target browser/AT matrix and avoid using it to force duplicate speech:
function announce(region, message) {
  region.textContent = '';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => (region.textContent = message));
  });
}

// Re-announcing the SAME message: clear first (some AT ignore repeats).

/* ===================================================================
 * 9. TOASTS — persistent container at app root, don't auto-hide
 * =================================================================== */
// Auto-hiding toasts (3s) can fail WCAG 2.2.1 (Timing Adjustable) and make
// the message unreviewable. Prefer a persistent toast with a close button.
//
//   <div class="toast-container" role="region" aria-label="Notifications"
//        aria-live="polite"></div>

/* ===================================================================
 * 10. DEBOUNCE rapid announcements (search, infinite scroll)
 * =================================================================== */
// A flooded assertive queue makes NVDA/VoiceOver truncate or skip.
// Choose a delay from user testing rather than treating a number as universal.
// A genuine visible status message must be programmatically determinable;
// WCAG 4.1.3 does not require inventing or speaking every dynamic update.
function debounceAnnounce(fn, delay = 150) {
  let timer;
  return (msg) => {
    clearTimeout(timer);
    timer = window.setTimeout(() => fn(msg), delay);
  };
}

/* ===================================================================
 * 11. SEARCH RESULT COUNTS — polite, debounced, atomic
 * =================================================================== */
//   <div id="result-count" role="status" class="sr-only"></div>
const announceCount = debounceAnnounce((msg) => {
  const el = document.getElementById('result-count');
  el.textContent = '';
  requestAnimationFrame(() => { el.textContent = msg; });
}, 150);
// after results render: announceCount(`${results.length} of ${total} results match`);

/* ===================================================================
 * 12. INFINITE SCROLL — provide a "Load more" button + announce chunks
 * =================================================================== */
// Keep the footer reachable via a skip link; announce loaded counts.
//   announce(`${loadedCount} items loaded; ${total - loadedCount} remaining`, 'polite');
// Best practice: prefer pagination over infinite scroll for accessibility.

/* ===================================================================
 * 13. FORM SUBMISSION STATUS
 * =================================================================== */
//   <div id="form-status" role="status" class="sr-only"></div>
// On submit: "Submitting…" → after success: "Form submitted successfully."
// For async failures: role="alert" (assertive).

/* ===================================================================
 * 14. PROGRESS BARS — progressbar role is NOT a live region
 * =================================================================== */
// A progressbar exposes value changes itself. Add a separate bounded status
// only when testing shows the terminal or milestone outcome is otherwise lost;
// do not mirror every percentage into a second accessible element.
//   <div role="progressbar" aria-labelledby="lbl" aria-valuemin="0"
//        aria-valuemax="100" aria-valuenow="40" aria-valuetext="40 percent uploaded"></div>
//   <div role="status" class="sr-only">40% complete</div>
// Use aria-valuetext when the number alone isn't meaningful
// (e.g. "Uploading: 50% — about 10 seconds left").

/* ===================================================================
 * 15. aria-busy during async loads — always use try/finally
 * =================================================================== */
async function loadRegion(region) {
  region.setAttribute('aria-busy', 'true');
  try {
    region.textContent = '';
    region.appendChild(await buildFirstPart());
    region.appendChild(await buildSecondPart());
  } finally {
    region.setAttribute('aria-busy', 'false'); // announces once
  }
}
// If async throws before finally, aria-busy stays true and silences the subtree.

/* ===================================================================
 * 16. SPA ROUTE ANNOUNCEMENTS — focus move OR live region (not both)
 * =================================================================== */
// Choose one tested route-change strategy. A focused, named new-page heading
// is normally already announced; do not also announce the same title live.
//
//   <div id="route-announcer" aria-live="polite" aria-atomic="true" class="sr-only"></div>
//
// In router afterEach:
//   region.textContent = '';  // clear in route cleanup to avoid stale messages
//   requestAnimationFrame(() => { region.textContent = to.meta.title; });
// OR move focus to the new primary heading (tabindex="-1"), not both.
// Framework support varies; consult its current router documentation.

/* ===================================================================
 * 17. WCAG 4.1.3 STATUS MESSAGES (Level AA) — without focus change
 * =================================================================== */
// Covered by aria-live / role="status" / role="alert" so screen readers
// announce WITHOUT moving focus.
// Scope note: inline field errors are covered by WCAG 3.3.1 (Error
// Identification) via aria-describedby/aria-invalid, NOT live regions.
//
// Minimal compliant patterns:
//   <div role="status">Saved.</div>
//   <div role="alert">Your session expires in 2 minutes.</div>
//   <div role="progressbar" aria-valuemin="0" aria-valuemax="100"
//        aria-valuenow="40" aria-valuetext="40 percent uploaded"></div>
//   <div role="status" class="sr-only">40% complete</div>

/* ===================================================================
 * 18. LIVE REGIONS + INTERACTIVE ELEMENTS = ANTI-PATTERN (2026 update)
 * =================================================================== */
// Do NOT use an aria-live / role="status" / role="alert" container for a
// message that contains interactive controls (links, buttons, "Undo")
// the user may need to act on. Per Sara Soueidan / Scott O'Hara (2026):
//
//   1. When a screen reader announces a live region, it announces the RAW
//      TEXT only — the semantics of any <button>, <a>, or <input> inside
//      it are STRIPPED. The user hears the words but not that they are
//      actionable, and cannot reach them from the announcement.
//   2. Most AT does not let a live-region announcement draw focus, so even
//      a Tab press won't reliably land on the inline action.
//
// For actionable notifications (toast with "Undo", session expiry with
// "Extend", errors with "Retry") use a NON-live region + move focus:
//
//   <div role="alertdialog" aria-labelledby="toast-title" aria-describedby="toast-desc">
//     <h2 id="toast-title">Item deleted</h2>
//     <p id="toast-desc">The row was removed from your cart.</p>
//     <button type="button" onclick="undo()">Undo</button>
//     <button type="button" onclick="dismiss()">Dismiss</button>
//   </div>
//   // JS: toastEl.focus() or move focus to the primary action button.
//
// Rule: classify the message. A genuine non-interactive status can use a live
// status mechanism. An actionable blocking decision normally needs a named
// dialog and deliberate focus management. There is no universal numeric live-
// region limit, but fewer coordinated channels reduce collisions.
//
// Chat is not an automatic exception. Keep its transcript semantic and
// manually navigable. Use role="log" only when sequential auto-announcement is
// an explicit, tested product requirement; AI token/tool streams stay silent.
