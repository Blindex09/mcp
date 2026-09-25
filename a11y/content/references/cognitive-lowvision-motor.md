# Cognitive, Low-Vision & Motor Accessibility Guide (2026)

Specifications for WCAG 3.0 cognitive outcomes, timeout extensions (SC 2.2.1), 400% zoom reflow (SC 1.4.10), text spacing (SC 1.4.12), Label in Name (SC 2.5.3), and Forced-Colors Mode.

---

## 1. WCAG 3.0 Cognitive Outcome Guidelines

- **Standard Status:** WCAG 3.0 is an incomplete Working Draft with no reliable Recommendation date. WCAG 2.2 AA remains the standard baseline.
- **Functional Outcomes:**
  - **Memory Support:** Eliminate time-sensitive memory tests, support auto-fill, passkeys, and persistent process summaries.
  - **Clarity & Structure:** Plain language, clear typography, step-by-step progress indicators.
  - **Focus & Attention:** Prevent unexpected context shifts, minimize non-essential animations.
  - **Error Prevention & Recovery:** Inline validation, clear non-jargon error descriptions, single-click undo.

---

## 2. SC 2.2.1 Timing Adjustable (Level A) - Timeout Extensions

When sessions have time limits:
- **Advance Warning:** Present `role="alertdialog"` notice before expiry.
- **20-Second Window:** User must have at least 20 seconds to respond.
- **Simple Action:** Single button press ("Extend Session") extends timer.
- **10 Extensions:** Must allow extending at least 10 times.

---

## 3. SC 1.4.10 Reflow (Level AA) - 400% Zoom Math & CSS

- **Math Baseline:** $1280\text{px} / 4 = \mathbf{320\text{ CSS px}}$ viewport width baseline. Content must reflow into a single column without horizontal scrolling at 320px width.
- **CSS Techniques:** Use auto-fit grid (`grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr))`) and `overflow-wrap: break-word`. Avoid fixed container widths (`width: 500px`).

---

## 4. SC 1.4.12 Text Spacing Overrides (Level AA)

Layouts must remain fully functional when user stylesheets apply:
- Line height: $\ge 1.5\times$ font size (use unitless `line-height: 1.5`).
- Paragraph spacing: $\ge 2\times$ font size.
- Letter spacing: $\ge 0.12\times$ font size.
- Word spacing: $\ge 0.16\times$ font size.
- **Rules:** Never use fixed container heights (`height: 40px`) or `overflow: hidden` on text wrappers.

---

## 5. SC 2.5.3 Label in Name (Level A) - Speech Recognition

For voice control users (Apple Voice Control, Dragon):
- The programmatic accessible name must contain the visible label text, subject to WCAG's case, punctuation, symbolic-text, and parenthetical-content interpretations. Matching the visible wording and order is the safest default; “verbatim” is not the normative test in every case.
- **Best Practice:** Front-load visual text in `aria-label` (e.g. `aria-label="Filter products by price"` for visual text "Filter").

---

## 6. Custom Forced-Colors Mode Implementations

Target `@media (forced-colors: active)` in CSS and use System Color Keywords:
- `Canvas` (background), `CanvasText` (body text), `ButtonFace` (button background), `ButtonText` (button text), `ButtonBorder`, `Highlight` / `HighlightText` (active/focused items), `GrayText` (disabled controls).
- Use `border: 2px solid transparent;` in base styles to reserve border space when forced-colors mode injects `ButtonText` border colors.
- Use `forced-color-adjust: none;` ONLY for color swatches where color itself is essential data.

---

## 7. Color Contrast — WCAG 2.x Ratio vs WCAG 3.0 APCA (do not switch early)

- **Standard Baseline (2026): WCAG 2.1/2.2 AA** — 4.5:1 normal text, 3:1 large text (≥18pt or ≥14pt bold) and UI components (SC 1.4.3 / 1.4.11). **Do NOT drop WCAG 2 conformance based on a draft.**
- **WCAG 3.0 contrast confirmation (March 2026 Working Draft):** The contrast algorithm in WCAG 3.0 is **"yet to be determined."** APCA (Advanced Perceptual Contrast Algorithm) was marked for REMOVAL from the WCAG 3.0 draft in early 2023 and remains Exploratory — it is NOT normative. The draft's "visual contrast" requirement currently reads as a placeholder.
- **Experimental metrics:** APCA and other perceptual methods may be explored as non-conformance design research, but their claims and thresholds require separate evidence. Do not present them as WCAG 3 requirements or substitutes for WCAG 2.2.
- **Recommended posture:** Build and test to WCAG 2.2 AA. Treat SC 2.4.13 Focus Appearance as AAA enhancement guidance, not an AA requirement.
