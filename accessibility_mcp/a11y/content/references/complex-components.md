# Ultra-Complex UI Components Accessibility Guide (2026)

Accessibility patterns for virtualized data grids, collaborative rich text editors, custom canvas/WebGL visualizations, and multi-step wizard flows.

---

## 1. Virtualized Data Grids & Spreadsheets

### A. Dual 2D Interaction Model
- **Grid Navigation Mode (Default):**
  - Arrow Keys ($\leftarrow \rightarrow \uparrow \downarrow$): Move focus between adjacent cells.
  - `Home` / `End`: Jump to first / last cell in row. `Ctrl+Home` / `Ctrl+End`: Top-left / bottom-right cell.
  - `Page Up` / `Page Down`: Scroll viewport and shift focus by one page height.
  - `Tab` / `Shift+Tab`: Exits grid container to next page control.
- **Cell Edit Mode:** `Enter` or `F2` enters edit mode (input/dropdown inside cell); `Escape` restores 2D grid focus.

### B. Roving `tabindex` vs `aria-activedescendant`
- **Roving `tabindex`:** Active cell gets `tabindex="0"` and `.focus()`, all inactive cells get `tabindex="-1"`. It is one documented option for tabs, menus, toolbars, and grids; choose it or `aria-activedescendant` according to the widget and tested AT behavior.
- **`aria-activedescendant`:** Real focus stays on container (e.g. `<div role="grid" tabindex="0">` or `<input role="combobox">`). `aria-activedescendant` points to active child item `id`. Container MUST have `tabindex="0"` and referenced child MUST exist in the DOM. Best for Comboboxes, Editors (preserves text caret focus), and heavy virtualized Grids.
- **Dynamic Indices:** Virtualized cells MUST continuously update `aria-rowindex`, `aria-colindex`, `aria-rowcount`, and `aria-colcount` based on absolute dataset coordinates.
- **Multi-Cell Range Selection:** `aria-multiselectable="true"`, selected cells set `aria-selected="true"`. Use a live summary region (*"Selected 40 cells from A1 to D10"*) to prevent screen reader verbal overload.

---

### C. TreeGrids (`role="treegrid"`)
- **Hybrid 2D & Tree Structure:** Combines 2D table grid with hierarchical tree expansion (`role="row"`, `role="gridcell"`, `aria-expanded="true|false"` on expandable rows).
- **Required Attributes:** `aria-level`, `aria-posinset`, `aria-setsize`, `aria-rowindex`, `aria-colindex`.
- **Focus Models:**
  - **Row-First Model:** Arrow keys navigate row to row; `ArrowRight` expands row or enters cell navigation; `ArrowLeft` collapses row or moves focus to parent row header.
  - **Cell-First Model:** Arrow keys navigate between cells; `ArrowRight`/`ArrowLeft` on expander cells toggle child row expansion.

---

## 2. Collaborative Rich Text Editors (draft-sensitive)

### A. ARIA roles and native markup

WAI-ARIA 1.3 is a Working Draft. Prefer native `<ins>`, `<del>`, and `<mark>` where they express the content, and do not claim draft-role interoperability without testing.
- `role="suggestion"`: Parent container for track-changes.
  - `role="insertion"`: Proposed added text.
  - `role="deletion"`: Proposed deleted text.
- `role="comment"`: Annotations attached to text span via `aria-details="comment-id"`.
- `role="mark"`: Contextual text highlighting.

### B. Keyboard Shortcuts & Announcements
- Global shortcut (e.g. `Alt+F10`) toggles focus between text caret and active comment card in sidebar.
- **Co-Authoring Telemetry:** Keep character-level and routine presence telemetry silent. If user research establishes a need, offer bounded macro-event announcements as a separate preference.

---

## 3. Custom Canvas & WebGL Visualizations

### A. Parallel Accessible DOM Tree (PAT)
Position invisible HTML elements (`tabindex="0"`, `role="button"`) or fallback HTML trees directly over visual canvas coordinates.

### B. Spatial Graph Navigation
- Implement directional arrow key navigation ($\leftarrow \rightarrow \uparrow \downarrow$) calculated via spatial 2D coordinates between graph nodes.
- Expose relationships only when the selected ARIA property accurately describes them; do not use `aria-controls` merely to mean “connected to.” Provide an equivalent semantic list/table view, using a tree only when the data is genuinely hierarchical and its keyboard pattern is implemented.

---

## 4. Multi-Step Wizard Flows

### A. Step Navigation & Focus
- Semantically label steps: `<nav aria-label="Checkout Progress"><ol><li aria-current="step">Step 1</li></ol></nav>`.
- Shift programmatic focus to new step heading (`<h2 tabindex="-1">`) upon step change.

### B. State & Error Management
- If automatic status speech is required, use one persistent, bounded announcer outside the routed subtree. Do not mirror the new step's full visible content in it.
- Validation error summary: focus a named summary container with links to invalid fields. Because focus already announces it, avoid also making the same container a live alert unless a tested exception requires it.
