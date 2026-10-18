# ARIA, Native Semantics, and Duplicate-Exposure Rules (2026)

Production baseline: HTML ARIA conformance plus WAI-ARIA 1.2. WAI-ARIA 1.3 and AccName 1.2 are Working Drafts; label draft-only patterns and verify support before use.

Official references: [ARIA in HTML](https://www.w3.org/TR/html-aria/), [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/), [WAI-ARIA 1.3 Working Draft](https://www.w3.org/TR/wai-aria-1.3/), [APG Read Me First](https://www.w3.org/WAI/ARIA/apg/practices/read-me-first/), and [APG accessible names](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/).

## 1. ARIA decision procedure

Before adding or retaining any ARIA:

1. Check whether native HTML/platform semantics already provide the role, name, state, keyboard behavior, and focus behavior.
2. Inspect the computed accessibility tree. Do not infer exposure from source markup alone.
3. Check ARIA in HTML for permitted roles and attributes on the exact host element.
4. Implement the complete interaction promised by the role. ARIA changes semantics; it does not add keyboard behavior, focusability, validation, or state management.
5. Test the relevant browser/AT or native platform combination. APG examples illustrate patterns; they do not guarantee every mobile/browser combination.
6. During remediation, remove redundant or harmful ARIA before adding anything new.

No ARIA is better than incorrect ARIA.

## 2. One meaning, one accessible representation

Expose each piece of information once in the effective accessibility tree.

Common duplication failures:

- Visible “IA Assistente” plus `aria-label="Mensagem de IA Assistente"` plus `aria-roledescription="mensagem"` on its container.
- A visible final AI answer plus a permanent visually hidden copy used as a live region.
- A native `<button>` label plus an `aria-label` that repeats or replaces the visible text unnecessarily.
- `role="alert"` combined with redundant `aria-live="assertive"`, producing repeated announcements in some AT.
- A named `<section>` for every visual card, creating excessive region landmarks.
- Compose/SwiftUI parent semantics that repeat all child labels without intentionally merging/removing descendants.
- Desktop and mobile DOM variants both left exposed at the same breakpoint.

Correction rule:

- Keep one persistent visible source of truth.
- Use a transient announcer only when automatic speech is genuinely required; clear its content after the event is queued so it does not become a second browse-mode copy.
- Prefer visible text as the accessible name.
- Name only landmarks that help navigation; a named `<section>` becomes a `region` landmark.
- When merging native-mobile semantics, verify the merged and unmerged trees and eliminate repeated child exposure intentionally.

Test by navigating headings, landmarks, controls, and reading order with the target screen reader. A visually correct interface can still expose duplicates.

## 3. Accessible names and descriptions

- Every interactive control needs a concise accessible name. Prefer visible text, `<label>`, `<legend>`, `<caption>`, and other native naming mechanisms.
- Use `aria-labelledby` when existing visible text should name an element. Use `aria-label` mainly when no suitable visible text exists, such as an icon-only button.
- `aria-labelledby` has higher precedence than `aria-label`; placing both on one element is redundant and confusing, though not syntactically forbidden. Remove the unused source.
- Ensure the accessible name contains the visible label (WCAG 2.5.3 Label in Name).
- Do not use placeholder or `title` as the primary form label.
- Keep names short; put supplementary information in an accessible description only when it adds value.
- Do not name roles that prohibit author naming. Check the role's `nameFrom` definition and ARIA in HTML instead of relying on a copied matrix.
- Avoid empty `aria-label`, broken ID references, duplicated IDs, and labels that conceal useful descendant content.

## 4. Roles, states, and native elements

- Do not add a role identical to a native element's implicit role unless a documented compatibility need requires it.
- Do not override native semantics with an unrelated role. Validate the exact element/role pair using ARIA in HTML.
- Use state attributes only on roles that support them: for example, `aria-pressed` for toggle buttons, `aria-checked` for checkable roles, `aria-selected` for selection roles, and `aria-sort` on row/column headers.
- Keep required ownership/context relationships valid (`tablist`/`tab`, `listbox`/`option`, `menu`/`menuitem`, `tree`/`treeitem`, grid rows/cells).
- Do not use `aria-hidden="true"` on a focusable element or an ancestor of focusable content. Use `inert`, `hidden`, `disabled`, or correct conditional rendering according to intent.
- Do not use `role="application"` as a general fix. It changes screen-reader interaction modes and requires a complete application keyboard model.

## 5. Headings, landmarks, and regions

- Use headings for document outline, not font size, tool status, thought text, or visual card titles.
- Use landmarks for meaningful page areas. A `<section>` becomes a region only when it has an accessible name.
- Label repeated landmarks uniquely. Do not include the role word in the label (for example, label a `nav` “Principal”, not “Navegação principal”).
- Avoid landmark proliferation. Routine AI tool calls, transient progress, and each chat message do not need individual region landmarks.
- Prefer one visible author heading/label per chat message; do not repeat it in the container's accessible name.

## 6. Live regions and dynamic interfaces

- A visual update does not automatically require speech.
- Create any required live region before updating it; use the least disruptive politeness level.
- Do not combine implicit live-region roles with redundant live attributes unless testing demonstrates a specific need.
- Never put interactive controls inside a live-region announcement and expect their semantics to be conveyed through speech.
- Keep streaming tokens, reasoning, tool progress, logs, and navigation details silent by default. Provide bounded, user-approved announcements.
- For the AI-interface default in this skill: announce “Digitando...” after submission, remain silent during work, and announce the complete final response once after a valid success event.

## 7. Keyboard and focus

- Avoid positive `tabindex`. Use natural order, `tabindex="0"` for custom composite entry points, and `tabindex="-1"` for programmatic focus targets.
- Keep a visible focus indicator that meets WCAG 2.2 requirements.
- Do not move focus merely because content streams or status changes. Move it for genuine context changes such as opening a modal, then restore it.
- If a focused item is removed, choose and focus the logical next/previous target instead of allowing focus to fall unpredictably to the document.

## 8. Draft ARIA features

ARIA 1.3 is a Working Draft dated 4 June 2026. Roles such as `code`, `emphasis`, `strong`, `deletion`, `insertion`, `subscript`, `superscript`, `paragraph`, and `time` are forward-looking. In ordinary HTML, continue using `<code>`, `<em>`, `<strong>`, `<del>`, `<ins>`, `<sub>`, `<sup>`, `<p>`, and `<time>`. Do not rely on draft roles without a tested fallback.

## 9. Review checklist

- Is native markup sufficient?
- Does the role match actual behavior?
- Are all attributes allowed for the computed role and host element?
- Is every control named once, with visible text preferred?
- Does the accessibility tree contain duplicate or hidden copies?
- Are landmarks/headings useful rather than noisy?
- Are dynamic announcements necessary, bounded, and non-duplicative?
- Does focus remain visible, logical, and recoverable?
- Has the result been tested with the target AT/platform combination?
