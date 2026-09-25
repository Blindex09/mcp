import { useReducedMotion, usePreferredContrast, usePreferredColorScheme } from '@reactuses/core';
import { useRef } from 'react';

/**
 * React accessibility hooks (reactuse / @reactuses/core, 2026).
 *
 * These hooks read OS-level user preferences so your components adapt
 * automatically. Accessibility isn't only ARIA — it's respecting the
 * settings users already configured.
 *
 * NOTE: these hooks are NOT part of Adobe's `react-aria` package — that
 * package has no useReducedMotion/usePreferredContrast/usePreferredColorScheme
 * exports. They come from `@reactuses/core` (reactuse.com).
 *
 * Source: reactuse.com, "Building Accessible React Components with Hooks" (2026).
 */

/* ------------------------------------------------------------------ */
/* Toast notification that respects user preferences                    */
/* ------------------------------------------------------------------ */
function AccessibleToast({ message, onDismiss }) {
  const prefersReducedMotion = useReducedMotion();
  const isHighContrast = usePreferredContrast() === 'more';
  const scheme = usePreferredColorScheme(); // 'light' | 'dark' | 'no-preference'
  const dismissRef = useRef(null);

  const colors = scheme === 'dark'
    ? { bg: '#1a1a1a', text: '#f5f5f5', border: '#444' }
    : { bg: '#fff', text: '#1a1a1a', border: '#ccc' };

  return (
    <div
      role="alert"                  // implicit assertive live region; do not duplicate aria-live
      style={{
        position: 'fixed', top: '16px', right: '16px',
        backgroundColor: colors.bg, color: colors.text,
        border: `${isHighContrast ? '3px' : '1px'} solid ${colors.border}`,
        borderRadius: '8px', padding: '16px 20px', maxWidth: '400px',
        display: 'flex', alignItems: 'center', gap: '12px',
        fontWeight: isHighContrast ? 700 : 400,
        // Respect motion preferences — fade instead of slide when reduced
        animation: prefersReducedMotion ? 'none' : 'slideIn 0.3s ease-out',
        transition: prefersReducedMotion ? 'none' : 'opacity 0.2s ease',
      }}
    >
      <span style={{ flex: 1 }}>{message}</span>
      <button
        ref={dismissRef}
        onClick={onDismiss}
        aria-label="Dismiss notification"
        style={{
          background: 'none', border: `1px solid ${colors.text}`,
          color: colors.text, cursor: 'pointer', borderRadius: '4px', padding: '4px 8px',
        }}
      >
        ×
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Search results announcement (polite)                                 */
/* ------------------------------------------------------------------ */
function SearchResults({ query, results, isLoading }) {
  const liveAnnouncer = useRef<HTMLDivElement>(null);

  // The live region must exist BEFORE results change.
  // role="status" implies aria-live="polite" + aria-atomic="true".
  return (
    <div>
      <input
        type="search"
        aria-label="Search"
        aria-controls="search-results"
        aria-describedby="search-status"
      />
      {/* aria-live="polite" announces when the user pauses; assertive interrupts */}
      <div id="search-status" role="status" className="sr-only">
        {isLoading ? 'Searching…' : `${results.length} results for "${query}"`}
      </div>
      <ul id="search-results">
        {results.map((r) => (
          <li key={r.id}>
            <a href={r.url}>{r.title}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export { AccessibleToast, SearchResults };
