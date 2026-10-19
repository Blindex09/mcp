# WCAG findings with evidence, and the behavior probes (2026)

A finding is only worth reporting if the evidence you measured supports it. Research on agentic auditing (2026) found that
agents catch far more than scanners (keyboard traps, lost focus, modals that leak) but also assert things the page never
showed. The cure is calibration: every finding names its criterion, its element and its evidence, and what the evidence
cannot support is reported as "can't tell", never as a failure.

## 1. How to file a finding

In the autonomous run, put a `finding` object in the step where you notice it:

- `criterion`: the WCAG 2.2 success criterion number (e.g. `2.1.2`). If you are unsure which one, leave it empty. Never invent one.
- `severity`: `blocker` (the task cannot be done), `serious` (done only with great effort or help), `moderate`, `minor`.
- `target`: the dossier id (`e12`) or `css:<selector>` of the element.
- `claim`: one plain sentence stating what is wrong and for whom.
- `evidence_steps`: the step numbers whose result shows it. Without evidence the finding becomes "can't tell".

Hand-driven sessions use `a11y_finding` with the same fields; evidence refers to the numbers in the session trace.

Be specific only about what the facts show. If you say an attribute is missing, the element facts must show it missing. A
native `<dialog>` opened with `showModal()` is modal without `aria-modal`; what it can still lack is an accessible name.

## 2. Which probe proves which criterion

| Probe | What it does | Criteria it gives facts for |
|---|---|---|
| `tab_walk` | Tab from the top to the end: every stop, where focus gets stuck, where it is covered | 2.1.2 No Keyboard Trap, 2.4.3 Focus Order, 2.4.7, 2.4.11 |
| `focus_obscured` | only the stops where a sticky header, banner or overlay covers the focused element | 2.4.11 Focus Not Obscured |
| `target_size` | targets under 24x24 CSS px and the spacing exception | 2.5.8 Target Size (Minimum) |
| `dialog` | opens a modal by keyboard: focus in, name, modal, Tab stays inside, Escape closes, focus returns | 2.1.1, 2.4.3, 4.1.2 |
| `disclosure` | accordion, FAQ, nav submenu: Enter/Space toggle `aria-expanded` and the content | 2.1.1, 4.1.2 |
| `menu` | menu button (role=menu): open keys, focus into items, arrows, Home/End, Escape returns focus | 2.1.1, 2.4.3, 4.1.2 |
| `tabs` | roving tabindex, arrows, Home/End, selected tab linked to its panel, Tab enters the panel | 2.1.1, 2.4.3, 4.1.2 |
| `combobox` | role, `aria-expanded`, active option exposed, arrows, Enter, Escape keeps focus | 2.1.1, 4.1.2 |
| `form_errors` | submits by keyboard and measures: field marked invalid, error tied to the field, focus, announcement | 3.3.1, 3.3.3, 4.1.3 |
| `status_update` | activates a button and measures whether the change reaches someone who cannot see it: pre-existing live region or moved focus, and that focus did not fall to the body | 4.1.3 Status Messages, 2.4.3 |
| `listbox` | role, name, options, one Tab stop, arrows, Home/End, `aria-selected` | 2.1.1, 4.1.2 |
| `tree` | role, name, `aria-expanded` on parents, one Tab stop, arrows, expand/collapse, Home/End | 2.1.1, 4.1.2 |
| `tooltip` | appears on focus, tied by `aria-describedby`, Escape closes without moving focus | 1.4.13, 2.1.1, 4.1.2 |
| `route_change` | activates a link and measures title, focus and announcement of the new screen | 2.4.2, 2.4.3, 4.1.3 |

The contract probes return `checks` with `expected`, `observed` and `met` (true, false, or null when it could not be
measured). `expected` is the WAI-ARIA Authoring Practices pattern. Two judgments stay yours: whether this component was
supposed to follow that pattern at all (a navigation submenu is a disclosure, not a menu), and whether a deviation hurts
the person. A `met: null` is not a pass: it says the probe could not tell (for example the browser's native datalist popup is
invisible to the DOM).

Choosing the probe is part of the judgment: first work out what the component really is (see `component-identity-guide`),
then probe it as that.

## 3. Reporting

Report each confirmed finding with the criterion, the person affected, the evidence and the fix that keeps the design. Say
which findings the verifier could not confirm, and which probes did not run. Green probes prove only the checks they ran.
