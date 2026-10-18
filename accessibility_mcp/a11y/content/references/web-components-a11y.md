# Web Components & Custom Elements Accessibility Guide (2026)

Specifications for **Form-Associated Custom Elements (FACE)**, **`ElementInternals`**, **Accessibility Object Model (AOM)**, and **Lit 3.x / Stencil v4+** accessibility patterns.

---

## 1. Form-Associated Custom Elements (FACE) & `ElementInternals`

- **Declaration:** Custom elements declare `static formAssociated = true` and call `this.attachInternals()`.
- **`ElementInternals.setFormValue(value, state)`:** Accepts `string`, `File`, or `FormData` for multi-value controls.
- **`ElementInternals.setValidity(flags, message, anchor)`:** 
  - `flags`: `{ valueMissing, typeMismatch, patternMismatch, ... }`.
  - **`anchor` (Crucial 3rd Argument):** Always pass the internal focusable element inside the Shadow DOM (e.g. `this.shadowRoot.querySelector('input')`). On form submit validation failure, the browser uses this anchor to focus and scroll to the target.
- **`ElementInternals` ARIA Mixin:** Set `internals.role`, `internals.ariaLabel`, `internals.ariaDisabled` to provide default semantics without populating host DOM attributes. Host HTML attributes set by consumers override internal defaults.

---

## 2. Accessibility API surface and experimental AOM work

- **ARIA reflection:** `ElementInternals` can expose default roles, labels, and states. Support differs by property and older browser/AT versions; feature-detect newer element-reference properties and test the target matrix.
- **User-intent events:** AOM proposals for assistive-technology intent events are experimental. Do not build production interaction on invented or unsupported events such as `ariarequestincrement` or `ariarequestdismiss`.

---

## 3. Shadow DOM & Cross-Root ARIA

- **Shadow Root Reference Target:** Reference-target APIs are emerging, not a universal baseline. Feature-detect, verify the exact current syntax against the HTML Standard, and keep a same-tree or form-associated fallback.
- **Element Reflection:** Use `internals.ariaLabelledByElements = [labelElement]` or `internals.ariaDescribedByElements = [descElement]` to pass array of node references across roots.
- **`delegatesFocus: true`:** Set `attachShadow({ mode: 'open', delegatesFocus: true })` to delegate label click focus to the first internal focusable control.

---

## 4. Lit 3.x & Stencil v4+ Patterns

- **Lit 3.x:** Use the platform `static formAssociated = true` and `this.attachInternals()` unless a project dependency supplies and documents a decorator. Override form lifecycle callbacks as needed.
- **Stencil v4+:** Use `@AttachInternals() internals!: ElementInternals;` decorator and sync `internals.setFormValue()` during lifecycle updates.
