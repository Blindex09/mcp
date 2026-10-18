# Enterprise Web Application Accessibility Architecture (2026)

Architecture standards for large-scale web applications, micro-frontends, design systems, and CI/CD pipelines.

---

## 1. Micro-Frontends (MFE) Accessibility Coordination

In micro-frontend architectures (Module Federation, Single-SPA):

### A. Global Single-Instance Announcer
- **Shell Ownership:** The root Shell application owns the single persistent `aria-live` container (`polite` and `assertive` channels). MFEs must not instantiate independent live region containers to prevent race conditions or speech truncation.
- **Decoupled Event Bus:** MFEs dispatch custom events (`a11y-announce`) over a shared event bus:
  ```typescript
  window.dispatchEvent(new CustomEvent('a11y-announce', {
    detail: { message: 'Item added to cart', politeness: 'polite' }
  }));
  ```

### B. Cross-Boundary Routing & Focus Management
- **Routing Sequence:** Shell router updates `document.title`, announces route change, and shifts focus to incoming MFE's `<h1 tabindex="-1">` or `<main tabindex="-1">`.
- **Singleton Focus Manager:** Shared focus manager service prevents "focus loss" (falling back to `document.body`) when an MFE unmounts.
- **Landmark Disambiguation:** Shell owns top-level landmarks (`<header>`, `<main>`, `<nav>`, `<footer>`). MFEs use `aria-label` or `aria-labelledby` when adding secondary navigation or region landmarks.

---

## 2. Token-Based Accessibility Architecture (W3C DTCG Standard)

Design tokens following W3C DTCG specifications embed accessibility constraints into design assets:

### A. Token Metadata Format
```json
{
  "color": {
    "text": {
      "primary": {
        "$value": "#0f172a",
        "$type": "color",
        "$description": "Primary body text. Meets WCAG 2.2 AA (4.5:1) against surface.primary.",
        "$extensions": {
          "a11y": {
            "wcagCriterion": "1.4.3",
            "minRatio": 4.5,
            "targetSurface": "color.surface.primary"
          }
        }
      }
    }
  }
}
```

### B. Contrast validation
- **WCAG 2.2 Ratios:** 4.5:1 for regular text, 3:1 for large text / UI elements.
- Experimental perceptual methods may be recorded as optional research metrics, but must not replace WCAG 2.2 conformance checks or be presented as WCAG 3 requirements.

### C. Focus Ring Tokens (WCAG 2.2 SC 2.4.11 / 2.4.13)
Define composite focus-ring tokens that remain visible and unobscured. Treat the stricter WCAG 2.2 SC 2.4.13 AAA area/contrast requirements as an enhancement, not an AA requirement.

---

## 3. Automated CI/CD Pipelines & SARIF Integration

- **Playwright + `@axe-core/playwright`:** Standardized fixture scanning for `wcag2a`, `wcag2aa`, `wcag22aa` tags.
- **Parallel Sharding:** Run Playwright accessibility test matrix in parallel using `--shard=x/y` for sub-5-minute PR builds.
- **SARIF Code Reviews:** Convert axe test output to SARIF (`axe-sarif-converter`) to post inline PR review comments on Github/Gitlab PRs. Block builds on any new `critical` or `serious` violations.

---

## 4. Continuous Monitoring & Governance

- **Hybrid Monitoring:** Combine automated synthetic headless browser crawlers with lightweight real-user monitoring (RUM) telemetry catching dynamic focus traps or missing labels.
- **Team Attribution:** Map URL/component violations to specific engineering teams via `CODEOWNERS` for automated ticket creation (Jira / Linear).
