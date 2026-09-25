# Internationalization (i18n) & Right-to-Left (RTL) Accessibility (2026)

Accessibility for multiple *human* languages and writing directions — not to be
confused with [multilanguage-multiplatform-a11y.md](multilanguage-multiplatform-a11y.md),
which covers porting the accessibility pattern across *programming*
languages/frameworks (Vue, Flutter, Rust, etc.).

---

## 1. `lang` and `dir` — the two attributes everything else depends on

- **`<html lang="xx">`**: required on every page (it's one of WebAIM Million's
  top-6 recurring failures — see [audit-checklist.md](audit-checklist.md)). Screen readers
  use it to select the correct speech synthesis voice/pronunciation rules.
- **`lang` on sub-regions**: any element containing text in a *different*
  language than the page's `lang` must carry its own `lang` attribute
  (`<span lang="fr">bonjour</span>` inside an `<html lang="en">` page),
  otherwise the screen reader mispronounces it (WCAG 3.1.2, Level AA).
- **`dir="rtl"` / `dir="ltr"` / `dir="auto"`**: set on `<html>` for
  Arabic, Hebrew, Persian, Urdu, etc. `dir="auto"` on a single `<input>`/`<textarea>`
  lets the browser infer direction per-field from the first strong-directional
  character typed — useful for user-generated content in mixed-language apps.
- **Never rely on CSS alone** (`direction: rtl`) to flip a document's reading
  order — screen readers and browser find-in-page/selection behavior key off
  the **`dir` attribute**, not the computed CSS property.

## 2. Logical CSS properties (write once, both directions)

Physical properties (`margin-left`, `padding-right`, `left`, `text-align: left`)
do not flip automatically under `dir="rtl"` and force either a maintained
RTL-specific stylesheet or manual overrides. Use **logical properties** instead
— they flip automatically based on `dir` and `writing-mode`:

| Physical (avoid) | Logical (use) |
|---|---|
| `margin-left` / `margin-right` | `margin-inline-start` / `margin-inline-end` |
| `padding-left` / `padding-right` | `padding-inline-start` / `padding-inline-end` |
| `left` / `right` | `inset-inline-start` / `inset-inline-end` |
| `text-align: left` | `text-align: start` |
| `border-left` | `border-inline-start` |
| `float: left` | *(prefer flex/grid with logical `justify-content`/`inset`)* |

Baseline-supported across Chrome/Firefox/Safari since 2023 — safe to use as the
default in 2026, no fallback needed for evergreen browsers.

## 3. Bidirectional (bidi) text — `<bdi>` and `<bdo>`

- **`<bdi>`** (Bidirectional Isolate): wrap any dynamically-inserted string of
  *unknown* directionality (usernames, product names, search terms embedded in
  an otherwise-LTR/RTL sentence) so it doesn't visually corrupt the surrounding
  text's order. Example: `<p>Score: <bdi>{{ playerName }}</bdi> — 10 points</p>`
  — without `<bdi>`, an Arabic or Hebrew player name can drag the trailing
  digits/punctuation into the wrong visual position.
- **`<bdo dir="rtl">`**: force an explicit direction override (rare — mostly
  for showing directional text *as data*, e.g. a UI string explaining bidi
  itself). Don't reach for this to fix layout; that's what `dir`/logical
  properties are for.
- Unicode control characters (`‪`-`‮`, `⁦`-`⁩`) achieve the
  same effect as `<bdi>`/`<bdo>` in plain text contexts (e.g. inside an
  `aria-label` string) where you can't add an element.

## 4. Icons, chevrons, and directional imagery

- Mirror direction-implying icons under RTL: back/forward chevrons, arrows,
  "next"/"previous" pagination, progress indicators. CSS: `[dir="rtl"] .icon-chevron { transform: scaleX(-1); }`
  or use an icon font/SVG set that ships RTL variants.
- **Do NOT mirror**: icons depicting real-world objects with an inherent
  orientation regardless of reading direction — clocks, a play ▶ button (media
  playback direction is not a reading-direction concept), brand logos, numerals.
- Charts/graphs: decide per-chart whether the x-axis should reverse under RTL
  (time-series usually should NOT reverse — time still flows the same way);
  document the decision so it's consistent across the product rather than
  ad hoc per component.

## 5. Forms, dates, numbers — locale-aware, not just mirrored

- **Autocomplete/input purpose (`autocomplete` attribute)**: values are stable
  across locales (`autocomplete="name"`, `"tel"`, `"postal-code"`) — don't
  localize the *token*, only the visible label (ties into WCAG 2.2 SC 3.3.8
  Accessible Authentication, already covered in [wcag22-forms-redundant-entry.html](../examples/wcag22-forms-redundant-entry.html)).
- **Number/date/currency formatting**: use `Intl.NumberFormat` / `Intl.DateTimeFormat`
  with the active locale rather than hand-rolled formatting — locale affects
  digit shapes (Eastern Arabic-Indic numerals in some `ar-*` locales), decimal
  separators, and calendar systems (Hijri, Buddhist, etc.), all of which
  screen readers announce differently if mismatched with `lang`.
- **Form field order**: logical properties (§2) handle visual order; screen
  reader *traversal* order still follows DOM order — verify DOM order matches
  the intended reading order per locale, since RTL layout mirrors visually via
  CSS but the DOM doesn't reorder itself.

## 6. Testing checklist

- [ ] `<html lang>` set correctly per page/locale; sub-regions in a different
      language carry their own `lang`.
- [ ] `<html dir="rtl">` set for RTL locales; verify with a real RTL locale
      (`ar`, `he`, `fa`, `ur`), not just by flipping `direction` in devtools.
- [ ] Tab order and focus order still make sense reading right-to-left.
- [ ] Logical CSS properties used — no leftover `margin-left`/`right`/`left`
      that breaks mirroring.
- [ ] Chevrons/arrows mirrored; clocks/media icons/logos NOT mirrored.
- [ ] Mixed-direction dynamic content (names, search terms) wrapped in `<bdi>`.
- [ ] Screen reader smoke test in at least one RTL locale with NVDA/JAWS
      (Arabic or Hebrew voice pack) or VoiceOver (which has strong RTL support).
- [ ] Numbers/dates/currency formatted via `Intl.*` APIs, not string concatenation.
- [ ] Text expansion: German/Finnish/Russian UI strings can run 30-50% longer
      than English — verify truncation/wrapping doesn't hide content or break
      touch target sizing (SC 2.5.8) at max expected string length.
