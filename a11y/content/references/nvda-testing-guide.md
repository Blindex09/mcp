# NVDA Screen Reader Testing Guide (2026)

> **Before opening NVDA:** `a11y_aria_snapshot` shows the accessibility tree a screen reader is given and `a11y_tab_order`
> shows the keyboard order, both via the Accessibility MCP server. Use them to find missing/duplicated names and focus problems
> first; they do not replace listening to the real screen reader.


> Compiled from NV Access 2026.1 / 2026.1.1 release notes, the official User Guide & Key Commands, the TetraLogical NVDA HTML Support matrix (Feb 2026), and 2026 developer testing guides. NVDA is free and open-source (GPL) — download from nvaccess.org.

## Current state (2026)
- **Latest stable**: NVDA 2026.1.1 (patch for 2026.1, May 2026). Next beta: 2026.2.
- Min OS: Windows 10 (22H2). Dropped: Windows 8.1, 32-bit, ARM. Now 64-bit Python.
- **Best test browser**: Firefox (most reliable), Chrome/Edge also supported.
- 2026.1 web highlights: **`aria-errormessage` now reported** (Chrome + Firefox) — a major ARIA addition; spelling/grammar errors can play a sound; no longer treats 0-size controls as invisible (verify "sr-only" helpers aren't suddenly exposed).

## Browse mode vs Focus mode
| Mode | Purpose | Behavior |
|---|---|---|
| **Browse** (default) | Read the document | Cursor keys move text; single-letter quick-nav works |
| **Focus** ("forms mode") | Interact with a control | Keys pass through; type into fields; operate widgets |

**Auto-switching (default on):** Tab/click onto a control → focus mode; leave it → browse mode. A high-pitched beep = entering focus; lower beep = returning. Manual toggle: `NVDA+space`.

> **Gotcha:** auto-switch only triggers on Tab by default — not arrow-key caret movement (unless that option is checked). Test custom widgets with manual `NVDA+space` in both modes.

## Quick navigation keys (single-letter)
Add `Shift` to move backwards. `NVDA+shift+space` toggles all single-letter nav.

| Key | Element | Key | Element |
|---|---|---|---|
| `h` | heading | `b` | button |
| `1`–`9` | heading level N | `x` | checkbox |
| `k` | link | `c` | combo box |
| `u`/`v` | unvisited/visited link | `r` | radio |
| `f` | form field | `e` | edit field |
| `l`/`i` | list / list item | `q` | block quote |
| `t` | table | `g` | graphic |
| `d` | landmark | `o` | embedded object |
| `n` | non-linked text | `p` | paragraph |
| `s` | separator | `w` | spelling error |

## Essential commands
| Command | Key |
|---|---|
| Toggle browse/focus | `NVDA+space` |
| **Refresh browse buffer** | `NVDA+f5` *(critical for SPAs)* |
| Find | `NVDA+control+f` |
| **Elements List** (headings/links/landmarks/forms/buttons) | `NVDA+f7` |
| Report current focus | `NVDA+tab` (twice to spell) |
| Report title | `NVDA+t` |
| Read whole dialog | `NVDA+b` |
| **Report dynamic content changes** (toggle) | `NVDA+5` *(must be ON for aria-live)* |
| Input help mode | `NVDA+1` *(press any key to hear it)* |

## Recommended test setup
1. Download NVDA 2026.1.1; start with `Ctrl+Alt+N`.
2. **Speech Viewer** (Tools menu) — floating window showing exactly what NVDA speaks. Essential for capturing announcements.
3. **Braille Viewer** (Tools menu) — for verifying braille-specific attributes (`aria-brailleroledescription`).
4. **Focus Highlight** (Settings → Vision) — red = browse, blue = focus; shows where NVDA's caret is.
5. Speech rate ~40-50% while learning; punctuation "Most".
6. Dynamic content reporting ON (`NVDA+5`).
7. Test in Firefox first, then Chrome/Edge.

## Test workflow for a page
```
A. STRUCTURE (browse mode)
   1. Ctrl+Alt+N, open Speech Viewer. Load page in Firefox.
   2. NVDA+t → page title (unique? descriptive?)
   3. NVDA+F7 → Elements List → check heading outline, landmarks, links, form fields.
   4. H / Shift+H → walk every heading. Verify logical hierarchy (no skipped levels).
   5. D / Shift+D → walk landmarks (banner, nav, main, complementary, contentinfo).
   6. Down arrow / Say All (NVDA+DownArrow) → read top-to-bottom.

B. INTERACTIONS (focus mode)
   7. Tab through every focusable element. Listen: role + name + state.
   8. For each widget, verify NVDA auto-switches to focus mode (beep) and back.
   9. Operate with expected keys. Confirm state changes announce
      (expanded/collapsed, checked/unchecked, selected).

C. DYNAMIC CONTENT
   10. Trigger every state change: open dialogs, switch tabs, submit forms, SPA routes.
   11. Confirm announcements (aria-live, focus moves). Press NVDA+F5 if buffer stale.

D. DOCUMENT
   12. For each bug: record exact Speech-Viewer output, nav path, expected vs actual.
```

## Common announcements (2026.1)
| ARIA | NVDA speaks |
|---|---|
| `role="dialog"` | "dialog" + accessible name; focus moves in on open |
| `role="alert"` | "Alert" + content (assertive) |
| `role="status"` | content (polite, no "status" word) |
| `role="button"` | name + "button" |
| `aria-pressed` | "toggle button pressed/not pressed" |
| `role="checkbox"` + `aria-checked` | name + "checkbox checked/unchecked" |
| `role="combobox"` + `aria-expanded` | name + "combo box expanded/collapsed" + "has popup" |
| `role="tab"` + `aria-selected` | "tab selected/not selected" |
| `role="menu"` / `menuitem` | "menu" / "menu item"; "submenu" if `aria-haspopup` |
| `role="tree"` / `treeitem` | "tree view level N expanded x of y" |
| `role="table"` | "table with X rows and Y columns"; headers announced on cell entry |
| `role="heading"` + `aria-level` | "heading level N" |
| `aria-current="page"` | "current page" |
| `aria-required="true"` | "required" |
| `aria-invalid="true"` | "invalid entry" |
| **`aria-errormessage`** | error text announced when field invalid *(NEW 2026.1)* |

## NVDA-specific gotchas (2026)

### Live regions — "priming" is mandatory
NVDA does NOT announce pre-populated live regions on load (except `role="alert`" inconsistently). Reliable pattern:
```html
<!-- Step 1: empty region exists FIRST -->
<div id="status" aria-live="polite" aria-atomic="true"></div>
<!-- Step 2: populate AFTER (separate step triggers announcement) -->
<script>
  setTimeout(() => { document.getElementById('status').textContent = 'Saved'; }, 0);
</script>
```
- **Re-rendering the live region** (React/Vue/Angular parent re-mount) silences it — keep the container stable; only change its text.
- `aria-relevant` has **no effect in NVDA** (JAWS-only). Don't rely on it.
- Don't combine `aria-live="assertive"` with `role="alert"` — double-speaks in VoiceOver iOS.

### aria-activedescendant
- NVDA honors it — announces the highlighted option without moving DOM focus.
- Common failure: option elements **lack matching `id`** → NVDA silent or "blank".
- NVDA relies on `aria-activedescendant` for comboboxes; does NOT require `aria-selected` (unlike VoiceOver). Set `aria-selected="true"` on the highlighted option per W3C pattern.

### role="application"
- Forces NVDA into focus mode; passes all keys to your script.
- Use ONLY for non-standard widgets (editor canvas, complex grid). Misuse traps users — browse-mode quick-nav stops.
- Handle ALL keyboard yourself; mark readable sub-sections with `role="document"`.

### Focus management & SPA route changes
| Scenario | Problem | Fix |
|---|---|---|
| Route change | Browse buffer stale; NVDA reads old page | Move focus to new `<main>`/`<h1>` (`tabindex="-1"`); announce via live region (not both) |
| Modal open | NVDA may not say "dialog" if focus not moved in | Move focus to a focusable child OR give dialog `tabindex="-1"` and focus it; NVDA announces role on focus entry |
| Modal close | Focus drops to page top | Restore focus to trigger: `trigger.focus()` |
| Injected DOM | New focusables not in buffer | Move focus to new content so NVDA re-renders (don't rely on user pressing NVDA+F5) |

### 2026.1 web bug fixes
- `aria-errormessage` now reported (Chrome + Firefox).
- `aria-labelledby` now names tables in Firefox.
- Radio/checkbox menu items announced correctly on submenu entry.
- Malformed links no longer break reading in Chromium.
- **Open issue**: `aria-errormessage` only reads the FIRST idref (#19490) — if you chain multiple error IDs, only the first announces.

## NVDA + ARIA attribute support (2026.1)
✅ reliable · ⚠️ partial · ❌ not announced

| Attribute | Status | Notes |
|---|---|---|
| `aria-label` / `aria-labelledby` / `aria-describedby` | ✅ | reliable across browsers |
| `aria-current` | ✅ | all tokens announced |
| `aria-expanded` / `aria-pressed` / `aria-checked` | ✅ | |
| `aria-disabled` | ✅ | "unavailable" |
| `aria-required` / `aria-invalid` | ✅ | |
| **`aria-errormessage`** | ✅ NEW | only first idref read (#19490) |
| `aria-live` | ⚠️ | must prime empty first then mutate |
| `role="alert"` / `role="status"` | ✅ | |
| `aria-atomic` | ⚠️ | Firefox bug #1885011 |
| `aria-relevant` | ❌ | no NVDA effect |
| `aria-activedescendant` | ✅ | requires matching `id` on option |
| `aria-modal="true"` | ✅ | triggers dialog focus containment |
| `aria-hidden="true"` | ✅ | never put on focusable elements |
| `aria-details` | ⚠️ | announced as presence; **no navigation path** — don't rely on it as sole way to reach supplemental content |
| `aria-controls` | ⚠️ | exposed in API but NVDA adds no "controls" nav command |
| `aria-flowto` | ❌ | not exposed |
| `title` attribute | ⚠️ | fallback name only; not keyboard-accessible; NVDA doesn't expand `<abbr>` from title |

## How NVDA announces common widgets

### Tables — cell & header navigation
On entry: "table with X rows and Y columns". Navigate with `Ctrl+Alt+Arrows`:
- `Ctrl+Alt+Right/Left` — next/prev column (same row)
- `Ctrl+Alt+Up/Down` — next/prev row (same column)
- `Ctrl+Alt+Home/End` — first/last column
- `Ctrl+Alt+PageUp/Down` — first/last row
Headers announce if associated via `<th scope>` / `headers` / `aria-labelledby`: "row 2 column 3, Price, 19.99".

### Forms — label / required / invalid / error
```html
<label for="email">Email</label>
<input id="email" type="email" required aria-invalid="true"
       aria-errormessage="email-err" aria-describedby="email-hint">
<p id="email-hint">We never share your email.</p>
<p id="email-err">Enter a valid email address.</p>
```
On focus: "Email, edit, required, invalid entry, We never share your email. Enter a valid email address." *(2026.1 reads aria-errormessage)*

| Field | Announcement |
|---|---|
| `<input type="password">` | "Password, edit protected" (typed chars = "star") |
| `<input type="range">` | "Volume, slider 50" |
| `<input type="number">` | "Quantity, edit, spin button" |
| `<select>` | "Country, combo box" (Alt+Down to expand) |
| `<fieldset>`+`<legend>` | "Grouping, <legend>" then each control |

## Testing with NVDA checklist

### Environment
- [ ] NVDA 2026.1.1; Firefox primary, Chrome/Edge secondary
- [ ] Speech Viewer open
- [ ] Focus Highlight on (red=browse, blue=focus)
- [ ] Dynamic content reporting ON (`NVDA+5`)
- [ ] NVDA modifier set (Insert or Caps Lock)

### Structure
- [ ] Title unique/descriptive (`NVDA+t`); `lang` on `<html>`
- [ ] Heading outline logical via `NVDA+F7` and `H` — no skipped levels
- [ ] Landmarks reachable with `D` (banner, nav, main, contentinfo min)
- [ ] Skip-to-main works (Tab → Enter → focus in main)
- [ ] Reading order matches visual; images have `alt` (`G` walks graphics)

### Interactions
- [ ] Every interactive element reachable by Tab/Shift+Tab; no keyboard traps
- [ ] NVDA auto-switches focus mode on fields and back on exit
- [ ] Visible focus always present
- [ ] Each control: role + name + state announced
- [ ] `aria-hidden` never on a focusable element

### Widgets
- [ ] **Dialogs**: focus moves in on open; "dialog" + name; focus returns to trigger on close
- [ ] **Menus**: trigger `aria-expanded`; items by arrows; `Esc` closes
- [ ] **Comboboxes**: `aria-activedescendant` matches option `id`; active option announced
- [ ] **Tabs**: tablist focus-mode; arrows; `aria-selected`; Tab → tabpanel
- [ ] **Accordions**: `aria-expanded` on toggle; panel reachable after open
- [ ] **Tables**: "X rows Y columns"; `Ctrl+Alt+Arrows` move; headers announced
- [ ] **Forms**: every field labeled; required; `aria-invalid` + `aria-errormessage` on error

### Dynamic content & SPAs
- [ ] Live regions primed empty first, then mutated
- [ ] `role="alert"` for errors; `role="status"` for polite updates
- [ ] SPA routes move focus to `<main>`/`<h1>` OR announce via live region (not both)
- [ ] `aria-busy="true"` toggled during async loads (try/finally)
- [ ] Modals restore focus to trigger

## Primary sources (2026)
- NVDA 2026.1 release: https://www.nvaccess.org/post/nvda-2026-1
- User Guide (2026.1.1): https://download.nvaccess.org/releases/2026.1.1/documentation/userGuide.html
- Key Commands: https://download.nvaccess.org/releases/2026.1.1/documentation/keyCommands.html
- TetraLogical NVDA HTML Support matrix (Feb 2026): https://tetralogical.github.io/screen-reader-HTML-support/NVDA.html
- TetraLogical live-region analysis: https://tetralogical.com/blog/2024/05/01/why-are-my-live-regions-not-working
- aria-errormessage PR #16411: https://github.com/nvaccess/nvda/pull/16411
- aria-errormessage multi-idref bug #19490: https://github.com/nvaccess/nvda/issues/19490
- WebAIM NVDA guide: https://webaim.org/articles/nvda/