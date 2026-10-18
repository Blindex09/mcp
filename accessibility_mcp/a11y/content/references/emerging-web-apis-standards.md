# Emerging Web APIs, Testing Rules & Web Standards (2026)

Technical specifications for 2026 browser APIs (Invoker Commands, Popovers, CSS Anchor Positioning, Container Queries, `inert`), axe-core 4.10+ rules, and Web/Mobile Web accessibility standards.

---

## 1. Emerging 2026 Native Browser APIs & CSS Standards

### A. Invoker Commands API (`command`, `commandfor`, `interestfor`)
- **Native Commands:** Standard commands (`command="show-modal"`, `command="toggle-popover"`, `command="close"`) automatically manage ARIA states and keyboard focus.
- **Custom Commands Warning (`command="--custom-action"`):** Custom actions prefixed with `--` do **NOT** manage ARIA states (`aria-expanded`, `aria-pressed`) or focus automatically. Developers must update ARIA states in event listeners manually.
- **Interest Invokers (`interestfor`):** Declarative trigger for popover hints (`popover="hint"`), supporting WCAG 1.4.13 hover/focus content persistence and dismissability.

---

### B. Popover API Accessibility Rules
- **Top Layer Rendering:** Displays content in the browser's native Top Layer above all stacking contexts without `z-index` bugs.
- **No Implicit Semantics:** The Popover API manages top-layer rendering and Escape key light-dismiss, but **does NOT assign semantic roles**. Developers MUST explicitly add `role="dialog"`, `role="tooltip"`, or `role="menu"` as appropriate.
- **Modes:** `popover="auto"` (native light dismiss, Esc key close), `popover="manual"` (explicit button trigger to close), `popover="hint"` (tooltips).

---

### C. `inert` Attribute vs. `aria-hidden="true"`
- **`inert` (6-in-1 Complete DOM Isolation):** Applying `inert` to a container:
  1. Prevents keyboard focus / tabbing.
  2. Blocks pointer / click events.
  3. Hides content from the accessibility tree.
  4. Disables text selection.
  5. Prevents in-page search (Ctrl+F) matches.
  6. Disables spatial navigation.
- **`aria-hidden="true"` Flaw:** `aria-hidden` hides content from screen readers but leaves elements focusable via keyboard, creating keyboard traps and visual dead-ends.
- **Modal Rule:** Open native `<dialog>` via `.showModal()`, or set `inert` on non-modal background containers while a custom modal is active.

---

### D. CSS Anchor Positioning Accessibility
- **Strictly Visual Mechanism:** CSS Anchor Positioning (`anchor-name`, `position-anchor`) is purely a visual rendering mechanism. It **does NOT alter DOM order or tab navigation sequence**.
- **Remediation:** Establish explicit ARIA links (`aria-describedby`, `aria-controls`, `aria-details`) and programmatically manage keyboard focus between the anchor element and target popover.

---

### E. Container Queries (`@container`) & Font Scaling
- **Relative Units:** Container query breakpoints must use relative units (`rem`/`em`) instead of `px` so components adapt when users scale default font sizes (WCAG 1.4.4).
- **Fluid Typography Limits:** Font sizes using container units (`cqw`, `cqh`) must be bound using `clamp()` or `calc(1rem + 1cqw)` to prevent text from becoming unreadably small in narrow containers.

---

### F. CSS `@starting-style` & `transition-behavior: allow-discrete`
- **Accessible Top-Layer Transitions:** Allows animating `<dialog>` and `popover` entry/exit transitions natively.
- **Enabling Discrete Property Animation:** Using `transition-behavior: allow-discrete` allows transitioning properties like `display` and `overlay` without removing the element instantly from the accessibility tree, preventing abrupt screen reader disconnects during close animations.
- **Key Syntax:**
  ```css
  dialog[open] {
    opacity: 1;
    display: block;
  }
  dialog {
    opacity: 0;
    display: none;
    transition: opacity 0.3s, display 0.3s allow-discrete, overlay 0.3s allow-discrete;
  }
  @starting-style {
    dialog[open] {
      opacity: 0;
    }
  }
  ```

---

### G. HTML5 Native `<search>` Element
- **Native Landmark:** Replaces the legacy `<form role="search">` or `<div role="search">`.
- **Compatibility:** It has an implicit search landmark where supported. Test the target browser/AT matrix and keep a `<form role="search">` fallback when older support is in scope.

---

### H. Customizable `<select>` and `<selectedcontent>`
- These HTML/CSS features remain limited availability in 2026. Feature-detect them and preserve a conventional native `<select>` fallback. Do not use the abandoned `<selectlist>` name or claim uniform keyboard/screen-reader support without testing.

---

### I. WAI-ARIA 1.3 Additions (`aria-colindextext`, `aria-rowindextext`)
- **`aria-colindextext` / `aria-rowindextext`:** Provides human-readable text representations for virtualized or paginated data table indices (e.g., `aria-rowindextext="Section B, Row 4"`).
- **No `aria-actions` attribute exists.** There is no such attribute in ARIA 1.2, the ARIA 1.3 draft, or any editor's draft — do not use it. To associate contextual quick-actions with an item, use a real `role="toolbar"` (or a plain list of `<button>`s) placed inside or adjacent to the item; no extra ARIA relationship attribute is needed for that pattern.

---

### J. INP (Interaction to Next Paint) & Assistive Technology Responsiveness
- **Core Web Vital Impact:** Poor INP (>200ms) directly harms screen reader users by delaying focus movement, DOM updates, and `aria-live` announcements.
- **Best Practice:** Keep main-thread DOM mutations during live region announcements lightweight and avoid heavy synchronous tasks during user interaction events.

---

### K. WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum)
- **Problem:** Sticky headers or fixed bottom banners visually obscure focused input elements when keyboard users tab down the page.
- **CSS Solution:** Apply `scroll-margin-top` and `scroll-margin-bottom` to focusable sections/headings/inputs matching the fixed header/footer height:
  ```css
  :focus-visible {
    scroll-margin-top: 5rem;
    scroll-margin-bottom: 3rem;
  }
  ```

---

### L. Mobile Touch Target Expansion (CSS `::before` Pattern)
- **WCAG 2.2 SC 2.5.8 Target Size:** Minimum 24×24 CSS px for web; recommended 44×44 CSS px for mobile web touch targets.
- **CSS Hit Target Expander:** A pseudo-element can enlarge a hit area, but verify its actual pointer box, stacking, and overlap with adjacent targets:
  ```css
  .icon-button {
    position: relative;
    width: 24px;
    height: 24px;
  }
  .icon-button::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    min-width: 44px;
    min-height: 44px;
  }
  ```

---

### M. Mobile Screen Reader Backdrops (`pointer-events: none` Flaw)
- ❌ **DON'T:** Use `pointer-events: none` to hide modal backdrops or drawer overlays from mobile screen readers. `pointer-events: none` only disables touch clicks, but VoiceOver and TalkBack **still swipe through hidden elements**.
- ✅ **DO:** Prefer native modal behavior or `inert` for inactive background content. If legacy `aria-hidden` is unavoidable, move focus first and ensure no focused/focusable descendant remains hidden.

---

## 2. Testing Engine Rules (axe-core 4.10+)

- **`summary-name` Rule:** All `<summary>` elements must have non-empty accessible names.
- **Target size:** Do not assume an automated rule fully evaluates SC 2.5.8 geometry and exceptions. Measure targets/spacing and manually test responsive/touch layouts. The AA threshold is not 44 CSS px on mobile web.
- **`aria-prohibited-attr` Rule:** Flags prohibited ARIA attributes placed on structural/inline HTML elements where ARIA is forbidden by ARIA in HTML.
- **Hybrid AI Auditing:** Combines deterministic rules (~40-50% issue detection) with manual keyboard sweeps and AI visual/semantic checks for image alt text and reading order.
