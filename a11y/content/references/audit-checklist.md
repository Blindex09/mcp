# Accessibility Audit & Retrofit Checklists (2026)

Copy-paste checklists for audits, PRs, and sprint planning. Field-proven in 2026 remediation work.

---

## Full audit checklist (deliverable for an audit run)

- [ ] Inventory export completed (routes, components) — `routes.txt` or sitemap
- [ ] Automated `axe-core` and Lighthouse runs saved with JSON outputs for top traffic pages + critical flows (login, search, checkout, onboarding)
- [ ] Top 10 high-impact pages manually verified (keyboard + screen reader)
- [ ] SPA routes driven via Playwright/Puppeteer so dynamic content is scanned (not just initial HTML)
- [ ] CSV backlog exported with: `url/component | issue | wcag_sc | automated? | occurrence_count | user_impact | estimated_effort_hours | owner`
- [ ] Business-impact annotated for each P0/P1 issue (blocks checkout? registration? revenue?)
- [ ] Mobile VoiceOver/TalkBack sampling done on key flows
- [ ] Accessibility-tree inspection compares visible content with computed names, descriptions, roles, and hidden/live copies; the same meaning is not exposed twice
- [ ] ARIA removal review completed: every added role, state, property, live region, and hidden accessible string has a documented semantic need that native HTML/platform APIs do not already meet
- [ ] Color contrast sampled at every surface combination (hover, disabled, error states — not just primary) — `axe`/`audit-axe.js` catches most in-DOM failures automatically; use `node scripts/audit-contrast.js <fg> <bg> --size=<px>` for palette/mockup review before code exists, or to double-check a specific pair by hand
- [ ] Browsers: Chrome + Safari (current stable)
- [ ] Report exported to PDF with audit date and WCAG version targeted

### Automated scan commands (2026)
```bash
# Lighthouse CLI on a single URL (WCAG 2.2 AA)
npx lighthouse https://staging.example.com/login \
  --only-categories=accessibility \
  --output=json --output-path=./reports/login-a11y.json

# axe-core CLI sitewide (WCAG 2.2 AA tags)
npx @axe-core/cli https://staging.example.com --tags wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa --save reports/axe.json

# Custom repository auditor script
node scripts/audit-axe.js https://staging.example.com

# Manual contrast check for a design/mockup color pair (no live page needed)
node scripts/audit-contrast.js "#767676" "#ffffff" --size=16
```

## WCAG 2.2 New Criteria Audit Items (Level AA / A)
- [ ] **SC 2.4.11 Focus Not Obscured (Minimum) (AA)**: Focused elements are not hidden behind sticky headers/footers (`scroll-margin-top` applied).
- [ ] **SC 2.5.7 Dragging Movements (AA)**: Drag-and-drop features (reorder, canvas pan) have single-pointer tap/click alternatives.
- [ ] **SC 2.5.8 Target Size (Minimum) (AA)**: All touch targets are at least 24×24 CSS px or maintain a 24px non-intersecting spacing circle.
- [ ] **SC 3.2.6 Consistent Help (A)**: Help mechanisms (support chat, contact form, FAQ link) are placed in consistent order across pages.
- [ ] **SC 3.3.7 Redundant Entry (A)**: Multi-step forms auto-populate or allow selecting previously entered user data.
- [ ] **SC 3.3.8 Accessible Authentication (Minimum) (AA)**: No cognitive tests; paste enabled on password/OTP inputs, `autocomplete` attributes present, passkeys supported.
- [ ] **SC 4.1.1 Parsing**: Removed in WCAG 2.2 (do not fail pages for obsolete XML/HTML parsing rules).

### WebAIM Million 2026 — error-distribution benchmark
Use these stats to scope audits and frame prioritization conversations with stakeholders (source: WebAIM, analyzed Feb 2026, top 1M home pages):

- **56.1 detectable errors per page on average** (+10.1% vs 2025; reversed 6 years of gradual improvement).
- **95.9% of home pages** had detected WCAG 2 A/AA failures (up from 94.8%). True non-conformance is higher because automated tools catch only ~30–40% of issues.
- **Same 6 error types = ~96% of all detected failures, 7 years running:** low contrast (83.9% of pages), missing alt text (>50%), missing form input labels (33.1%), empty links, empty buttons, missing `<html lang>`.
- **ARIA correlate (counterintuitive but actionable):** 82.7% of pages used ARIA (excl. landmarks); pages WITH ARIA averaged **59.1 errors** vs **42 without** (+40%). ARIA prevalence rose 28% YoY in labels/descriptions (avg 31.4 `aria-label`/`labelledby`/`describedby` per page). 22% of `role="menu"` instances introduce barriers from missing markup/keyboard support.
- **Key takeaway for scoping:** More ARIA ≠ more accessible. Weight manual semantic review of ARIA-heavy regions heavily — the "First Rule of ARIA" (prefer native HTML) is now statistically the highest-ROI audit pattern. The most common failures are basic and cheap to fix, so the quick-win sweep below addresses exactly them.

## Prioritization rubric (score each issue 1–4 per dimension)

| Dimension | 4 (High) | 3 | 2 | 1 (Low) |
|---|---|---|---|---|
| User impact | Completely blocks a core flow | Major annoyance for many | Noticeable friction for some | Cosmetic or minor |
| Frequency | >50% of users | 10–50% | 1–10% | <1% |
| Business/quality impact | High product/quality risk | Significant brand exposure | Internal SLA risk | Minimal |
| Effort to fix | <1 dev-day | 1–3 dev-days | 3–7 dev-days | >7 dev-days |
| Regression risk | Low (isolated change) | Moderate | Moderate-high | High |

**Composite score thresholds:**
- 17–20 → **P0 / Critical** — hotfix, ship ASAP
- 12–16 → **P1 / High** — next sprint
- 7–11 → **P2 / Medium** — scheduled cleanup
- ≤6 → **P3 / Low** — backlog grooming

---

## Quick-win sweep (fast edits that fix a large share of automated failures)

- [ ] Add missing `alt` (or `alt=""` for decorative images)
- [ ] Every interactive control has an accessible name (`aria-label`, visible label, or `aria-labelledby`)
- [ ] Fix glaring color-contrast violations (CTA buttons, body text on background, focus rings)
- [ ] Restore visible `:focus-visible` outlines (don't remove without a replacement)
- [ ] Replace `<div onClick>` with `<button>` (action) or `<a href>` (navigation)
- [ ] Add `<label for>` to every form input (placeholder is NOT a label)
- [ ] The page has a clear primary heading and a logical heading hierarchy; do not choose levels for visual size alone
- [ ] `<main>` is the single top-level landmark; add a "skip to main content" link
- [ ] `lang` attribute on `<html>`
- [ ] Genuine status messages that do not receive focus have an appropriate status mechanism; ordinary dynamic content is not automatically made live
- [ ] Urgent, time-sensitive messages use `role="alert"` only when interruption is justified; interactive/blocking decisions use a dialog, not an alert containing controls
- [ ] No element repeats native semantics with redundant ARIA, and no visible message has a permanent hidden duplicate in the accessibility tree
- [ ] Repeated peer items (shortcuts, options, actions, steps, and results) are visually separated and use semantic lists where appropriate; controls are not concatenated in one paragraph/container

---

## PR-level Definition of Done (add as PR checklist)

- [ ] `axe` run on the component/page — no new critical violations
- [ ] Unit test with `jest-axe` added where appropriate
- [ ] Keyboard navigation tested (tab order, activation keys, Esc closes modals)
- [ ] Screen reader smoke test recorded (short note: NVDA or VoiceOver)
- [ ] Visual check for `:focus-visible` styles and contrast on all states
- [ ] `prefers-reduced-motion` respected on any new animation
- [ ] Dynamic updates were classified: status message, context change, component state, or ordinary content. Only the cases that need automatic notification use a live/status mechanism
- [ ] Live-region output is bounded and tested for duplicate speech; token streams, thought text, tool logs, file edits, navigation details, and command output remain silent by default
- [ ] Form errors associated with `aria-invalid` + `aria-describedby`
- [ ] Component CSS selectors match the classes actually rendered; action/shortcut lists remain one item per row under zoom, reflow, and user text spacing

### jest-axe unit test pattern
```js
import { axe, toHaveNoViolations } from 'jest-axe';
import { render } from '@testing-library/react';
expect.extend(toHaveNoViolations);

test('MyInput has no violations', async () => {
  const { container } = render(<MyInput />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### cypress-axe / Playwright e2e pattern
```js
// Cypress
import 'cypress-axe';
describe('Accessibility', () => {
  it('checkout flow has no critical violations', () => {
    cy.visit('/checkout');
    cy.injectAxe();
    cy.checkA11y(null, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    });
  });
});
```

---

## Sprint template (2-week accessibility sprint)

1. **Sprint goal**: Remove blockers in checkout that prevent keyboard checkout completion.
2. **Backlog**:
   - P0: Fix keyboard trap in `CartModal` — 1 dev-day
   - P1: Add `aria-live` announcements to the error banner — 0.5 dev-day
   - P1: Increase contrast on product price — 2 dev-hours
3. **Acceptance criteria**:
   - `CartModal` keyboard flow passes manual test and `cypress-axe` with no critical issues.
   - `aria-live` region announces errors for screen readers.
4. **QA sign-off**:
   - Run PR automated checks (axe, jest-axe)
   - Manual keyboard walkthrough recorded (short checklist)
   - Attach before/after screenshots and `axe` JSON

---

## Backlog fields to add in your issue tracker

- `a11y_severity` (Critical / Significant / Moderate / Recommendation)
- `wcag_success_criteria` (e.g., 1.4.3, 2.1.1)
- `occurrence_count` (how many routes/pages/components)
- `estimated_effort_hours`
- `owner`

---

## Metrics to track (define dashboards)

| Metric | Why it matters | Target (example) |
|---|---|---|
| Critical issues open | Business/quality exposure | Reduce 80% in 90 days |
| Automated pass rate | Detect regressions early | >90% on PRs |
| PR a11y check coverage | Prevent regressions | 100% for UI changes |
| Manual verification pass | Real user experience | >95% on critical flows |
| Mean time to remediate P0/P1 | Velocity | <14 days |

---

## Manual keyboard testing procedure

1. Open the page; unplug the mouse.
2. Press Tab from the very top — does focus land on a skip link first?
3. Tab through every interactive element — is the order logical (matches visual flow)?
4. Is a visible focus indicator present on every focusable element?
5. Activate every control with Enter / Space — does it do what the mouse click does?
6. In modals: Tab/Shift+Tab cycles inside; Escape closes; focus returns to trigger.
7. In menus/tabs/comboboxes: Arrow keys move; Home/End jump; the right element gets focus.
8. Test with the page zoomed to 400% and at 320px width (reflow).

---

## Screen reader smoke test checklist (NVDA / VoiceOver / JAWS)

- [ ] All images have alt text or are marked decorative (`alt=""`)
- [ ] Form labels are read with their inputs
- [ ] Error messages are announced
- [ ] Buttons have clear purposes (not just "button")
- [ ] Shortcut and action sets announce as lists with the expected item count, and every control is encountered separately
- [ ] Links have descriptive text (not "click here")
- [ ] Headings create a logical document outline
- [ ] Landmarks identify page regions (`nav`, `main`, `aside`, `footer`)
- [ ] Important status messages that do not take focus are programmatically exposed; ordinary dynamic content remains discoverable without forced speech
- [ ] The same author, message, result, label, state, or final answer is not encountered twice because of `aria-label`, `aria-labelledby`, hidden text, duplicated responsive DOM, or merged native semantics
- [ ] `role="status"`/`role="alert"` are not combined with redundant implicit `aria-live` values unless a tested compatibility exception is documented
- [ ] AI response streaming is silent token by token; if the product contract requests it, announce “Digitando...” after submission and the final response once, using a transient single channel
- [ ] Modal dialogs announced when opened (name + role)
- [ ] Route changes announced in SPAs
- [ ] A waiting state is announced only when it is a meaningful status message; continuous progress and implementation telemetry do not become unsolicited speech
- [ ] Form submission results announced
