// SPA / AJAX accessibility patterns (2026)
// The core SPA problem: client-side routing does NOT reload the page,
// so screen readers don't announce the new page or reset focus.
// You must do both manually.

// Helper functions for demonstration
function showLoading() { console.log('Loading started...'); }
function hideLoading() { console.log('Loading complete.'); }
function renderResults(results) { console.log('Rendering results:', results); }
async function runValidation() { return []; }

/* ------------------------------------------------------------------ */
/* Pattern 1: Route change announcer                                   */
/* Put this empty live region in your app shell ONCE. It must exist    */
/* in the DOM before content changes — adding aria-live + content     */
/* simultaneously often fails to announce.                              */
/*   <div id="route-announcer" aria-live="polite" class="sr-only"></div>*/
/* ------------------------------------------------------------------ */
function announceRouteChange(newPageTitle) {
  const announcer = document.getElementById('route-announcer');
  // Clear then set so screen readers re-announce identical strings
  announcer.textContent = '';
  // microtask delay ensures the empty state is registered first
  requestAnimationFrame(() => {
    announcer.textContent = `Navigated to ${newPageTitle}`;
  });
}

/* ------------------------------------------------------------------ */
/* Pattern 2: Move focus to the new page heading on route change       */
/* Gives screen reader users a "page top" landmark like a full reload. */
/* The <h1> needs tabindex="-1" to be programmatically focusable.      */
/* ------------------------------------------------------------------ */
function focusNewPageHeading() {
  // small delay lets the new route's DOM render first
  setTimeout(() => {
    const heading = document.querySelector('h1');
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      heading.focus();
    }
  }, 100);
}

/* ------------------------------------------------------------------ */
/* Pattern 3: Skip link that survives SPA navigation                   */
/* The target must be focusable (tabindex="-1") on every route.        */
/*   <a href="#main-content" class="skip-link">Skip to main content</a>*/
/*   <main id="main-content" tabindex="-1">...</main>                  */
/* ------------------------------------------------------------------ */
// No JS needed — the skip link works via fragment navigation + tabindex.
// Just ensure <main> keeps id="main-content" and tabindex="-1" on every route.

/* ------------------------------------------------------------------ */
/* Pattern 4: Announce AJAX search results (live region)              */
/* Polite is the default for most updates; assertive only for urgent.  */
/* ------------------------------------------------------------------ */
async function search(query) {
  showLoading();
  const results = await fetch(`/api/search?q=${encodeURIComponent(query)}`).then(r => r.json());
  hideLoading();

  // Announce the count, not every result (too noisy)
  const status = document.getElementById('search-status'); // aria-live="polite"
  status.textContent = `${results.length} results found`;
  // Render results into a list with role="list" or a plain <ul>
  renderResults(results);
}

/* ------------------------------------------------------------------ */
/* Pattern 5: Announce form errors after async validation              */
/* Use role="alert" (assertive) only for errors that block submission. */
/* ------------------------------------------------------------------ */
async function validateForm() {
  const errors = await runValidation();
  if (errors.length) {
    const summary = document.getElementById('form-error-summary');
    // Make the summary focusable so keyboard users can reach it
    summary.setAttribute('tabindex', '-1');
    summary.focus();
    summary.innerHTML = `<h2>Please fix ${errors.length} error(s):</h2><ul>` +
      errors.map(e => `<li>${e.message}</li>`).join('') + '</ul>';
  }
}

/* ------------------------------------------------------------------ */
/* Infinite scroll — provide an alternative (pagination)             */
/* and announce loaded chunks via a live region. Landmarks let users   */
/* navigate past loaded content.                                       */
/* ------------------------------------------------------------------ */
function onLoadMoreChunk(chunkCount) {
  const live = document.getElementById('load-status'); // aria-live="polite"
  live.textContent = `Loaded ${chunkCount} more items`;
  // Always provide a "Load more" button as an alternative to auto-scroll.
}

/* ------------------------------------------------------------------ */
/* Debounce rapid state changes to prevent live region queue overflow  */
/* Rapid updates can flood a screen reader's announcement queue.       */
/* ------------------------------------------------------------------ */
function debounce(fn, ms = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}
const debouncedAnnounce = debounce((msg) => {
  document.getElementById('route-announcer').textContent = msg;
}, 300);