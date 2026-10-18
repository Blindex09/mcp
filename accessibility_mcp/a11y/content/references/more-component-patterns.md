# More Component Patterns — beyond the classic eleven (2026)

`ui-components-apg` covers modals, menus, accordions, tooltips, comboboxes, tabs, trees, data tables, carousels and drag-and-drop.
Real sites are full of other widgets. This guide gives, for each, **what it is for the person**, **what to look for in the facts**
(`a11y_dossier`, `a11y_page_map`), **how to prove its behavior** (`a11y_act`, `a11y_reach`) and **the contract to expect**.
Use it with `component-identity-guide`: decide identity by behavior and context, never by class name or tag.

## 1. Toolbar
- **Meaning:** a group of related controls used together (formatting, playback).
- **Facts:** several buttons in a row inside one container, one Tab stop expected; `role=toolbar` or none.
- **Prove:** Tab into the group once, ArrowLeft/Right move between controls, Tab leaves the group.
- **Contract:** `role=toolbar` + accessible name, roving tabindex (or `aria-activedescendant`), orientation stated when vertical. If every button is a separate Tab stop and the group is long, consider a toolbar.

## 2. Slider / range
- **Meaning:** choose a number or range by dragging.
- **Facts:** native `input[type=range]` (best), or `role=slider` with `aria-valuemin/max/now/text`, or a draggable `div` (mouse-only).
- **Prove:** focus it; ArrowLeft/Right (±step), Home/End, PageUp/Down; check the value is announced with units.
- **Contract:** native input when possible; custom needs all `aria-value*`, keyboard steps, visible focus, target size, and `aria-valuetext` for non-numeric values. Two-thumb ranges need two named sliders.

## 3. Switch / toggle button / checkbox
- **Meaning:** on/off. A *switch* takes effect immediately; a *checkbox* is part of a form submitted later; a *toggle button* changes the meaning of an action ("Mute").
- **Facts:** `role=switch` / `aria-checked`, `aria-pressed`, `input[type=checkbox]`; label wording ("Enable notifications" vs "Notifications").
- **Prove:** Space toggles; state change is exposed (tree diff) and announced; the label does not flip with the state (pressed buttons keep the same name).
- **Contract:** native checkbox or `role=switch` with `aria-checked`; toggle buttons use `aria-pressed` and a stable name.

## 4. Radio group / segmented control
- **Meaning:** choose exactly one of a few visible options.
- **Facts:** `input[type=radio]` with shared `name`, or `role=radiogroup` with `role=radio`, or **links/buttons styled as options** (a size selector made of `<a href="#">` is really a radio group).
- **Prove:** Tab enters the group once; arrows move *and* select; Space selects the focused one.
- **Contract:** `fieldset/legend` or `radiogroup` with a name; roving tabindex; `aria-checked`. Do not build it as independent buttons/links with no shared state.

## 5. Date picker
- **Meaning:** choose a date. Often a text field **plus** a popup calendar.
- **Facts:** text input with a button, a grid of day buttons (`role=grid`, `gridcell`), month/year controls, or native `input[type=date]`.
- **Prove:** the field accepts typed dates (with a format hint); the calendar button opens a dialog; arrows move by day/week, PageUp/Down by month, Home/End within the week, Escape closes and returns focus; the selected day is announced with full date.
- **Contract:** typing must always be possible (WCAG 3.3.7/2.5.7 spirit); popup is a dialog (`role=dialog`, name, focus return); each day has a full accessible name ("Friday, 26 September 2026"); today/selected/disabled states exposed.

## 6. Breadcrumbs
- **Meaning:** where the person is in the site hierarchy.
- **Facts:** an ordered list of links inside `<nav>`, last item the current page.
- **Contract:** `<nav aria-label="Breadcrumb">` + `<ol>`, `aria-current="page"` on the last item; separators are decorative (CSS or `aria-hidden`).

## 7. Pagination
- **Meaning:** move through pages of results.
- **Facts:** row of numbered links/buttons, "Next/Previous", current page styled.
- **Contract:** `<nav aria-label="Pagination">` with a list of links; `aria-current="page"` on the current one; links named "Page 3" (not just "3") or with visually hidden context; previous/next disabled state exposed; loading a new page moves focus or announces the change.

## 8. Search
- **Meaning:** find content, usually with suggestions and results.
- **Facts:** `role=search` region, input `type=search`, a submit control, an autocomplete list (then it is a **combobox**), a results container.
- **Prove:** results update is announced (live region with the count), focus does not jump unexpectedly, empty result states are explained.
- **Contract:** `role=search` landmark, visible label or clear accessible name, status message for result counts.

## 9. Toast / notification / alert
- **Meaning:** feedback that appears without the person moving focus.
- **Facts:** an element that gains text after an action; `role=status/alert` or `aria-live` present *before* the text changes; auto-dismiss timing.
- **Prove:** after the action, `a11y_act` shows `announcements`. **No announcement = silent to a screen reader.**
- **Contract:** `role=status` (polite) for success, `role=alert` (assertive) for errors; the container exists from load; enough time to read (WCAG 2.2.1); a way to dismiss or keep it.

## 10. Popover / disclosure panel (non-modal)
- **Meaning:** extra content or controls attached to a trigger, without blocking the page.
- **Facts:** trigger with `aria-expanded`/`aria-controls` or the `popover` attribute; panel not modal (page still interactive).
- **Prove:** Enter/Space opens; Escape closes and returns focus to the trigger; Tab order flows into the panel and on.
- **Contract:** button trigger, `aria-expanded`, panel after the trigger in DOM (or managed focus), no focus trap.

## 11. Stepper / wizard
- **Meaning:** a multi-step task.
- **Facts:** step indicators, Back/Next buttons, a heading that changes per step, a progress bar.
- **Prove:** moving to the next step moves focus to the new step heading (or announces it); errors are announced and linked to fields; the current step is exposed.
- **Contract:** ordered list of steps with `aria-current="step"`, heading focus management, a summary of progress, no loss of entered data on Back.

## 12. File upload
- **Meaning:** attach files.
- **Facts:** `input[type=file]` (native, best), a styled button that triggers it, a drop zone (mouse-only if it is the only path).
- **Contract:** keyboard-operable trigger; drop zone never the only way; selected file names and errors are announced; progress is exposed (`progress`/`aria-valuenow`).

## 13. Loading / skeleton / progress
- **Meaning:** something is being fetched.
- **Facts:** spinner or skeleton with no text; `aria-busy`; a `progress` element.
- **Contract:** loading state announced politely once (not every tick), `aria-busy` on the region being updated, focus not lost when content arrives, a way to know it finished.

## 14. Carousels, tooltips, data tables, drag and drop
See `ui-components-apg`; complex data grids, editors and canvases in `complex-components`.

## How to report a pattern review

For each widget: what it is (with the behavioral evidence), what it exposes today, the gap against the contract above, the smallest fix that
keeps the site's design, and what could not be verified (real screen reader, real device). Do not force a widget into a pattern it is not:
if two fit, say which behaviors decide it.
