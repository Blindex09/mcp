/**
 * ARIA attributes complete reference (2026) — WAI-ARIA 1.2 + 1.3 draft.
 * Grouped by category. Notes on deprecation and common misuse.
 *
 * Rule #1: use native HTML first. ARIA supplements, never replaces,
 * native semantics and behavior.
 */

/* ===================================================================
 * 1. ROLES — what an element IS (set once, rarely change)
 * =================================================================== */

/* --- Landmark roles (prefer native elements instead) --- */
// header / banner → <header>           (use <header>, NOT role="banner" unless site-wide)
// navigation → <nav>                    main → <main>
// complementary → <aside>               contentinfo → <footer>
// search → <search> (2024+; wrap a search form)
// form → <form> (use <form> + aria-label when name needed)
// region → named section (use <section aria-labelledby>)

/* --- Document structure roles --- */
// article, heading, list, listitem, paragraph, separator (when focusable),
// group (generic grouping with an accessible name), figure, caption,
// tab, tabpanel, tablist, table, row, cell, columnheader, rowheader,
// grid, gridcell, treegrid, definition, term, note, mark (highlighted)

/* --- Widget roles (custom components) --- */
// alert, alertdialog, dialog, banner, button (prefer <button>),
// checkbox (prefer <input type=checkbox>), combobox, gridcell,
// link (prefer <a href>), listbox, menu, menubar, menuitem,
// menuitemcheckbox, menuitemradio, option, progressbar, radio,
// radiogroup, scrollbar, searchbox, separator (resizable), slider,
// spinbutton, switch, tab, tabpanel, textbox, timer, toolbar, tooltip,
// tree, treeitem, treegrid

/* --- Abstract roles (do not use in HTML) --- */
// range, select, section, sectionhead, widget, composite, input,
// structure, window, landmark

/* --- Live region roles (announce dynamic changes) --- */
// alert     → implicit assertive + atomic (urgent errors); do not repeat aria-live
// status    → implicit polite + atomic (status updates); do not repeat aria-live
// log       → implicit polite (append-only logs); use only when auto-announcement is wanted
// marquee   → aria-live="off" (non-essential scrolling, rare)
// timer     → aria-live="off" (countdowns; announce manually if needed)
// progressbar → use <progress> or role="progressbar" with aria-valuenow

/* ===================================================================
 * 2. GLOBAL states & properties (usable on any element)
 * =================================================================== */

// aria-label        string  — accessible name when no visible text
// aria-labelledby  idref(s)— points to visible text for the name (preferred over aria-label)
// aria-describedby idref(s)— supplementary description (tooltip, hint, error)
// aria-description string  — programmatic description (1.3; rare, not widely supported)
// aria-details     idref   — pointer to extended info (supersedes aria-describedby; AT support uneven in 2026)
// aria-hidden      true|false — removes from AT entirely (use on decorative/duplicate)
// aria-disabled    true|false — disabled but still focusable (vs `disabled` attr which removes focus)
// aria-hidden + aria-disabled often used together for icons

// aria-live        off|polite|assertive — live region politeness
// aria-atomic      true|false — announce the WHOLE region vs just the changed nodes
// aria-relevant    additions|removals|text|all — what changes to announce (default: additions text; rarely override)
// aria-busy        true|false — "this region is updating, hold off" (use during async loads)
// aria-current     page|step|location|date|time|true|false — mark the current item (nav, breadcrumbs, wizards)

// aria-keyshortcuts string — declare keyboard shortcuts (e.g. "Alt+Shift+S")
// aria-roledescription string — override the announced role name ("carousel", "slide")
// aria-brailleroledescription string — braille-specific role description (1.2)
// aria-braillelabel  string — braille-specific accessible name (1.2)
// aria-errormessage  idref — pointer to an error message (paired with aria-invalid; 1.2)
// aria-flowto      idref(s) — suggest next reading order (rarely needed)
// aria-owns        idref(s) — declare ownership when DOM nesting doesn't reflect it (combobox→popup)

/* ===================================================================
 * 3. WIDGET states (change at runtime with interaction)
 * =================================================================== */

// aria-expanded    true|false|undefined — is a collapsible open? (accordion, menu, combobox, tree)
// aria-pressed     true|false|mixed — toggle button state
// aria-checked     true|false|mixed — checkbox/radio/menuitemcheckbox/menuitemradio/treeitem
// aria-selected    true|false|undefined — listbox option, tab, treeitem, gridcell
// aria-haspopup    false|true|menu|listbox|tree|grid|dialog — declares a popup type
// aria-controls   idref — points to the element this controls (menu button → menu, tab → tabpanel)
// aria-activedescendant idref — VIRTUAL focus in composite widgets (combobox, listbox, tree, grid)
//   Use when DOM focus stays on the container but AT should report a child as active.
// aria-orientation horizontal|vertical — tablists, menus, sliders, toolbars
// aria-sort        ascending|descending|none — sortable column header
// aria-multiselectable true|false — listbox/tree/grid allowing multiple selections
// aria-readonly    true|false — grid/listbox/combobox: focusable but not changeable
// aria-required    true|false — form field, combobox, listbox
// aria-invalid     true|false|grammar|spelling — marks a field with an error
// aria-placeholder string — placeholder text (prefer <input placeholder> for inputs)
// aria-autocomplete inline|list|both|none — combobox autocomplete behavior
// aria-valuenow    number — current value of slider/spinbutton/progressbar/scrollbar
// aria-valuetext   string — human-readable value (e.g. "3 of 10" instead of "3")
// aria-valuemin    number — minimum value
// aria-valuemax    number — maximum value
// aria-level       integer — depth in a tree or heading hierarchy
// aria-setsize     integer — total items in a group (1 of N)
// aria-posinset    integer — position in a group
// aria-colcount / aria-rowcount — total columns/rows (grids)
// aria-colindex / aria-rowindex — position (grids)
// aria-colspan / aria-rowspan — span (grids, like HTML colspan/rowspan)
// aria-rowheader / aria-colheader — idrefs to header cells (grids)
// aria-multiline   true|false — textbox
// aria-dropeffect / aria-grabbed — DRAG AND DROP (DEPRECATED in ARIA 1.2 — do not use)

/* ===================================================================
 * 4. DEPRECATED / avoid in 2026
 * =================================================================== */
// aria-dropeffect, aria-grabbed — removed; use HTML drag-and-drop instead
// role="application" on generic containers — disables screen reader shortcuts, rarely right
// aria-relevant — almost never override; default "additions text" is correct
// aria-live="rude" — removed from spec; use "assertive"
// role="region" without an accessible name — creates an unnamed landmark (no-op)

/* ===================================================================
 * 5. The accessible name calculation (priority order)
 * =================================================================== */
// 1. aria-labelledby (points to visible text)  ← preferred
// 2. aria-label (string)                       ← use when no visible text
// 3. Element's own content (button text, link text)
// 4. <label for> (form controls) or <caption> (tables) or <title> (SVG)
// 5. title attribute (last resort; inconsistently announced)
//
// Hide visible-but-redundant label text with .sr-only to keep it as the
// accessible name source while keeping aria-labelledby clean.

/* ===================================================================
 * 6. aria-activedescendant vs roving tabindex (when to use which)
 * =================================================================== */
// Both solve "one tab stop, many items" in composite widgets.
//
// ROVING TABINDEX:
//   - The active item gets tabindex="0", others get "-1".
//   - Call .focus() on the active item to move real DOM focus.
//   - Simpler to test; works everywhere.
//   - Best for: tabs, menus, toolbars, radio groups, simple listboxes.
//
// aria-activedescendant:
//   - DOM focus stays on the container (e.g., the combobox input).
//   - Container's aria-activedescendant = id of the highlighted child.
//   - Required when focus must NOT move (combobox text caret must stay).
//   - Best for: combobox (input keeps caret), grids, complex listboxes/trees.
//
// Pitfall: aria-activedescendant must ALWAYS resolve to an element that
// exists in the DOM. Virtualized lists must render the active option.
