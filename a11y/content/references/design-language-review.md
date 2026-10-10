# Design Language Review — typography, spacing and color that serve people, inside the site's own style (2026)

Goal: suggest improvements (font, size, weight, line-height, spacing, contrast, target size) **without breaking the
site's design**. The site's own scale is the reference; you propose changes that stay inside it, or that extend it
coherently, and you justify each one. These are suggestions with reasons, not verdicts of taste.

## 1. Measure first (`a11y_design_tokens`, `a11y_dossier`)

Read what the site actually uses: type styles with counts and examples, font families, sizes, weights, colors, spacing
values, radii, `:root` variables, paragraph widths. From this infer the site's **scale**:

- Is there a size ramp (e.g. 14/16/20/28) or is it ad hoc (14/15/16/17/19)? Which styles are used the most?
- Which font families carry the brand and which appear to be accidents (one-off, fallback leakage)?
- Is spacing built on a base unit (4/8) or scattered?
- Which colors are the text/background system, which are one-offs?

## 2. Review against people, then against the site

Check the site's real usage against what people need, and note where the two disagree:

- **Body text**: comfortable size (about 16 px or more for continuous text), line-height around 1.5 for paragraphs, line
  length roughly 45–75 characters; nothing that breaks when the user increases text spacing (`a11y_stress text_spacing`).
- **Hierarchy**: headings clearly differ from body by size/weight/spacing, in a consistent ramp; one obvious h1.
- **Contrast**: text and meaningful graphics meet WCAG ratios in every state (hover, focus, disabled, error), not only
  the primary one (`a11y_contrast`, `a11y_audit`).
- **Touch/pointer targets**: at least 24×24 CSS px (WCAG 2.2), preferably ~44 px on touch, with space around them.
- **Focus**: a visible, high-contrast indicator that fits the site's look (outline/offset/radius from its tokens).
- **Consistency**: the same role looks the same everywhere (all secondary buttons alike, all inputs alike).
- **Reflow/zoom**: nothing cut off at 320 px (`a11y_stress reflow_320`) or at large text sizes.

## 3. Propose inside the site's scale

- Prefer an **existing** token/size/weight from the site's ramp over a new value. If none fits, propose the nearest
  step that keeps the ramp's logic (e.g. same modular ratio) and say so.
- Keep the **font family** unless it is the problem (legibility, missing weights, poor small-size rendering); if you
  suggest another, say why and offer a fallback stack that matches metrics.
- Change **one thing at a time**, with the smallest effect that fixes the issue (size before font swap, line-height before
  layout changes).
- Keep hierarchy relationships: if body grows, adjust headings so the ramp still reads.

## 4. Try it before recommending it

Use `a11y_preview_css` to apply the proposal temporarily to a representative element (the site is untouched), then
`a11y_screenshot` before/after and re-run the checks that matter (`a11y_stress`, contrast). Revert with `revert=true`.
Recommend only what you tried and saw working; mention what you did not try (other pages, breakpoints, dark mode).

## 5. Deliver each suggestion as

1. **Where** (element/style, with an example from the dossier or tokens).
2. **What the site does today** (measured values) and **why it is a problem for people** (or an inconsistency).
3. **Suggestion** (exact values, using the site's tokens where possible) and **why it fits this design**.
4. **Evidence** (preview + screenshot, stress result) and **risk** (what might change elsewhere).
5. Mark it clearly as a **design suggestion**; accessibility failures with a normative criterion are reported separately
   from matters of taste.
