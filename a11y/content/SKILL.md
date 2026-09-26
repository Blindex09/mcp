---
name: web-accessibility
description: Build and audit accessible web, mobile web, Android, and iOS interfaces. Covers HTML, CSS, JavaScript, TypeScript, React, Angular, AJAX/SPA, Kotlin/Jetpack Compose, and SwiftUI/UIKit; WCAG 2.2 AA, WCAG2Mobile/WCAG2ICT guidance, careful ARIA and native semantics, focus, touch, screen readers, AI-agent response interfaces, and retrofit work. Use when asked to create or correct accessible interfaces, audit WCAG, add NVDA/VoiceOver/TalkBack support, fix keyboard/touch navigation, or build accessible AI chat and tool-execution experiences.
---

# Web and Mobile Accessibility Skill (2026)

Use WCAG 2.2 AA as the web conformance baseline. Treat WCAG 3.0 (Working Draft, 3 Mar 2026), WAI-ARIA 1.3 (Working Draft, 4 Jun 2026), and AccName 1.2 (Working Draft) as research, not production conformance standards. Re-check changing framework, browser, operating-system, and assistive-technology behavior against official documentation.

## 0. Scope and evidence level

- **Tier 1 — audited core:** HTML, CSS, JS, TS, React, Angular, AJAX/SPA, mobile web, Android Kotlin/Jetpack Compose, and iOS SwiftUI/UIKit. Require native semantics first, automated checks where available, and manual NVDA/VoiceOver/TalkBack verification.
- **Tier 2 — starting pointers:** Vue/Nuxt, Svelte, C#/.NET, Flutter/Dart, Rust, Python UI frameworks, PHP/Laravel, and Ruby/Rails in [references/multilanguage-multiplatform-a11y.md](references/multilanguage-multiplatform-a11y.md). Research current official platform guidance before shipping; a pointer is not implementation certification.
- Known gaps: Elixir/Phoenix LiveView and Go+htmx do not yet have dedicated coverage.

## 0.1 Using this skill through the MCP server

This skill ships inside the Accessibility MCP server (`a11y/`). Every `references/x.md` link below is the guide named `x`
for `a11y_get_reference`, and every `examples/y.ext` is the example named `y` for `a11y_get_example`.

| Need | Tool |
|---|---|
| See what exists (summary + sections of every guide/example) | `a11y_list_content` |
| Let the model pick the right guides/examples for a task described in plain language | `a11y_find(task)` |
| Read a guide (or one section of it) / get component source | `a11y_get_reference(name, section)` / `a11y_get_example(name)` |
| Get a file of the accessible AI React template or an audit script (`assets/...`, `scripts/...`) | `a11y_get_template(path)` |
| WCAG contrast ratio between two colors | `a11y_contrast` |
| Automated axe-core audit of a URL (http/https) or HTML string | `a11y_audit` |
| Accessibility tree, i.e. what a screen reader receives | `a11y_aria_snapshot` |
| Keyboard focus order, names, focus indicators | `a11y_tab_order` |

Selection of what to read is done by a model, never by keyword. The measurement tools (`a11y_contrast`, `a11y_audit`,
`a11y_aria_snapshot`, `a11y_tab_order`) report facts; interpreting them and deciding the fix stays with you.
They cover only part of WCAG: keyboard, screen-reader and touch checks remain manual (section 5).
Browser-based tools need `python -m playwright install chromium` once.

### Testing like a user (session tools)

A green audit is not accessibility. To find what really happens, open a persistent session and act as the user:

| Need | Tool |
|---|---|
| Start/stop a session with an enforced persona (`keyboard`, `screen_reader`, `low_vision`, `mobile_touch`, `reduced_motion`, `forced_colors`) | `a11y_open` / `a11y_close` |
| Facts about every interactive element, to decide what each one really is in this site | `a11y_dossier` |
| Do what a user does and get the effect (focus, tree changes, announcements) | `a11y_act` |
| Tab presses needed to reach an element; what a screen reader gets for it | `a11y_reach` / `a11y_announce` |
| Reflow at 320 px, text-spacing clipping | `a11y_stress` |
| The site's real design language; try a change temporarily; look at it | `a11y_design_tokens` / `a11y_preview_css` / `a11y_screenshot` |

Coverage: `a11y_page_map` returns FACTS about ALL content (headings/outline, landmarks, images and alt, links, forms, tables, media, iframes, live regions, reading order,
`:hover` rules) including open Shadow DOM and each iframe; `a11y_dossier` crosses Shadow DOM and iframes; `a11y_coverage` lists what was and was NOT covered (include it
in every report); `a11y_crawl` scans several pages (facts only; robots.txt; GET only). On non-local sites, requests that change data are blocked unless `allow_mutations=allow`.
Judge the content with [references/page-structure-review.md](references/page-structure-review.md) and widgets beyond the classic eleven with
[references/more-component-patterns.md](references/more-component-patterns.md).

Browsers: `a11y_open`, `a11y_audit`, `a11y_aria_snapshot`, `a11y_tab_order`, `a11y_walkthrough` and `a11y_review` take `browser` (chromium default, firefox, webkit;
installed automatically). Chromium is the most precise; Firefox/WebKit results list their limits. `a11y_compare_browsers` shows the same page side by side
(facts only); see [references/cross-browser-a11y.md](references/cross-browser-a11y.md).

Autonomous user: `a11y_walkthrough(task, persona)` and `a11y_review(focus)` run a model as the person (with screenshots and the accessibility
tree) and return a plain-language report; `a11y_close` interrupts them; `a11y_status` shows readiness. `a11y_focus_style` gives the facts of what :focus changes.
`a11y_dossier` reports role/name **as computed by the browser** and whether each element is focusable/clickable (an element that is clickable but not
focusable, with no role, is a mouse-only control).

How to judge: [references/component-identity-guide.md](references/component-identity-guide.md) (what is this element, in this site),
[references/ux-persona-testing.md](references/ux-persona-testing.md) (task-based walkthroughs and the report, including what was NOT verified),
[references/design-language-review.md](references/design-language-review.md) (typography/spacing suggestions inside the site's own scale).

## 1. References by domain

Read only what the task needs.

### A. Foundations, ARIA, audit, and testing

- [references/component-identity-guide.md](references/component-identity-guide.md), [references/ux-persona-testing.md](references/ux-persona-testing.md), [references/design-language-review.md](references/design-language-review.md): judging what components are, testing like a user, and design review.
- [references/aria-rules-dos-and-donts.md](references/aria-rules-dos-and-donts.md): native semantics, careful ARIA, accessible-name duplication, roles/states, and focus.
- [references/audit-checklist.md](references/audit-checklist.md): automated and manual audit workflow.
- [references/nvda-testing-guide.md](references/nvda-testing-guide.md): NVDA/browser testing.
- [references/cognitive-lowvision-motor.md](references/cognitive-lowvision-motor.md), [references/predictability-understandable.md](references/predictability-understandable.md), [references/i18n-rtl-a11y.md](references/i18n-rtl-a11y.md).

### B. AI, agents, streaming, and tools

- [references/ai-conversational-a11y.md](references/ai-conversational-a11y.md): provider-neutral response, announcement, semantic rendering, and transcript contract.
- [references/agentic-ai-messaging-a11y.md](references/agentic-ai-messaging-a11y.md): tools, file/command operations, HITL, diffs, and artifacts.
- [references/ollama-realtime-agent-ui.md](references/ollama-realtime-agent-ui.md): Ollama adapter; keep the frontend contract provider-neutral.
- [references/accessible-ai-code-template.md](references/accessible-ai-code-template.md) and [assets/accessible-ai-react](assets/accessible-ai-react): copyable React implementation of the accessible AI/agent presentation contract. Reuse its reducer, stream parser, announcement channel, semantic turn rendering, tool grouping, media behavior, and HITL dialog; adapt styling and product policy without weakening the invariants.

### C. Components, platforms, and architecture

- [references/ui-components-apg.md](references/ui-components-apg.md), [references/complex-components.md](references/complex-components.md), [references/web-components-a11y.md](references/web-components-a11y.md).
- [references/frameworks-mobile-a11y.md](references/frameworks-mobile-a11y.md), [references/emerging-web-apis-standards.md](references/emerging-web-apis-standards.md), [references/enterprise-architecture.md](references/enterprise-architecture.md), [references/legacy-refactoring.md](references/legacy-refactoring.md).
- [references/mobile-cognitive-media-svg-headings.md](references/mobile-cognitive-media-svg-headings.md), [references/documents-media-a11y.md](references/documents-media-a11y.md), [references/electron-desktop-a11y.md](references/electron-desktop-a11y.md).

### D. Specialized and extended domains

- [references/niche-domains-a11y.md](references/niche-domains-a11y.md), [references/spatial-xr-3d-gaming.md](references/spatial-xr-3d-gaming.md), [references/multilanguage-multiplatform-a11y.md](references/multilanguage-multiplatform-a11y.md), [references/accessibility-statement.md](references/accessibility-statement.md).
- Auditors: [scripts/audit-axe.js](scripts/audit-axe.js), [scripts/audit-contrast.js](scripts/audit-contrast.js). Implementations: [examples/](examples/).

## 2. Core rules

1. **Use native semantics first.** Prefer `<button>`, `<a href>`, `<input>`, `<dialog>`, `<nav>`, and `<main>`. Add ARIA only for a semantic gap.
2. **Make interaction input-independent.** Support keyboard, switch, pointer, touch, zoom, and screen-reader gestures. WCAG 2.2 SC 2.5.8 AA requires 24×24 CSS px or an allowed exception; prefer 44×44 CSS px where practical. Follow 44 pt on iOS and 48 dp on Android.
3. **Keep focus visible and predictable.** Never remove focus styling without an equivalent. Move focus only when context truly changes; restore it after dialogs and destructive removal.
4. **Meet contrast and reflow baselines.** Use WCAG 2.2 ratios and test text spacing, 320 CSS px reflow, zoom, forced colors, dark mode, and user font scaling.
5. **Give controls concise names.** Prefer visible native labels. Ensure label-in-name. Do not overwrite useful visible text with unnecessary `aria-label`.
6. **Use live announcements sparingly.** A changing visual interface does not automatically need speech. Avoid per-token/per-progress announcements; provide user control and bounded terminal announcements.
7. **Honor user preferences.** Support reduced motion, contrast/forced colors, color scheme, text size, Dynamic Type, Android font scaling, and platform accessibility settings.
8. **Test manually.** Automated tools find only a subset of defects. Test keyboard/touch/switch flows and the actual accessibility tree with relevant browser/AT/platform combinations.
9. **Fix source code, not overlays.** Accessibility overlays cannot repair semantics, interaction contracts, or focus architecture reliably.
10. **Expose one meaning once.** Do not expose the same author, response, status, label, instruction, or control twice through visible text plus redundant ARIA, duplicate live-region copies, mirrored DOM, or merged mobile semantics.
11. **Treat ARIA as a surgical tool.** Every role is a behavioral promise. Verify allowed roles/attributes, accessible-name computation, focus, keyboard behavior, and AT output. During remediation, remove harmful/redundant ARIA instead of layering more ARIA over incorrect markup.
12. **Keep drafts labeled.** Never present WCAG 3, WAI-ARIA 1.3, experimental HTML/CSS APIs, or vendor behavior as stable normative requirements.
13. **Structure repeated peer items.** Render shortcuts, related options, action sets, steps, results, and similar repeated items as separate visual rows and semantic list items when they form a list. Do not concatenate controls or sentences in one paragraph/container, and do not use spaces, punctuation, `<br>`, or ARIA as a substitute for `<ul>`/`<ol>` and `<li>`. Preserve one independently focusable native control per action. See [references/ui-components-apg.md](references/ui-components-apg.md#12-repeated-options-shortcuts-and-action-sets).

## 3. Component selection

```text
Need an interaction?
├── Native element expresses it? → use native HTML/platform control
├── Modal/blocking? → native dialog/platform modal + initial focus + containment + return focus
├── Show/hide content? → details/summary or button with aria-expanded + aria-controls
├── Select one value? → native select/radio first; custom listbox only when required
├── Actions menu? → menu pattern only for application-style commands
├── Tabs? → tablist/tab/tabpanel with documented arrow-key behavior
└── Composite custom widget? → use the relevant APG/platform pattern and test support
```

Do not infer that every visually separated block needs a region or heading. Landmarks and headings represent meaningful document structure; operational AI states and routine tool progress are ordinary text.

## 4. Stack guidance

- **HTML/mobile web:** semantic HTML, progressive enhancement, responsive reflow, touch plus keyboard, NVDA/VoiceOver/TalkBack browser tests.
- **React:** prefer React Aria Components or well-tested primitives; preserve native DOM semantics and focus.
- **Angular:** use official Angular Aria/CDK patterns and verify actual package APIs for the project version.
- **Android:** prefer Material/Compose semantics, built-in controls, TalkBack/Switch Access, 48 dp targets, font scaling, and Compose accessibility checks.
- **iOS:** prefer SwiftUI/UIKit semantics, VoiceOver/Voice Control/Switch Control, 44 pt targets, Dynamic Type, and Accessibility Inspector.
- **Experimental APIs:** feature-detect, provide a semantic fallback, and do not rely on draft ARIA roles in production without support testing.

## 5. Audit and retrofit workflow

1. Inventory target platforms, browsers, AT, input methods, and conformance level.
2. Inspect DOM/native semantics and the computed accessibility tree for duplicate, missing, overridden, or hidden information.
3. Run automated validation, axe/Lighthouse/platform checks, syntax/build checks, and framework linters (via the MCP: `a11y_audit`, `a11y_aria_snapshot`, `a11y_tab_order`, `a11y_contrast`).
4. Complete keyboard, touch, zoom/reflow, screen-reader, focus, error, and dynamic-content flows manually.
5. Correct native structure first; then add only necessary ARIA/platform semantics.
6. Retest accessible names, roles, states, focus, announcements, reading order, and singular/plural localized text.
7. Add regression tests and document untested combinations or experimental dependencies.

For the full process, read [references/audit-checklist.md](references/audit-checklist.md).
