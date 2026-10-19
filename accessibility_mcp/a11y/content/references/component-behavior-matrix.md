# Component behavior matrix: what it must do, must not do, and what the screen reader receives (2026)

Origem: Qaaccessibility e este servidor. Ao mudar este guia, mudar também lá, na mesma entrega. Sources: WAI-ARIA Authoring Practices
(APG), WCAG 2.2, HTML Standard, developer.android.com (Compose semantics, read 2026-10-19), angular.dev best-practices/a11y (read
2026-10-19), vuejs.org/guide/best-practices/accessibility (read 2026-10-19) and Scott O'Hara's article on lists and Safari (published 2019-01-12,
updated 2023-01-30). The iOS points below are NOT confirmed in an official source: the Apple documentation page did not render for reading on
2026-10-19; confirm them on developer.apple.com before relying on them.

How to read it. Each component has: MUST (the contract), MUST NOT (the defects we actually see), TREE (what the browser hands to
the screen reader: role, name, state; this is deterministic and the MCP measures it), SPEECH (what a screen reader typically says;
it varies by screen reader, version, browser and settings, so never assert exact words as fact), PROBE (the `a11y_probe` kind that
measures the behavior) and the stack notes. A probe result of `met: null` is "could not measure", never a pass.

## 1. Headings

- MUST: real `h1`-`h6` for anything that works as a title; one `h1` per page or view; levels follow the outline without skipping;
  visual size comes from CSS, never from the level number.
- MUST NOT: a `div`/`span` styled big as a title (the tree has no heading); a heading chosen for its size; headings used as the
  title of every card inside a list when the list items are links (prefer the link; see lists).
- TREE: `heading "Text" [level=2]`. SPEECH: "heading level 2, Text". Navigation by heading is the main way people scan a page.
- TOOLS: `a11y_page_map` (outline, level_jumps, first_level), `a11y_aria_snapshot`.

## 2. Lists

- MUST: `ul`/`ol`/`dl` for real lists; markers come from CSS. A list of links is `ul > li > a`.
- MUST NOT: `div` rows with a typed bullet; `list-style:none` on a list that carries meaning in Safari/VoiceOver without
  `role="list"` (removing the marker can drop the list semantics there; check the tree in that browser); a heading inside every
  `li` just to style the card title (the screen reader says "list of N items, heading level 2" for every item).
- TREE: `list > listitem`. SPEECH: "list with N items", then "1 of N" style position. TOOLS: `a11y_page_map` (`lists.details`,
  `lists_with_headings_in_items`).

## 3. Links and buttons

- MUST: link = goes somewhere (`a href`), button = does something (`button`). Name says the destination or action and is unique in
  its context; visible label is contained in the accessible name (2.5.3). A new-window link says so.
- MUST NOT: `div`/`span` with `onclick` (no role, not focusable, no Enter/Space); `a` without `href` used as a button; "click
  here"; the same name for different destinations (page_map `same_text_different_destination`); `role="button"` without Space/Enter
  and tabindex.
- TREE: `link "Name"` / `button "Name"`. SPEECH: "link, Name" / "button, Name". PROBE: `tab_walk` (every stop, names, focus
  style), `target_size` (24x24 CSS px minimum, 2.5.8; real buttons need `min-height`/padding, a bare `button` often measures about 21 px).
- Duplicate names across one page (two "Delete project" buttons) need a context: put the controls in a named `group`/region or
  rename. This site's own examples are wrapped in `role="group" aria-label="..."` for that reason.

## 4. Images

- MUST: informative = alt that says what it conveys in context; decorative = `alt=""`; image inside a link = the alt names the
  destination; complex image = short alt plus a long description nearby.
- MUST NOT: missing `alt` (the screen reader reads the file name); alt that repeats the adjacent text; "image of"; text baked into
  images without the same text available.
- TREE: `img "alt"` or nothing for `alt=""`. TOOLS: `a11y_page_map` images, axe `image-alt`. Whether the alt is good is your
  judgment from the context (never a rule on words).

## 5. Form field and form errors

- MUST: every field has a programmatic label (`label for`, or `aria-label`/`aria-labelledby`); required and format hints are in the
  label or `aria-describedby`; `autocomplete` on personal data fields (1.3.5). On error: the invalid field has `aria-invalid="true"`,
  the message is tied to the field with `aria-describedby`, focus goes to the first invalid field (or to an error summary that links
  to it), and the error is announced (role=alert / live region / focus move). Fix the message so it says how to correct it (3.3.3).
- MUST NOT: placeholder as the only label; error shown only by red color or an icon; a red sentence next to the field with no
  link to the field and no focus move; clearing what the person typed; blocking paste on password fields.
- TREE: `textbox "Email" [invalid] ` plus description. SPEECH: "Email, edit, invalid entry, <message>".
- PROBE: `form_errors` (target = submit button or a field). The probe measures: `campo_invalido_marcado`, `erro_descrito_no_campo`,
  `foco_vai_ao_erro`, `erro_anunciado`. If every field is already valid for the browser (no `required`, no constraint) the probe
  returns `met: null` and lists any new text; a purely custom message with no constraint is still a defect you judge from the tree.

## 6. Dialog (modal)

- MUST: opens from a keyboard-reachable trigger; focus moves inside; dialog has role dialog/alertdialog and an accessible name
  (`aria-labelledby` to its title); modal (`<dialog>` opened with `showModal()` or `aria-modal="true"` plus inert background); Tab
  and Shift+Tab stay inside; Escape closes; on close focus returns to the trigger (or a sensible place if the trigger is gone).
- MUST NOT: a `div` that appears but never takes focus; focus that leaks to the page behind; a dialog with no name; Escape
  swallowed; opening on page load without a reason; nested scrolling that hides the buttons.
- TREE: `dialog "Delete this project?"`. SPEECH: "dialog, Delete this project?" then the focused control. A native `<dialog>` with
  `showModal()` is modal without `aria-modal`; what it can still lack is the name.
- PROBE: `dialog` (target = the trigger). If nothing visible with a dialog role opens, the probe says so; whether the thing
  was meant to be a dialog is your call. In Firefox the Tab-loop check can be `null` (focus leaves for browser UI).

## 7. Disclosure and accordion

- MUST: the trigger is a `button` (or `summary` of `details`) with an exposed state: `aria-expanded` true/false on the button, or
  the native open state of `details`; Enter and Space toggle; focus stays on the trigger; hidden content is really hidden (not just
  offscreen) when collapsed. Accordion headers are buttons inside headings.
- MUST NOT: `div` with `onclick`; `aria-expanded` that does not follow the real visibility; moving focus into the panel on
  open without reason; `details` re-implemented with divs.
- TREE: `button "Q" [expanded=false]` or `group`/`details` with `summary`. SPEECH: "button, collapsed" then "expanded".
- PROBE: `disclosure` (target = the button or the `summary`). Native `details`/`summary` passes: the state is native, no `aria-expanded` is needed.
- Navigation submenus are disclosures, not `role="menu"` (menu is for application command menus).

## 8. Tabs

- MUST: `role="tablist"` containing `role="tab"`; each tab has `aria-selected` and `aria-controls` to a `role="tabpanel"` with
  `aria-labelledby`; a single tab stop (selected tab `tabindex=0`, others `-1`); ArrowLeft/Right move focus (Up/Down if vertical),
  Home/End jump; Tab from the selected tab enters the panel; activation is automatic or manual (both valid).
- MUST NOT: `div`s with click handlers; every tab in the Tab order; arrows that do nothing; hidden panels left in the tree.
- TREE: `tab "Profile" [selected]`, `tabpanel "Profile"`. SPEECH: "tab, selected, 1 of 3". PROBE: `tabs` (target = any tab).

## 9. Menu button (action menu)

- MUST: the button has `aria-haspopup="menu"` and `aria-expanded`; Enter, Space or ArrowDown opens; focus goes to the first item;
  ArrowUp/Down move, Home/End jump, Escape closes and returns focus to the button, Tab closes; items are `menuitem`.
- MUST NOT: `role="menu"` on site navigation; a menu that opens only on hover or click; focus left on the button after opening.
- PROBE: `menu` (target = the button). For hover-only menus see `page_map.hover_reveals`.

## 10. Combobox (and autocomplete)

- MUST: the input has `role="combobox"` (native `input` with `list` or `select` is exposed natively), `aria-expanded`,
  `aria-controls` to a `listbox`; ArrowDown opens/moves, the active option is exposed with `aria-activedescendant` (focus stays
  in the input) or by moving focus; Enter picks and closes; Escape closes and keeps focus in the field; result count changes are
  announced politely.
- MUST NOT: a plain text input with a `div` list that only reacts to the mouse; announcing every keystroke; closing the list
  on focus loss that blocks option clicks.
- TREE: `combobox "City" [expanded]`, `option "Recife" [selected]`. PROBE: `combobox` (target = the field). Native popups
  (`datalist`, `select`) are not observable in the DOM: the probe returns `null` for those checks, which is not a pass.

## 10b. Listbox, tree view, tooltip, carousel and sortable table

- LISTBOX (probe `listbox`). MUST: `role="listbox"` with a name, options `role="option"`, one Tab stop (the list with `aria-activedescendant`, or the current option with `tabindex="0"`), ArrowUp/Down, Home/End, Space/Enter select with `aria-selected`. MUST NOT: `div` rows with click handlers; one Tab stop per option.
- TREE VIEW (probe `tree`). MUST: `role="tree"` with a name, `role="treeitem"`, `aria-expanded` on every parent, one Tab stop (roving), ArrowDown/Up move, ArrowRight opens (or enters the first child), ArrowLeft closes (or goes to the parent), Home/End. MUST NOT: nested `ul` opened only by a click on a `span`.
- TOOLTIP (probe `tooltip`). MUST: appears on focus as well as hover, element `role="tooltip"` tied to the control by `aria-describedby`, Escape closes it without moving focus, the pointer can move onto it without it vanishing (WCAG 1.4.13). MUST NOT: `title` alone (not shown for keyboard focus); a tooltip only on `mouseenter`.
- CAROUSEL (probe `status_update` on the next button). MUST: `aria-roledescription="carousel"` plus a name, slides as `role="group"` `aria-roledescription="slide"` with "1 of 3", named controls ("Previous slide"), the change announced in a status region that already exists; with automatic rotation also a pause control FIRST in the tab order, pause on hover and focus, and no rotation under `prefers-reduced-motion` (WCAG 2.2.2). MUST NOT: controls named only with a glyph (the screen reader says the symbol or nothing).
- SORTABLE TABLE (probe `status_update` on the header button). MUST: a `button` inside the `th`, `aria-sort` on the sorted column, the new order announced in a status region. MUST NOT: a clickable `th` that is not focusable.

## 10c. CSS: what the style sheet changes for the screen reader, the keyboard and the reader

- FOCUS: MUST keep a visible indicator (the default ring or a `:focus-visible` ring with 3:1 contrast). MUST NOT use `outline: none` without a replacement. Measure with `a11y_focus_style` (it lists what `:focus` changes; works with `css:` targets).
- HIDDEN TEXT: `display:none` and `visibility:hidden` remove the text from the tree (the screen reader does not read it). Text meant only for the screen reader uses the visually-hidden technique (clip, 1 px, absolute). `aria-hidden` removes from the tree too.
- LIST MARKER: in Safari with VoiceOver, `list-style:none` removes the list semantics; WebKit called it a purposeful change, and `role="list"` on the `ul` restores it (Scott O'Hara, published 2019-01-12, updated 2023-01-30; the update says a nested list inside a `nav` is still exposed as a list). The Chromium and the Playwright WebKit measured here (2026-10-19) still expose a list, so this site cannot reproduce it and labels the case "depends on the browser, not measured here". Add `role="list"` anyway.
- HOVER MENUS: a submenu shown only by `:hover` is unreachable by Tab (measure: links in the code against links Tab reaches). Show it also with `:focus-within`, or use a disclosure button.
- TEXT SPACING (WCAG 1.4.12): fixed `height` with `overflow:hidden` clips text when the person raises letter, word and line spacing. Use `min-height`. The measure depends on the font size: measure with the site's own styles.
- CONTRAST: axe measures fixed colors; also audit `color_scheme=dark` and `forced_colors`.
- MOTION: animations must stop or shrink under `@media (prefers-reduced-motion: reduce)`. Measure with the `reduced_motion` persona (computed `animation-name`).

## 11. Live regions, status and alerts

- MUST: the live region element exists in the DOM before its text changes; `role="status"` (polite) for results and saved
  messages, `role="alert"` (assertive) only for urgent errors; the message is short and says what changed.
- PROBE: `status_update` (target = the button): checks that the change reaches someone who cannot see it, that the region already existed before the text (`fresh` in the live observer), and that focus did not fall to the body. `role="alert"` born with its text is usually spoken, so it is not flagged.
- MUST NOT: inserting the region and its text in the same tick and expecting speech; announcing on every keystroke or timer;
  `aria-live` on a large container that re-renders; relying on color/animation as the only signal.
- TOOLS: `a11y_act` and `a11y_announce` report what was announced; page_map lists live regions. Whether a given screen reader
  speaks it depends on timing and the screen reader; confirm with a real one when it matters.

## 12. Route change in a single-page app (and any content swap without reload)

- MUST: update `document.title`; move focus to the new view (the `h1` with `tabindex="-1"`, or the main container) or announce the
  change in a status region; update `aria-current` on the active nav link; restore scroll and focus sensibly on Back.
- MUST NOT: leave focus on a link that no longer exists (focus falls to `body`); change the content silently; announce a title on
  first load.
- PROBE: `route_change` (target = the link or button): `titulo_muda`, `foco_nao_se_perde`, `troca_perceptivel`. A jump to an
  in-page anchor (same document, only the fragment changes, same h1) reports the title check as `null`.
- Angular: subscribe to `NavigationEnd` and move focus yourself; use `ariaCurrentWhenActive` on `RouterLinkActive`; `LiveAnnouncer`
  from the CDK `a11y` package announces via `aria-live` (angular.dev, read 2026-10-19). Vue (official guide, read 2026-10-19): after a route change, call `focus()` on a `span` with `tabindex="-1"` placed just before the skip link (watch the route); the guide says nothing about
  the page title or live regions, so do both yourself (title, announcement, or focus on the new heading as this site does); `useId()` gives unique ids for label and `aria-labelledby` links in reusable components. React: no router does it for you.

## 13. AJAX, lazy loading and infinite lists

- MUST: loading state is perceivable (`aria-busy` on the region, a status message "Loading results", then "N results"); new
  content does not steal focus unless the person asked for it; on error say what failed and offer a retry; "load more" moves
  focus to the first new item or keeps it on the button and announces the count; infinite scroll has a keyboard alternative
  and a reachable footer.
- MUST NOT: a spinner with no text; replacing the whole list under the focused item; removing the "Load more" button that holds the focus (focus falls to the body); timeouts that remove content before it is read.
- PROBE: `status_update` on the button that starts the request. On failure the message goes to a `role="alert"` region that already exists, says what to do, and offers "Try again".
- STREAMING AI ANSWERS: do not update a live region word by word (the screen reader talks over itself). Write the answer in an element that does not announce, keep focus in the field, and announce once at the end in a status region ("Answer ready"). The number of announcements after one action is a measured fact in this site (chat example): count them, do not guess.

## 14. Tables

- MUST: real `table` for tabular data, `caption`, `th` with `scope`, headers associated in complex tables; no layout tables.
- MUST NOT: grid made of divs with no roles; `th` used for styling; sort buttons with no state (`aria-sort`).
- TREE: `table`, `columnheader`, `cell`. SPEECH: row/column headers are read as the person moves between cells (table mode).

## 15. Stack notes: where the same contract goes wrong

| Stack | Typical defect | What to check and how |
|---|---|---|
| HTML | wrong element for the job; missing label/alt/lang | `a11y_aria_snapshot`, `a11y_page_map`, axe |
| CSS | `display:none` vs offscreen; `list-style:none` drops list in Safari; focus ring removed; content only via `::before`; hover-only reveal; text clipped at 320 px or with user text spacing; contrast in dark and forced-colors | `a11y_open` with `color_scheme`, persona `forced_colors`/`low_vision`, `a11y_stress`, `page_map.hover_reveals`, `a11y_focus_style` |
| JS | click-only handlers; focus not managed after DOM updates; `tabindex>0`; timers that remove content | `tab_walk`, `a11y_reach`, `a11y_act`, the contract probes |
| AJAX/fetch | silent updates, focus lost when the DOM node is replaced, no error state | `a11y_act` then read the announcement/tree diff; section 13 |
| React / Vue / Svelte / Angular, same five failures | the compiler does not warn about a `div` with a click handler (only a linter such as eslint-plugin-jsx-a11y, eslint-plugin-vuejs-accessibility or the angular-eslint template rules, if configured); the Svelte compiler DOES warn (`a11y_click_events_have_key_events`, `a11y_no_static_element_interactions`), so do not silence it with `svelte-ignore`; a conditional render (`{x && ...}`, `v-if`, `@if`, `{#if}`) creates a live region together with its text; none of the routers moves focus or the title for you | build the real component and probe the built page (this site does, for the four) |
| React | `key` re-mounting the focused node; `useId` for label/description ids; effects that move focus on every render; portals for dialogs (focus return); synthetic `div` buttons; fragments hiding landmarks | probes on the built page, not on the source |
| Angular | no focus move on `NavigationEnd`; `*ngIf` removing a live region before it speaks; use CDK `cdkTrapFocus`, `LiveAnnouncer`, `FocusMonitor`; bind ARIA with `[attr.aria-*]` or `[aria-label]` as the version supports | probes; read `specialist-angular-framework` |
| Vue | `v-if` removing the live region/focused node; `v-show` leaves content in the tree if only the style hides it from sight (it uses `display:none`, which hides it); route announcer is your job | `route_change`, tree diff |
| Svelte | compiler warnings `a11y_click_events_have_key_events` and `a11y_no_static_element_interactions` (and others) are real signals: fix with a native element, not by suppressing with `svelte-ignore` | read the warning list on svelte.dev/e; probes |
| Web Components | the site's CSS does NOT reach inside a shadow root (a `button` inside measured 21 px high until the shadow got its own style); closed shadow roots hide the tree from the dossier; `delegatesFocus`; ids do not cross shadow boundaries (`aria-labelledby`/`for` break); form-associated custom elements need `ElementInternals` for labels and validity | `a11y_dossier` (crosses open shadow DOM), `a11y_aria_snapshot`; `specialist-web-components` |
| Android (Compose) | missing `contentDescription` on icons (null when a text label sits beside it); custom clickables without `Role`; no `stateDescription`; many nodes read one by one instead of `semantics(mergeDescendants = true)`; `liveRegion` (`Polite` normally, `Assertive` rarely, never on fast-updating text); `heading()` for section titles; `clickable`/`toggleable` merge descendants already | official docs, TalkBack on a real device or emulator; this MCP has no Android runner (declare as not verified) |
| iOS (SwiftUI/UIKit) | custom views without `accessibilityLabel`/traits; decorative images not hidden; `UIAccessibility.post(notification:)` for announcements and layout/screen changes | developer.apple.com; VoiceOver on a real device; no iOS runner here (declare as not verified) |

Always finish a stack review by saying what was NOT verified: real screen reader speech, real devices, untested flows.
