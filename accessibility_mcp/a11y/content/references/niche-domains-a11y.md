# Niche Domains Accessibility Guide (2026)

Specifications for **Accessible Authentication & Passkeys (WCAG 2.2 SC 3.3.7/3.3.8/3.3.9)**, **Data Visualization & Sonification (D3/Chart.js/Highcharts)**, **Kiosk & Self-Service POS Web Interfaces**, and **HTML Email Accessibility**.

---

## 1. Accessible Authentication & Passkeys / WebAuthn

- **WCAG 2.2 SC 3.3.8 (Level AA) & 3.3.9 (Level AAA):** Authentication must NOT require solving cognitive function tests (memorizing passwords, transcribing CAPTCHAs, solving math puzzles).
- **Compliant Mechanisms:** Password Managers (`autocomplete` enabled, copy-paste NEVER blocked), Passkeys / FIDO2 (`autocomplete="username webauthn"` with WebAuthn Conditional UI `PublicKeyCredential.isConditionalMediationAvailable`), Magic Links, OAuth.
- **WCAG 2.2 SC 3.3.7 No Redundant Entry (Level A):** Previously entered form information in a multi-step session must be auto-populated or selectable.

---

## 2. Data Visualization & Chart Accessibility (Sonification)

- **ARIA Graphics Roles:** `<svg role="graphics-document">`, dataset groups `<g role="group">`, nodes `<rect role="graphics-symbol">`.
- **Keyboard Roving Tabindex:** Only active data point has `tabindex="0"`, others `tabindex="-1"`. Arrow keys navigate between data nodes.
- **Web Audio API Data Sonification:** Map data values (e.g. $20k to $80k) to audio frequencies (220Hz to 880Hz) on node focus, giving auditory pitch feedback to blind users.
- **Fallback Data Tables:** Provide linked semantic `<table>` elements (`<caption>`, `<th scope="col|row">`) for screen reader access.

---

## 3. Kiosk & Self-Service POS Hardware/Web Interfaces

- **Headphone Jack Audio Routing:** Use `navigator.mediaDevices.ondevicechange` to detect 3.5mm/USB headset insertion. Automatically activate Privacy Screen Mode (dimming display) and route TTS speech synthesis (`SpeechSynthesisUtterance`) to headphones via `setSinkId`.
- **Tactile Keypad Mapping:** Map hardware keycodes (Storm EZ Access keypads, F1/Help, F2/Privacy Toggle, Arrows, Enter, Escape) to speech and web focus actions.

---

## 4. HTML Email Accessibility

- **Layout Table Roles:** Structural layout tables MUST have `role="presentation"` (or `role="none"`) and explicit `cellspacing="0" cellpadding="0" border="0"`.
- **Semantic Tags in Cells:** Place native `<h1>`, `<p>`, `<a>`, `<strong>` tags inside cells instead of plain text inside `<td>`.
- **Dark Mode Overrides:** Combine `@media (prefers-color-scheme: dark)` with Outlook `[data-ogsc]` / `[data-ogsb]` selector overrides and `<meta name="color-scheme" content="light dark">`.
