# UX Persona Testing — test like a real user, not like a rule checker (2026)

Automated audits go green while real people fail. This guide is for running a **task-based walkthrough** through a
persistent browser session (`a11y_open` → probes → `a11y_close`), observing what a person would actually experience, and
reporting where they get stuck. The judgment (was it understandable? was it a struggle?) is yours; the tools give facts.

## 1. Personas (enforced by the tools)

| Persona | What the harness enforces | What you look for |
|---|---|---|
| `keyboard` | no mouse: only `press`/`type`/`wait`, reach things with Tab (`a11y_reach`) | reachable in a sane order, visible focus, no trap, Enter/Space/Escape/arrows behave, shortcuts to skip repeated blocks |
| `screen_reader` | no mouse, no screenshots; you only perceive the accessibility tree and announcements | every control has a name, role and state; changes are announced; reading order makes sense; nothing important is visual-only |
| `low_vision` | 320 px viewport (400% zoom) | no horizontal scroll, nothing cut off or overlapping, text still readable, controls still usable |
| `mobile_touch` | phone viewport with touch | target size, spacing between targets, no hover-only features, gestures have alternatives |
| `reduced_motion` | `prefers-reduced-motion` on | no essential motion, no parallax/auto-play that ignores the preference |
| `forced_colors` | Windows high-contrast emulation | borders/icons/focus still visible, no information lost |
| `default` | none | the baseline experience |

Run the important flows in **at least** `keyboard` and `screen_reader`, and check `low_vision` for reflow.
Use different sessions per persona (a new `a11y_open` replaces the previous one).

## 2. How to run a walkthrough

1. **Pick the user's task** in plain words ("find a product and add it to the cart", "sign up", "change my email").
   Not a list of elements: a goal.
2. **Open** the page with the persona (`a11y_open`). Read `a11y_observe`.
3. **Act as that person would**, one step at a time (`a11y_act`, `a11y_reach`). After each step read the effect report:
   did focus go where a user expects? did something announce the change? did the tree change?
4. **Note every friction**, even when nothing "fails": too many Tab presses, an unlabeled control, a status that appears
   silently, a surprise focus jump, a confusing name, a dead end.
5. **Finish or give up.** If the task cannot be completed with this persona, that is the headline finding.
6. **Repeat for the other personas.** Compare the effort: a task that takes 4 steps with a mouse and 60 Tab presses
   with a keyboard is a usability problem even if every element passes an audit.

## 3. What to record per step

- Persona, goal, step number, action taken, what the user perceived (focus, announcement, tree change), and whether the
  outcome was clear.
- Effort: number of steps / Tab presses versus the default persona.
- Blockers vs. friction: **blocker** = cannot proceed; **friction** = can proceed but with avoidable effort or doubt.

## 4. Severity

- **Blocker** — the task cannot be completed (unreachable control, keyboard trap, missing name on the only submit button).
- **Serious** — completing it requires guessing or workarounds (silent errors, focus lost after an action).
- **Moderate** — extra effort or confusion (long Tab path, vague names).
- **Minor** — polish.

## 5. The report (always include)

1. **Scope**: URL, persona(s), tasks attempted.
2. **Outcome per task and persona**: completed / completed with friction / not completed.
3. **Findings**: severity, where, what the user experienced (facts from the tools), why it matters, suggested fix that
   keeps the design (see `component-identity-guide`).
4. **Automated results** (`a11y_audit`, `a11y_stress`) — listed **separately**, and never used as proof of accessibility.
5. **NOT VERIFIED**: what you could not test with these tools — real screen readers (NVDA/JAWS/VoiceOver/TalkBack),
   real devices, real assistive hardware, flows behind logins you did not run, content that changes with data.
   State this explicitly; a walkthrough that hides its limits produces the same false green it is meant to prevent.

## 6. Cautions

- The accessibility tree is a proxy for a screen reader, not the real thing. Announcement wording and browse-mode
  behavior differ per product; recommend a manual pass with NVDA/VoiceOver before sign-off (`nvda-testing-guide`).
- Do not type real credentials or personal data into tested pages; use test accounts and test data.
- One walkthrough is a sample. Say which flows were covered.
