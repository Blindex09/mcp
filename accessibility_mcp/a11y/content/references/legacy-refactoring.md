# Legacy Codebase Refactoring & Encapsulation Guide (2026)

Strategies for refactoring non-semantic legacy code, Shadow DOM encapsulation, third-party iframe integration, and resolving screen reader virtual buffer bugs.

---

## 1. Refactoring Non-Semantic Legacy Code (`<div onClick>` at Scale)

### A. Automated Codemods (`jscodeshift`)
Use AST transformations to convert `<div onClick>` to `<button type="button" data-legacy-retrofit="true">` across monorepos.

### B. CSS Cascade Reset Layer
Inject a CSS cascade layer (`@layer components.legacy-reset`) to strip default browser button styles without breaking existing `div` visual layouts:
```css
@layer components.legacy-reset {
  button[data-legacy-retrofit="true"] {
    all: unset;
    display: inline-block;
    box-sizing: border-box;
    cursor: pointer;
    text-align: inherit;
    font: inherit;
    color: inherit;
  }
  button[data-legacy-retrofit="true"]:focus-visible {
    outline: 2px solid var(--color-focus-ring, #005fcc);
    outline-offset: 2px;
  }
}
```

### C. Polyfill Wrapper (`<AccessibleClickable>`)
When instant HTML migration is risky, wrap legacy clickable containers in an adapter component that handles `role="button"`, `tabIndex={disabled ? -1 : 0}`, `Enter`/`Space` keydowns, and `e.preventDefault()` on Spacebar.

---

## 2. Shadow DOM Encapsulation & Cross-Root ARIA

### A. Focus Delegation (`delegatesFocus: true`)
Set `this.attachShadow({ mode: 'open', delegatesFocus: true })`. Automatically delegates click focus to first focusable child and matches `:focus-within` on the host element.

### B. Cross-Root ARIA Links (Reference Target Specification)
Reference-target features such as `shadowrootreferencetarget` are emerging and not a universal 2026 baseline. Feature-detect and test before use; otherwise keep the label and control in the same accessible tree or expose a form-associated custom element with `ElementInternals`.

---

## 3. Third-Party Widgets, IFrames & Embeds

- **IFrame name:** Give an informative iframe a concise `title`. Do not duplicate the same name with `aria-label`. Remove nonessential tracking frames from user-facing products where possible; if one must remain hidden, verify it has no focusable/interactive content.
- **Cross-Origin Focus Exit Bridge (`postMessage`):** Catch `A11Y_FOCUS_EXIT` events sent from iframe children when users tab past boundary elements, shifting host focus to `#iframe-next-anchor` / `#iframe-prev-anchor`.
- **Proxy Announcements:** If a trusted embedded app cannot expose required state itself, normalize authenticated `postMessage` events and announce only bounded user-relevant outcomes through the host's single announcer.
- **Overlay Warning:** Avoid third-party "Accessibility Overlay" JS widgets. They fail accessibility compliance and corrupt screen reader virtual buffers.

---

## 4. Resolving Screen Reader Virtual Buffer Bugs

- **Dynamic Node Replacement:** Avoid unmounting/destroying active container nodes in single-page apps (which causes NVDA/JAWS cursor to jump to `<body>`). Mutate `textContent` or child nodes inside stable parent containers.
- **Live-region lifecycle:** When a live region is genuinely required, create a stable empty container before the event and update it later. Do not rely on a universal fixed delay; test the framework/browser/AT matrix, keep messages bounded, and avoid a permanent duplicate of visible content.
- **`role="application"` Trap:** Restrict `role="application"` exclusively to 2D canvas/spreadsheet widgets. Do NOT use on general page layouts.
- **Background Subtree Leakage:** Apply HTML5 `inert` attribute to all background application containers when a modal or drawer is active.
