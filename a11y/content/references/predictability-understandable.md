# WCAG Guideline 3.2 Predictable (Previsibilidade) — 2026 Standards & Implementation Guide

Comprehensive specifications, code patterns, anti-patterns, framework examples (React 19, Angular 21, Microfrontends), and Assistive Technology (AT) expectations for **WCAG Guideline 3.2 Predictable (Previsibilidade)**.

---

## 1. Executive Summary & Overview

WCAG Guideline 3.2 ensures that web user interfaces operate and appear in predictable ways. Predictability is a foundational pillar of digital accessibility: users with visual impairments, motor disabilities, or cognitive/neurological variations rely on consistent mental models, stable focus states, and spatial memory to navigate digital experiences effectively.

In modern 2026 frontend architectures (Single Page Applications, React 19, Angular 21, Microfrontends, Design Systems), dynamic rendering and client-side routing introduce significant risks of violating Guideline 3.2 if state changes, focus transitions, and DOM order are not deliberately managed.

---

## 2. Success Criteria Specifications (WCAG 2.2 AA / AAA)

### A. SC 3.2.1 On Focus (Level A) — No Context Change on Focus
> **Requirement:** When any component receives focus, it does not initiate a change of context.

- **Definition of "Change of Context":** A major shift in the user environment that, if made without user awareness, disorients the user (e.g., opening a new window/tab, launching a modal, navigating to a new route, submitting a form, or shifting focus away).
- **Anti-Patterns:**
  - `onFocus={() => navigate('/page')}`: Auto-routing on focus.
  - Auto-modal launch or form submission on input focus.
- **2026 Framework Patterns:**
  - **React 19:** Focus event listeners (`onFocus`) must strictly be reserved for non-contextual visual side effects (focus ring highlighting, tooltip display). Action execution must be bound to explicit user gestures (`onClick`, `onKeyDown` with `Enter`/`Space`).
  - **Angular 21:** Use Angular CDK's `FocusMonitor` exclusively to detect focus origin (`mouse`, `keyboard`, `touch`) for visual styling, *never* to trigger `Router.navigate()` or `MatDialog.open()`.
- **AT Impact:** Moving focus onto an element triggers NVDA, JAWS, VoiceOver, or TalkBack to speak its label, role, and state. If focus triggers a context change, the virtual buffer is wiped, speech is truncated, and focus is displaced—leaving the user stranded.

---

### B. SC 3.2.2 On Input (Level A) — No Context Change on Input without Warning
> **Requirement:** Changing the setting of any user interface component does not automatically cause a change of context unless the user has been advised of the behavior before using the component.

- **Content Update vs. Context Change:**
  - *Allowed (Content Update):* Selecting a checkbox dynamically displays additional form fields *below* the checkbox without moving focus or reloading the page.
  - *Violative (Context Change):* Selecting an option from a `<select>` or radio group immediately submits the form, reloads the page, or shifts focus to a new view without prior warning.
- **2026 Compliant Implementation Patterns:**
  1. **Explicit Action Pattern (Recommended):** Require the user to activate a distinct `<button type="submit">` after changing input settings.
  2. **Prior Warning Pattern:** If auto-apply/auto-redirect on selection is functionally required, warn the user *prior* to interaction using `aria-describedby` or visible helper text directly associated with the input.
- **AT Gotcha:** On Windows screen readers (NVDA/JAWS), navigating dropdown options via keyboard arrow keys fires the `change` event on every arrow press. Auto-navigate `onChange` handlers redirect the user on the very first down-arrow press before they can inspect other options.

---

### C. SC 3.2.3 Consistent Navigation (Level AA)
> **Requirement:** Navigational mechanisms that are repeated on multiple Web pages within a set of Web pages occur in the same relative order each time they are presented, unless a change is initiated by the user.

- **MFE & SPA Architecture:** Primary navigation and layout shells must be governed exclusively by the MFE Shell / Host Orchestrator (`AppShellHost`). Sub-apps (child MFEs) render within dedicated main content slots (`<main>`) and cannot alter global navigation DOM order.
- **AT Impact:** Screen reader users rely on landmark keys (`D` in NVDA/JAWS, Rotor in VoiceOver) to jump to Navigation or Main content. Altering relative DOM order breaks landmark navigation habits and spatial memory.

---

### D. SC 3.2.4 Consistent Identification (Level AA)
> **Requirement:** Components that have the same functionality within a set of Web pages are identified consistently.

- **Design System Governance:** Enforce centralized Design Systems (`@org/design-system`) where UI primitives (e.g., `<SearchButton>`, `<PrintAction>`) encapsulate their icons, roles, and `aria-label` definitions as immutable component props.
- **Voice Control Impact:** Speech recognition users (Apple Voice Control, Dragon) speak visible labels or accessible names ("Click Search"). Inconsistent naming forces users to relearn speech commands on every view.

---

### E. SC 3.2.5 Change on Request (Level AAA)
> **Requirement:** Changes of context are initiated only by user request or a mechanism is available to turn off such changes.

- **Live Data Feeds:** High-frequency data feeds (WebSockets, RxJS streams) must provide a visible toggle control (`[Pause Live Updates]`) so users can prevent automated DOM updates from interrupting reading.
- **Session Timeout Warnings:** Session expiration warnings must notify users gracefully via `aria-live="polite"` or non-disruptive dialogs that allow extending the session without forcibly stealing focus away from active inputs.

---

### F. SC 3.2.6 Consistent Help (WCAG 2.2 Level A / 2.2 AA Conformance)
> **Requirement:** If a Web page contains help mechanisms (human contact details, contact forms, FAQs, AI Chatbots), they occur in the same relative order relative to other page content across pages.

- **MFE & Chatbot Pattern:** Instantiated at Application Shell level (global footer or persistent root container) so DOM position stays stable across microfrontend route transitions.

---

## 3. Code Patterns & Examples (2026 Specs)

### A. React 19 Examples

#### SC 3.2.2 Anti-Pattern (Violative Auto-Navigate Select)
```tsx
// ❌ VIOLATION (SC 3.2.2): Changing selection causes immediate unannounced navigation
export function BadLanguageSelector() {
  const navigate = useNavigate();
  return (
    <select onChange={(e) => navigate(`/locale/${e.target.value}`)}>
      <option value="en">English</option>
      <option value="pt">Português</option>
    </select>
  );
}
```

#### SC 3.2.2 Compliant Pattern (Explicit Submit Trigger — Recommended)
```tsx
// ✅ COMPLIANT (SC 3.2.2): Context change happens only when user activates button
export function CompliantLanguageSelector() {
  const [locale, setLocale] = useState('en');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/locale/${locale}`);
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-center">
      <label htmlFor="locale-select" className="sr-only">Select Language</label>
      <select 
        id="locale-select" 
        value={locale} 
        onChange={(e) => setLocale(e.target.value)}
      >
        <option value="en">English</option>
        <option value="pt">Português</option>
      </select>
      <button type="submit" className="btn-primary">
        Change Language
      </button>
    </form>
  );
}
```

---

### B. Angular 21 Pattern (SC 3.2.1 On Focus)

```typescript
// ✅ COMPLIANT (SC 3.2.1): FocusMonitor strictly handles visual ring focus; modal opens on explicit click
import { Component, ElementRef, inject, viewChild } from '@angular/core';
import { FocusMonitor } from '@angular/cdk/a11y';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-predictable-search',
  standalone: true,
  template: `
    <div class="search-wrapper">
      <input #searchInput type="text" placeholder="Search site..." aria-label="Search site" />
      <button type="button" (click)="openSearchModal()" aria-label="Submit Search">
        <svg aria-hidden="true" ...></svg>
      </button>
    </div>
  `
})
export class CompliantSearchComponent {
  private focusMonitor = inject(FocusMonitor);
  private dialog = inject(MatDialog);
  private searchInput = viewChild<ElementRef<HTMLInputElement>>('searchInput');

  ngAfterViewInit() {
    const el = this.searchInput()?.nativeElement;
    if (el) {
      this.focusMonitor.monitor(el).subscribe(origin => {
        // Purely aesthetic state handling — NO context change on focus!
      });
    }
  }

  openSearchModal() {
    this.dialog.open(SearchModalComponent); // Triggered by explicit user click
  }
}
```

---

### C. Microfrontend (MFE) Shell Architecture Blueprint

```tsx
// ✅ COMPLIANT MFE HOST SHELL (React 19 / Module Federation Orchestrator)
// Guarantees SC 3.2.3 (Navigation), SC 3.2.4 (Identification), SC 3.2.6 (Help)
export function AppShellHost() {
  return (
    <div className="app-shell-container">
      {/* SC 3.2.3: Global Header & Nav rendered exclusively by Host Shell */}
      <header className="global-header">
        <a href="#main-content" className="skip-link">Skip to main content</a>
        <GlobalBrandLogo />
        <GlobalHeaderNav /> {/* Consistent Order Across All MFEs */}
        <DesignSystemSearchInput /> {/* SC 3.2.4: Consistent Identification */}
      </header>

      {/* Dynamic Child Microfrontend Outlet */}
      <main id="main-content" tabIndex={-1}>
        <React.Suspense fallback={<MfeLoadingSpinner />}>
          <MicroFrontendOutlet /> 
        </React.Suspense>
      </main>

      {/* Global Footer & Help Widgets */}
      <footer className="global-footer">
        <GlobalFooterLinks />
        {/* SC 3.2.6: Consistent Help Mechanism in identical relative DOM order */}
        <div id="help-mechanism-container">
          <AiSupportChatWidget />
          <a href="/support/contact">Contact Support</a>
        </div>
      </footer>
    </div>
  );
}
```

---

## 4. Assistive Technology Impact Matrix

| Assistive Technology | SC 3.2.1 & 3.2.2 Impact (On Focus / Input) | SC 3.2.3, 3.2.4, 3.2.6 Impact (Navigation, ID, Help) |
| :--- | :--- | :--- |
| **NVDA / JAWS (Windows)** | Unexpected focus shifts cause screen reader to force-switch between Browse Mode and Focus Mode. Speech output is truncated, causing loss of reading position. | Landmark navigation (key `D` or `N`) relies on predictable DOM position. Consistent identification prevents confusion in Elements List (`Insert+F7`). |
| **VoiceOver (macOS / iOS)** | Focus shifts during focus/input events break VoiceOver Rotor navigation trees and reset gesture focus to the top-left screen boundary. | Rotor "Landmarks" and "Help" links require constant relative DOM ordering across views for muscle-memory swipe gestures. |
| **TalkBack (Android)** | Auto-submits on radio selection or focus redirect Android users back to top status bar, forcing a full screen re-scan. | Consistent component labels ensure screen reader audio cues match interactive touch targets. |
| **Screen Magnifiers (ZoomText)** | Focus shifts cause severe **"Viewport Jumping"**, violently panning the zoomed viewport across the screen, causing visual fatigue. | Users with narrow visible viewports rely on consistent corner/edge locations for menus, search buttons, and support links. |
| **Switch Access / Motor Keyboards** | Auto-actions on focus destroy sequential scanning loops, forcing switch users to start scan sequences from the beginning. | Predictable tab order eliminates unnecessary switch activations required to navigate reordered menus. |

---

## 5. Verification Checklist for WCAG 3.2 Compliance

- [ ] **3.2.1 On Focus (A):** Focus events (`onFocus`, `(focus)`) are strictly used for visual ring styling, never for navigation or modal launches.
- [ ] **3.2.2 On Input (A):** Select menus, radio groups, and text fields do not auto-submit or auto-navigate unless explicitly preceded by an inline warning.
- [ ] **3.2.3 Consistent Navigation (AA):** Page headers, sidebars, and main navigation links maintain identical relative DOM order across all views.
- [ ] **3.2.4 Consistent Identification (AA):** Buttons and components with identical functions share the same accessible name, icon, and role app-wide.
- [ ] **3.2.5 Change on Request (AAA):** Automatic live data feeds, page reloads, or carousels provide user controls to pause or disable updates.
- [ ] **3.2.6 Consistent Help (2.2 AA Conformance):** Help options (Contact details, FAQ links, AI Chatbots) occupy the same relative DOM order on every page where present.
