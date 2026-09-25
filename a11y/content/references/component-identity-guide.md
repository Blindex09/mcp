# Component Identity Guide — what is this element, in THIS site? (2026)

Use this guide to decide what an interactive element **really is** for the people using this site, then make its
semantics and behavior match — without changing how the site looks. The decision is a judgment: read the facts
(`a11y_dossier`), probe the behavior (`a11y_act`, `a11y_reach`, `a11y_announce`), compare with the site's own
conventions, and justify. Do not classify by tag name, class name, or a keyword in the label.

## 0. Principles

1. **Meaning over appearance.** A control is what it *does for the user*, not what it looks like. A box that looks
   like a text field but chooses among fixed options is a choice control; a "dropdown" that navigates is a menu of links.
2. **Evidence from behavior.** State the observed evidence for every verdict: what opened, what changed in the
   accessibility tree, what the keys did, what got announced.
3. **Respect the site's design.** Fix semantics, roles, names, states and keyboard behavior first. Change visuals only
   when they are the problem, and then inside the site's own design language (`a11y_design_tokens`).
4. **Native first.** If a native element fits the meaning, prefer it; use ARIA patterns only when a native one cannot
   express the behavior. Reuse the site's existing classes/tokens so the look stays identical.
5. **Say what you could not verify.** If a verdict rests on a guess, mark it as such.

## 1. Questions that reveal identity

Ask these of each element, using the dossier and probes:

- **Can the user type free text, or only choose?** (`editable`, what happens on typing, whether unmatched text is accepted)
- **Is there a set of options? Where do they live?** (`datalist_options`, `native_options`, `popup_items`, `popup_item_kinds`)
- **Do options filter as you type? Is one option "selected" and its value kept?**
- **Do the options go somewhere (navigate) or set a value/run a command?** (`popup_links`, URL change after activation)
- **Does it show/hide content in place, or open a floating layer?** (`expanded`, `popup_visible`, focus after opening)
- **What do Escape, Enter, Space, Arrow keys, Home/End and Tab do?**
- **What is it called and described for a screen reader?** (`a11y_announce`; does the name match the visible text?)
- **What does the rest of the site do for the same job?** (consistency: the same pattern must look and behave the same)

## 2. Identity table (patterns and their contract)

| Meaning for the user | Typical evidence | Expected semantics and keys |
|---|---|---|
| **Text field** | Free text; no fixed option set | native `<input>`/`<textarea>` + a real `<label>`; `autocomplete` when it is personal data |
| **Combobox** (editable + suggestions) | Free text **and** a list of suggestions/filtered options | native `<input list>` + `<datalist>` for simple cases; otherwise APG combobox: `role=combobox`, `aria-expanded`, `aria-controls`, `aria-autocomplete`, Arrow Down/Up to move, Enter to accept, Escape to close |
| **Select / dropdown list** (choose one, no typing) | Fixed options, value shown in the control | native `<select>` whenever possible; a custom listbox only if native cannot be styled enough, with the full listbox contract |
| **Listbox** (always-visible options) | Options visible in a box, one or many selected | `role=listbox`/`option`, `aria-selected`; arrows move; Space/Enter select |
| **Menu button (actions)** | Trigger opens commands that *do* something (rename, delete) | button + `aria-haspopup="menu"`; `role=menu`/`menuitem`; arrows, Escape returns focus to the trigger |
| **Navigation disclosure ("dropdown menu" of links)** | Trigger reveals links to pages; items navigate | a button with `aria-expanded` + `aria-controls` opening a list of **links** inside `<nav>`; **not** `role=menu` (menus are for application commands) |
| **Disclosure / accordion** | Reveals content in place, pushes the rest down | `<button aria-expanded>` (or `<details>/<summary>`); Enter/Space toggle; no arrow-key contract required |
| **Tabs** | Switches which panel of the same view is shown | `role=tablist/tab/tabpanel`, roving tabindex, arrows between tabs, Tab moves into the panel |
| **Dialog** | Blocks or demands attention over the page | native `<dialog>`/`role=dialog`, name, initial focus, containment, Escape, focus returns to the trigger |
| **Toggle / switch / checkbox** | Two states, immediate effect vs. form value | button `aria-pressed`, `role=switch`, or checkbox; state announced |
| **Link vs button** | Goes somewhere vs. does something | `<a href>` navigates; `<button>` acts. A "button" that changes the URL is a link |

The table is a starting point for *your* reasoning, not a lookup: real components mix traits. When they conflict,
decide by what the user is trying to do and say why.

## 3. Read the site's conventions before deciding

- Look at the other widgets of the same kind (`a11y_dossier` on the whole page). If the site already has a working
  pattern, extend it instead of introducing a second one.
- Check the copy: labels and headings tell what the site itself calls the thing.
- Check position and context (`context.landmark`, `context.heading`): a control inside `<nav>` that reveals links is
  navigation; inside a form that sets a value is a form control.

## 4. Deliver a verdict per element

For each element you reviewed, report:

1. **What it is (for users)** and **what it is exposed as today** (role/name/states from the dossier/`a11y_announce`).
2. **Evidence** — the probes you ran and what they showed.
3. **Gap** — where exposure or behavior does not match the meaning (wrong role, missing state, missing key, wrong name,
   focus lost, announcement missing).
4. **Fix that keeps the design** — the smallest change to semantics/behavior; name the existing classes/tokens to keep;
   link the relevant example (`a11y_get_example`) or guide section.
5. **Confidence and what remains manual** (real screen reader, real device).

Never claim "accessible" because an automated audit is green. Green means "no known rule failed", nothing more.
