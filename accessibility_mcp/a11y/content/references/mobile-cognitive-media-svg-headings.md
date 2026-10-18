# Mobile, Cognitive, Drag-Drop, Media, SVG/Charts, Headings & Landmarks (2026)

A consolidated reference for topics often under-covered. All sources dated 2026.

---

## 1. Mobile accessibility (2026)

### Touch target size (WCAG 2.5.8 / 2.5.5)
- **2.5.8 Target Size (Minimum)** (AA, new in 2.2): pointer targets ≥ **24×24 CSS px**. If smaller, a 24×24 circle centered on it must not intersect an adjacent target's circle. Independent of zoom factor. Exceptions: Inline, Available (other way), User Agent Control, Essential, In-sentence.
- **2.5.5 Target Size (Enhanced)** (AAA): **44×44 CSS px**. Apple HIG: 44pt; Material: 48dp.
```css
.btn { min-width: 48px; min-height: 48px; padding: 12px 16px; font-size: 16px; }
@media (hover: hover) and (pointer: fine) { .btn { min-width: 32px; min-height: 32px; } }
/* Small targets can pass via spacing instead of size */
.icon { width: 20px; height: 20px; margin: 12px; }
```

### Reflow at 320px & 400% zoom (WCAG 1.4.10)
Content must reflow to a single column at **320 CSS px wide** (≈ 1280px desktop @ 400% zoom), no two-dimensional scroll, no loss of info/function. Exceptions: data tables, maps, diagrams, content where 2D layout is essential.
```html
<!-- Recommended -->
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- FAILS 1.4.4 + 1.4.10 — never use -->
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
```

### Mobile Screen Reader Quirks & WebKit Bugs
- **`display: contents` compatibility:** Accessibility-tree behavior has changed across WebKit/browser releases. Do not apply it to semantic containers without testing current iOS Safari/VoiceOver; retain a non-`display: contents` fallback when semantics disappear.
- **`opacity: 0` Virtual Swipe Leakage:** Controls styled with `opacity: 0` or `height: 0` without `overflow: hidden` or `aria-hidden="true"` remain in the VoiceOver virtual swipe tree, creating phantom swipe stops.
- **iOS live-region timing:** Create announcers before updating them. Some Safari/VoiceOver versions miss content inserted in the same render transaction; if testing reproduces this, separate region creation and content update into later tasks. Do not encode 50–100 ms as a universal guarantee.
- **VoiceOver duplicate-announcement risk:** Redundantly combining implicit live-region roles such as `alert`/`status` with explicit live attributes can produce repeated speech in some browser/AT combinations. Use one semantic mechanism and test the target version.

### Gestures vs alternatives
- **2.5.1 Pointer Gestures** (A): all multipoint/path-based gestures need a single-pointer alternative.
- **2.5.7 Dragging Movements** (AA): dragging-only needs a tap/click alternative (see §3).

### Mobile screen readers
- **VoiceOver (iOS)**: swipe right/left to move; double-tap to activate; three-finger swipe to scroll. Enable via Settings → Accessibility → VoiceOver, or triple-click side button. Rotor exposes headings/landmarks/links.
- **TalkBack (Android)**: swipe right/left to navigate; double-tap to activate. Enable via Settings → Accessibility → TalkBack.

### Hover/focus on touch (WCAG 1.4.13)
Additional content on hover/focus must be dismissible, hoverable, persistent. On touch, hover doesn't exist — provide tap-based triggers.

### Font sizing
Small form text can trigger iOS Safari focus zoom. Prefer `font-size: 16px` or larger rather than disabling page zoom. Support Dynamic Type (iOS) and Android font scaling without clipping, truncation, or lost controls; test the product's supported platform scale range.

---

## 2. Cognitive accessibility (2026)

### WCAG 3.0 cognitive outcomes
WCAG 3.0 (3 March 2026) is an incomplete Working Draft. Treat its cognitive-accessibility topics as research directions, not stable requirements or a conformance score. Do not claim Bronze/Silver/Gold or 0–4 scoring as a current normative model. Continue using WCAG 2.2 plus W3C COGA guidance for clear language, consistency, error recovery, help, and user testing.

### Plain language (3.1.5 Reading Level, AAA; COGA Making Content Usable)
Write plainly, break into manageable sections, avoid jargon.

### Consistency (3.2.3, 3.2.4 — AA)
- **3.2.3 Consistent Navigation**: nav mechanisms repeated across pages appear in the same order.
- **3.2.4 Consistent Identification**: components with same functionality have consistent labels. A "Submit" button shouldn't become "Confirm" on the next screen.

### Predictable (3.2.1, 3.2.2, 3.2.6 — A/AA)
- **3.2.1 On Focus**: focus shouldn't trigger context change.
- **3.2.2 On Input**: changing a setting shouldn't auto-submit without warning.
- **3.2.6 Consistent Help** (new in 2.2, AA): help mechanisms in a consistent location across pages.

### Error prevention (3.3.1–3.3.4)
| SC | Level | Requirement |
|---|---|---|
| 3.3.1 Error Identification | A | Errors described in text |
| 3.3.2 Labels or Instructions | A | Provide labels/instructions |
| 3.3.3 Error Suggestion | AA | Suggest corrections |
| 3.3.4 Error Prevention (Financial/Data Transact) | AA | Submissions reversible or checkable/confirmable |

Use plain-language errors ("Please enter a 5-digit ZIP code"), hints before typing ("MM/DD/YYYY"), accept common format variations.

### Help & shortcuts
- **3.3.5 Help** (AAA): human contact info available.
- **2.1.4 Character Key Shortcuts** (A): single-char shortcuts need disable/remap option.

### Focus management that doesn't disorient
Avoid moving focus unexpectedly (violates 3.2.1). On dialog open: set focus in, trap; on close: return to trigger. Announce dynamic content via `aria-live`.

---

## 3. Drag-and-drop (2026)

### WCAG 2.5.7 Dragging Movements (AA, new in 2.2)
"All functionality that uses a dragging movement can be achieved by a single pointer without dragging, unless essential." Separate from keyboard accessibility (2.1.1) — a touch user who can't drag still needs a tap option. Exceptions: Essential, User Agent Control.

### Non-drag alternatives
- **Sortable lists**: up/down buttons on each item, or a "Move to position" menu.
- **File uploads**: always-visible "Choose File" button alongside the drop zone.
- **Sliders**: click-to-position on track + number input.
- **Kanban**: context menu per card with "Move to column" options.
```html
<!-- Sortable list with up/down buttons (2.5.7 compliant) -->
<ul class="sortable">
  <li>Task 1
    <button aria-label="Move Task 1 up" onclick="move(0,-1)">▲</button>
    <button aria-label="Move Task 1 down" onclick="move(0,1)">▼</button>
  </li>
</ul>
<!-- File upload with both methods -->
<label class="dropzone">Click to upload or drag and drop
  <input type="file" multiple accept="image/*">
</label>
```

### ARIA for draggable items — what to use instead of aria-grabbed
`aria-grabbed` and `aria-dropeffect` are deprecated. Do not replace them with unrelated ARIA states. Use native buttons such as “Move up”, “Move down”, or “Move to column”; if the product also provides a selectable listbox, use `aria-selected` only for actual selection. Convey transient reorder mode through concise instructions/status that testing shows users need.

### Keyboard reorder contract
Do not label a custom drag/reorder interaction as a W3C listbox pattern unless it actually implements listbox selection semantics. Prefer explicit move buttons. If a custom reorder mode is necessary, document its keys, provide Escape/cancel and undo, preserve focus, and announce only bounded user-triggered results such as “Item A moved to position 2 of 4.”

---

## 4. Media accessibility (2026)

| SC | Level | Requirement |
|---|---|---|
| 1.2.2 Captions (Prerecorded) | A | synchronized captions for prerecorded audio |
| 1.2.4 Captions (Live) | AA | live captions |
| 1.2.3 Audio Description or Media Alternative | A | audio description OR full text alternative |
| 1.2.5 Audio Description (Prerecorded) | AA | audio description required |
| 1.2.8 Media Alternative | AAA | full text alternative for all media (deafblind) |
| 1.4.2 Audio Control | A | autoplaying audio >3s needs pause/stop/mute |
| 2.2.2 Pause, Stop, Hide | A | autoplaying moving content >5s needs pause/stop/hide |

### Captions via HTML5 `<track>`
```html
<video controls aria-label="Product demo video">
  <source src="demo.mp4" type="video/mp4">
  <track kind="captions" src="en.vtt" srclang="en" label="English captions" default>
  <track kind="descriptions" src="ad.vtt" srclang="en" label="English audio descriptions">
</video>
```
A transcript is NOT a substitute for captions in video, but complements them (helps deafblind, search, low-bandwidth).

### Audio descriptions
If video has meaningful visual content not explained in audio → need AD. Standard AD inserts narration during natural pauses; extended AD (1.2.7, AAA) pauses the video.

### Accessible video player
Every control reachable via Tab, operable via Enter/Space/arrows; visible focus; accurate name/role/state (4.1.2); caption + AD toggle at the same menu level as volume/play. Keyboard contract: Space/Enter play-pause, M mute, F fullscreen, arrows/number-keys seek, C caption toggle.

### Auto-play
**Never autoplay with sound.** If autoplay, mute by default and provide a clearly-labeled pause control.

---

## 5. SVG and charts (2026)

### `<title>` / `<desc>` / `role="img"` + `aria-labelledby`
The `<title>` (first child of `<svg>`) maps to accessible name; `<desc>` to accessible description. Put `role="img"` on `<svg>` so screen readers treat it as a graphic and ignore nested children. Wire via `aria-labelledby` (preferred — `aria-describedby` has poorer AT support).
```html
<svg role="img" aria-labelledby="chart-title chart-desc" viewBox="0 0 640 360">
  <title id="chart-title">Website visitors Jan–Mar</title>
  <desc id="chart-desc">Visitors rose from 12,400 in January to 19,200 in March.</desc>
  <rect role="presentation" x="60" y="60" width="40" height="280" fill="currentColor"/>
</svg>
```
Decorative SVG: `aria-hidden="true"`, omit title/desc.

### Accessible charts — data table alternative (gold standard)
The most reliable chart alternative across all screen readers is a **visually-hidden HTML data table** with the same numbers. Use `.sr-only` (NOT `display:none`, which hides from AT too).
```html
<svg role="img" aria-label="Q3 revenue bar chart; North America led at $4.2M" viewBox="0 0 800 400">
  <title>Q3 Revenue by Region</title>
  <rect role="presentation" .../>
</svg>
<table class="visually-hidden">
  <caption>Q3 Revenue by Region</caption>
  <thead><tr><th>Region</th><th>Revenue</th><th>YoY change</th></tr></thead>
  <tbody>
    <tr><td>North America</td><td>$4.2M</td><td>+12%</td></tr>
    <tr><td>Asia-Pacific</td><td>$2.1M</td><td>+19%</td></tr>
  </tbody>
</table>
```
Technique ladder (effort vs coverage): `role="img"`+`aria-label` → `<title>`+`<desc>` → per-mark `aria-label` → full `role="grid"` → accessible data table (most reliable).

### Charting libraries (ApexCharts 2026 audit)
| Library | Render | ARIA role | Accessible name | Data table |
|---|---|---|---|---|
| **ApexCharts 5.16** | SVG | application | Yes | No |
| **Highcharts 11.4** | SVG | img | Yes | No |
| Google Charts | SVG | none | Yes | **Yes** (default) |
| Recharts | SVG | none | No | No |
| Plotly.js | SVG | none | No | No |
| Chart.js / ECharts / amCharts | Canvas | none | No | No |

ApexCharts + Highcharts ship role + name + title/desc with zero setup. Google Charts renders a data-table fallback by default. Canvas libraries expose nothing — add `role="img"` + `aria-label` on container + hidden data table.

**Highcharts**: enable the accessibility module — adds text description, keyboard nav, ARIA roles, hidden screen-reader info region. Configure `accessibility.description`, series/point `description`, `caption`.

### Per-mark labelling & live updates
Label each focusable mark with an accessible name combining category and formatted value ("Q1, 4.2M"). Do not make streaming chart mutations live. If a user-triggered filter produces an important status message, announce one bounded summary such as “12 pontos correspondem ao filtro”; keep the updated chart navigable on demand without repeating every mark.

---

## 6. Headings & landmarks deep dive (2026)

### Heading hierarchy rules
- Headings follow a logical nested order like a book's index — don't skip levels (no h1→h4).
- Heading levels represent structure, not design — use CSS for visual styling.
- Don't use headings as big-text styling, bold paragraphs, or empty headings.
- When stripping paragraphs, the remaining heading outline should still read clearly.

### Multiple h1 debate (resolved in 2026)
The WHATWG HTML example of multiple `<h1>` within `<section>` has been **removed** — not supported by browsers. **One `<h1>` per page** describing the page content is the established best practice for both SEO and accessibility. Multiple H1s weaken the hierarchy.

### Hidden headings
Visually-hidden headings (`.sr-only`) are valid when sighted layout doesn't need a visible heading but AT users benefit from the structure. Don't use `display:none` (removes from AT). Omitting a heading because "the design clearly indicates a new section" is a mistake — the heading is still needed for AT.

### Landmark roles and naming
| HTML Element | Landmark Role |
|---|---|
| `<header>` | banner |
| `<nav>` | navigation |
| `<main>` | main |
| `<aside>` | complementary |
| `<section>` (with accessible name) | region |
| `<article>` | article |
| `<footer>` | contentinfo |
| `<form>` | form |
| — | search |

**Naming rules:**
- If a landmark role appears more than once, give each a unique label (`aria-label="Primary"`, `aria-label="Footer"`).
- Don't include the role in the label (a `navigation` labelled "Site Navigation" announces as "Site Navigation Navigation") — use "Site".
- Prefer semantic HTML over `role` attributes; prefer `aria-labelledby` (visible heading) over `aria-label`.
- One `main` per page; one `contentinfo` (footer) per page.
```html
<header> <!-- banner -->
  <nav aria-label="Primary"><ul><li><a href="/">Home</a></li></ul></nav>
</header>
<main id="main-content">
  <h1>Page title</h1>
  <section aria-labelledby="sec1"><h2 id="sec1">First section</h2> ...</section>
</main>
<nav aria-label="Footer"> ... </nav>
<footer> ... </footer>
```

### Navigating by landmarks
JAWS, NVDA (D key, landmarks dialog), VoiceOver rotor compile landmark lists users jump between — "skip links for screen reader users."

### Skip links (WCAG 2.4.1 Bypass Blocks)
The skip link is the **first focusable element** in the DOM, jumping past repetitive nav to main content. Landmarks satisfy 2.4.1's normative wording for AT users but NOT for sighted keyboard users — you still need a visible skip link.
- Hide off-screen until focus (don't use `display:none`/`visibility:hidden` — removes from AT).
- Target needs `tabindex="-1"` for focus to land correctly.
```html
<a class="skip-link" href="#main">Skip to main content</a>
<main id="main" tabindex="-1"><h1>...</h1></main>
```
```css
.skip-link { position: absolute; left: -999px; top: auto; }
.skip-link:focus { left: 0; top: 0; padding: 8px 16px; background: #fff; border: 2px solid #000; z-index: 1000; }
```

### Heading level best practices
- One `<h1>` per page, just above main content.
- Don't skip levels (h1→h2→h3, never h1→h4).
- Choose level by position in the document outline, not font size.
- For reusable components, default to `<h2>` and adjust within the host page's structure.
- Empty headings (CMS glitches) fail — validate they contain text.
