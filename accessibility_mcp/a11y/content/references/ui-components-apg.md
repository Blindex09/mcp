# 2026 UI Component Accessibility Standards & ARIA APG Guide

Detailed ARIA attributes, keyboard contracts, and WCAG 2.2 specifications for 11 essential UI components.

---

## 1. Modals & Dialogs

### A. Native `<dialog>` (2026 Recommended Baseline)
- **HTML:** `<dialog id="modal-1" aria-labelledby="title-id" aria-describedby="desc-id">`
- **Activation:** `dialog.showModal()`
- **Implicit Behavior:** Implicit `role="dialog"` and `aria-modal="true"`. Renders in browser top layer with `::backdrop`. Background page (`<main>`, etc.) automatically rendered `inert`.
- **Keyboard & Focus:**
  - `Tab` / `Shift+Tab`: Native focus trap inside modal.
  - `Escape`: Fires native `cancel` event, closes modal, and restores focus to triggering element automatically.

### B. Custom Focus Trap (Legacy / Custom Overlay)
- **HTML:** `<div role="dialog" aria-modal="true" aria-labelledby="title-id" aria-describedby="desc-id" tabindex="-1">`
- **JS Management:** Apply `inert` to background containers (`<main>`). Capture `keydown` for `Tab` wrapping and `Escape` closing. Store `document.activeElement` before opening and call `.focus()` on close.

---

## 2. Dropdowns & Menus

### A. Navigation Disclosure (Website Site Navigation Links)
- **Use Case:** Site navigation dropdowns containing link lists (`<a>`).
- **HTML:** `<nav aria-label="Main Navigation">` + `<button aria-expanded="false" aria-controls="sub-menu">` + `<ul id="sub-menu"><li><a href="...">`
- **Keyboard:** `Tab` moves into button, then sequentially through links. `Enter`/`Space` toggles `aria-expanded`. `Escape` closes submenu and returns focus to button.
- **CRITICAL:** Do NOT use `role="menu"` or arrow key trapping for site navigation links!

### B. Action Menu (`role="menu"` — Desktop Application Actions Only)
- **Use Case:** Action menus (File > Save, Edit > Copy). NOT for site navigation links.
- **HTML:** `<button aria-haspopup="true" aria-expanded="false" aria-controls="menu-id">` + `<ul role="menu" id="menu-id">` + `<li role="menuitem">`
- **Keyboard:** `Down`/`Up Arrows` navigate items via roving tabindex. `Home`/`End` jump to start/end. `Enter`/`Space` trigger action and close. `Tab` closes menu immediately and moves focus to next page control.

---

## 3. Accordions

### A. Native `<details>` / `<summary>`
- **HTML:** `<details><summary>Heading Title</summary><p>Panel text...</p></details>`
- **Keyboard:** Native browser support. `Enter`/`Space` toggles open state. No custom ARIA attributes required.

### B. Custom ARIA Accordion
- **HTML:** `<h3 class="acc-heading"><button id="btn-1" aria-expanded="false" aria-controls="panel-1">Title</button></h3>` + `<div id="panel-1" role="region" aria-labelledby="btn-1" hidden>`
- **Keyboard:** `Tab` moves between header buttons. `Enter`/`Space` toggles `aria-expanded` and `hidden` attribute.

---

## 4. Alt Text & Graphic Visualizations

- **Decorative Images:** `alt=""` or `aria-hidden="true"`.
- **Informative Images:** Concise functional description in `alt="..."`. Avoid redundant text ("Image of...").
- **Inline SVG:** `<svg role="img" aria-labelledby="title-id desc-id">` with inner `<title id="title-id">` and `<desc id="desc-id">`.
- **Complex Charts & Visualizations:** Provide a short summary via `alt` or `<figcaption>`, paired with an adjacent accessible HTML `<table>` (with `<th>` and `scope="col|row"`).

---

## 5. Tooltips (Non-Interactive Contextual Popups)

- **HTML:** `<button aria-describedby="tip-1">Action</button>` + `<div id="tip-1" role="tooltip">Hint text</div>`
- **WCAG 1.4.13 Requirements:**
  - **Dismissable:** `Escape` key dismisses tooltip without moving focus.
  - **Hoverable:** Mouse can hover over tooltip text without it disappearing.
  - **Persistent:** Remains open until focus/hover is removed or `Escape` pressed.
- **CRITICAL:** Tooltips MUST NOT contain interactive elements (links, buttons).

---

## 6. Comboboxes (Editable Input with Listbox Popup)

- **HTML:** `<input role="combobox" aria-expanded="false" aria-haspopup="listbox" aria-controls="list-1" aria-autocomplete="list" aria-activedescendant="opt-1">` + `<ul id="list-1" role="listbox"><li id="opt-1" role="option" aria-selected="false">`
- **Keyboard:** DOM focus stays inside `<input>`. `Down`/`Up Arrows` update `aria-activedescendant` pointer. `Enter` accepts selection (`aria-selected="true"`) and closes. `Escape` closes popup.

---

## 7. Tabs (Roving Tabindex Pattern)

- **HTML:** `<div role="tablist" aria-label="...">` + `<button role="tab" aria-selected="true" aria-controls="panel-1" tabindex="0">` + `<div role="tabpanel" id="panel-1" aria-labelledby="tab-1" tabindex="0">`
- **Keyboard:** Roving tabindex (`tabindex="0"` on active tab, `-1` on inactive). `Left`/`Right Arrows` move focus between tabs. `Space`/`Enter` activates tab (or auto-activate on arrow focus). `Tab` moves from active tab directly into `tabpanel`.

---

## 8. Treeviews

- **HTML:** `<ul role="tree">` + `<li role="treeitem" aria-expanded="false" aria-selected="false" tabindex="0">` + `<ul role="group">`
- **Keyboard:** Roving tabindex. `Down`/`Up Arrows` navigate visible items. `Right Arrow` expands collapsed node or moves to first child. `Left Arrow` collapses expanded node or moves to parent. `Enter`/`Space` selects item (`aria-selected="true"`).

---

## 9. Data Tables (Sortable & Responsive)

- **HTML:** `<table>` + `<thead>` + `<tr>` + `<th scope="col" aria-sort="ascending|descending|none"><button type="button">Header</button></th>`
- **Responsive Overflow:** Wrap table in `<div tabindex="0" role="region" aria-label="Data Table">` to allow keyboard scrollability when table horizontally overflows viewports.

---

## 10. Carousels

- **HTML:** `<section role="region" aria-roledescription="carousel" aria-label="...">` + `<button aria-label="Pause automatic slide rotation">Pause</button>` + `<div role="group" aria-roledescription="slide" aria-label="1 of 4">`
- **WCAG 2.2.2 Rule:** Auto-rotation MUST automatically pause whenever keyboard focus or mouse hover enters carousel. Live region must use `aria-live="off"` while auto-rotating and `aria-live="polite"` when paused.

---

## 11. Drag-and-Drop (WCAG 2.5.7 Single-Pointer Alternative)

- **WCAG 2.5.7 Requirement:** All dragging movements (reordering, canvas pan, drag-and-drop file upload) MUST offer single-pointer tap/click alternatives.
- **Implementation:**
  - Provide "Move Up" / "Move Down" buttons for sortable lists.
  - Provide explicit file upload `<input type="file">` alongside drag dropzones.
  - Provide slider `+` / `-` increment buttons.
- **Keyboard Contract:** `Space`/`Enter` grabs item (`aria-pressed="true"`), `Up`/`Down` arrows adjust position, `Space`/`Enter` drops item, `Escape` cancels movement.

---

## 12. Repeated Options, Shortcuts, and Action Sets

- When peer items are presented as a set—keyboard shortcuts, related actions, settings, search results, or selectable options—give each item its own visual row and semantic boundary. Use `<ul><li>` by default, or `<ol><li>` when order matters.
- Keep every action as its own native `<button>` or `<a href>`. A list groups the controls; it does not replace their native semantics or keyboard behavior.
- For a simple expandable set of actions, use `<details><summary>More options</summary><ul><li><button>…`. Let `Tab` visit each action. When the disclosure behaves as a temporary options panel, support `Escape` from anywhere inside it: close the panel, prevent conflicting handlers, and return focus to its `<summary>`/trigger. Do not use `role="menu"` unless implementing and testing the complete application-menu keyboard contract.
- Use CSS layout (`display: grid|flex`, column direction, and `gap`) to create separate rows. Verify that the class names emitted by templates/components match the selectors that provide the layout.
- Do not concatenate peer controls or instructions inside one paragraph or unstructured container. Spaces, punctuation, `<br>`, block styling alone, and ARIA labels do not expose list structure or item count.
- Give a repeated disclosure contextual naming only when needed to distinguish instances. Put the complete unique name directly in `<summary>` whenever possible (for example, `More options for Project Alpha`) and do not also add `aria-label` or hidden duplicate text. In some browser, Electron, and screen-reader combinations, overriding a native `<summary>` name can expose both the ARIA name and its visible text, producing speech such as “More options for Project Alpha, more options.” Use `aria-labelledby`/`aria-label` only for a verified semantic gap, test the computed name, and require that the trigger is spoken exactly once.

```html
<details>
  <summary>More options for Project Alpha</summary>
  <ul class="action-list">
    <li><button type="button">Export JSON</button></li>
    <li><button type="button">Clone agent</button></li>
    <li><button type="button">Delete agent</button></li>
  </ul>
</details>
```

Test both surfaces: visually confirm one item per row at supported zoom/reflow sizes, then inspect the accessibility tree or use a screen reader to confirm a list with the correct item count and distinct controls. Tab to every disclosure trigger and verify that its unique name and visible label are each exposed once, without a repeated generic suffix.
Also open the disclosure, move focus into an action, press `Escape`, and confirm that it closes and focus returns visibly to the disclosure trigger. Do not add `Escape` to ordinary always-visible lists or use it to discard unsaved work without confirmation.
