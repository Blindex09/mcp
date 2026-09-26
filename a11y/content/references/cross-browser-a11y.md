# Cross-Browser Accessibility — the same page is not the same experience everywhere (2026)

Browsers build their own accessibility tree from the DOM and expose it to assistive technology through different
platform APIs. A page can look and audit fine in one browser and behave differently in another. Test the browsers your
users actually use, and read the differences with judgment: the tools give the facts, you decide what they mean.

## 1. Which browsers matter, and with what

| Pairing | Why it matters |
|---|---|
| **Firefox + NVDA** | The most common combination for NVDA users on Windows; NVDA also works well with Chromium. Test both. |
| **Chromium (Chrome/Edge) + NVDA / JAWS** | Largest desktop share. |
| **WebKit (Safari) + VoiceOver** | The only real option on iOS and macOS; the WebKit engine is the closest proxy without a device. |

`a11y_open`, `a11y_audit`, `a11y_aria_snapshot` and `a11y_tab_order` accept `browser` (`chromium`, `firefox`, `webkit`; missing ones
are installed automatically). `a11y_compare_browsers` shows the same page side by side. None of these is a real screen reader.

## 2. What the tools can measure in each browser

| Capability | Chromium | Firefox / WebKit |
|---|---|---|
| Roles, names, states | Computed by the browser (Chromium accessibility tree over CDP) | From Playwright's aria snapshot (an implementation of the accessible-name algorithm), one element at a time |
| Focusable | From the browser's accessibility tree | From the browser's computed `tabIndex` |
| Clickable, including elements with only `addEventListener` | Yes (`DOMSnapshot.isClickable`) | **No.** Only `cursor: pointer` (a weaker signal); a mouse-only control with default cursor is not discovered |
| Focus style (`a11y_focus_style`) | Forced `:focus` state, no events fired | Really focuses the element (fires focus/blur); `:focus-visible` may differ from keyboard focus |
| Keyboard, screenshots, axe, reflow, text spacing, personas | Yes | Yes (Firefox does not emulate `is_mobile`: the phone persona uses viewport and touch only) |

Every result says which browser produced it and lists its limits. Never present a Firefox/WebKit dossier as if it had Chromium's
precision; say what was not measured.

## 3. Reading the differences

Ask, for each difference (`a11y_compare_browsers`):

1. **Is it a page bug or a browser difference?** A role or name that differs because of invalid or ambiguous markup is a page bug
   (fix the markup). A difference in how the same valid markup is exposed is a browser implementation detail: note it, test with the
   real screen reader, and avoid depending on it.
2. **Which one matches the specification?** Check the ARIA/HTML-AAM/Accname specs and the [ARIA-AT](https://aria-at.w3.org/) results
   before deciding which browser is "wrong".
3. **Does it change what the user can do?** A missing name, a control not reachable by keyboard, or a state not exposed is serious in
   any browser. A cosmetic difference in the tree is not.
4. **Focus order differences** usually point to DOM order versus visual order, `tabindex`, or elements one browser treats as focusable
   (for example scrollable regions) and another does not. Judge which order the user would expect.
5. **Axe violations in only one browser** often come from rendering differences (contrast, layout) or unsupported features.

## 4. Report

State the browsers compared, the differences found (facts), your reading of each (page bug / browser difference / unknown), the impact
on users, and what was **not** verified (real screen reader with each browser, real devices, versions).
