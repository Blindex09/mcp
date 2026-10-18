# Multi-Language & Multi-Platform Accessibility Guide (2026)

Accessibility standards, libraries, APIs, and patterns across **Vue 3 / Nuxt 3**, **Svelte 5**, **C# / .NET 9+**, **Flutter / Dart**, **Rust**, **Python**, **PHP / Laravel**, and **Ruby on Rails**.

This is a routing guide, not proof that every library version or platform combination is accessible. Re-check official framework documentation, inspect the produced accessibility tree/semantics tree, and test keyboard, switch, VoiceOver, TalkBack, NVDA, or platform automation as applicable. Across all stacks, expose one meaning once: do not combine a native label with a duplicate automation name, merge a parent while leaving equivalent children exposed, or send the same visible update through an extra announcement channel.

---

## 1. Vue 3 / Nuxt 3 & Svelte 5 (Runes)

### A. Vue 3 / Nuxt 3
- **Reka UI (formerly Radix Vue):** Primary unstyled primitive library powering Nuxt UI v3 and `shadcn-vue`. Encapsulates WAI-ARIA behavior (roving tabindex, focus traps, ARIA attributes).
- **Nuxt 3 Route Announcements:** Built-in `<NuxtRouteAnnouncer />` component announces SPA page transitions to screen readers automatically.

### B. Svelte 5 (Runes)
- **Melt UI & Bits UI:** Built for Svelte 5 **Runes** (`$state`, `$derived`, `$effect`, and snippets replacing Svelte 4 slots).
- **Compiler Warnings:** Svelte 5 enforces strict compile-time a11y warnings (`a11y-click-events-have-key-events`). Filter false positives via `compilerOptions.warningFilter` in `svelte.config.js`.

---

## 2. C# / .NET 9+ (Blazor, .NET MAUI, WinUI 3 / WPF)

### A. Blazor (.NET 9)
- Combine `OnAfterRenderAsync` with lightweight JS Interop (`element.focus()`) to guarantee focus targets post-render.

### B. .NET MAUI Cross-Platform
- **Announcements API:** `SemanticScreenReader.Default.Announce("Message text");` exists for intentional, bounded announcements. Do not call it for streaming text or routine progress, and verify lifecycle behavior on supported targets rather than relying on a universal delay.
- **XAML Attributes:** `AutomationProperties.Name`, `AutomationProperties.HelpText`, `AutomationProperties.LabeledBy`, `AutomationProperties.IsInAccessibleTree`.

### C. WPF & WinUI 3 (UI Automation UIA)
- Custom controls subclass `FrameworkElementAutomationPeer` and override `GetPattern()` and `GetAutomationControlTypeCore()`. Test with FlaUI or Appium.

---

## 3. Flutter / Dart

- **Semantics Widget:** `Semantics(label: 'Submit', hint: 'Double tap to process', button: true, onTap: ...)`
- **MergeSemantics:** Groups child widgets (icon + text) into a single cohesive VoiceOver / TalkBack focus target.
- **ExcludeSemantics:** Hides decorative subtrees from screen reader focus.
- **Announcements API:** Use the current Flutter semantics announcement API only for intentional, bounded outcomes; avoid mirroring visible content or continuous progress into forced speech.
- **Testing Matches:** Enforce touch targets in widget tests via `expectLater(tester, meetsGuideline(androidTapTargetGuideline))`.

---

## 4. Rust (AccessKit Crate)

- **AccessKit:** Universal cross-platform accessibility infrastructure crate powering Bevy (game engine), Iced / Cosmic Desktop, egui, Freya, Slint.
- **Node & Role:** Defines elements with roles (`Role::Button`, `Role::TextInput`) and properties.
- **TreeUpdate:** Atomic diff payloads pushed from GUI code to OS accessibility adapters (`accesskit_windows`, `accesskit_winit`).
- **ActionHandler:** Implements screen reader action event handlers (`Action::Click`, `Action::Focus`).

---

## 5. Python (Django, Streamlit, PySide6 / PyQt6, wxPython)

- **Django 5.0+ Forms:** Auto-generates `aria-describedby` for help text and `aria-invalid="true"` for validation errors.
- **Streamlit:** Theme contrast configuration via `.streamlit/config.toml` and material icon markdown (`:material/icon_name:`).
- **PySide6 / PyQt6 (`QAccessible`):** Custom widgets subclass `QAccessibleInterface` and emit `QAccessibleEvent(widget, QAccessible.Event.NameChanged)`. Register via `QAccessible.installFactory()`.
- **wxPython (Windows, raw MSAA — no built-in "Announce" helper like MAUI/Flutter):** wxPython's `wx.Accessible` only wraps Microsoft Active Accessibility and has no convenience method for "speak this now." To make a screen reader announce that a control's content changed without moving keyboard focus (the native-desktop equivalent of a web `aria-live` region), call the raw Win32 API via `ctypes`:
  ```python
  import ctypes
  EVENT_OBJECT_LIVEREGIONCHANGED = 0x8019
  OBJID_CLIENT = -4
  CHILD_ID_SELF = 0

  def announce_change(control: wx.Window) -> None:
      hwnd = control.GetHandle()
      if hwnd:
          ctypes.windll.user32.NotifyWinEvent(
              EVENT_OBJECT_LIVEREGIONCHANGED, hwnd, OBJID_CLIENT, CHILD_ID_SELF
          )
  ```
  This raw event is Windows-specific and support depends on the widget's actual accessibility implementation; test NVDA, JAWS, and Narrator rather than promising identical behavior. **Treat it as opt-in, not a default** for any growing/streaming text control (chat transcript, log panel): firing it on every content change makes the screen reader speak automatically. Separately, appending to some native text controls can move the caret; capture and restore the user's reading position when the toolkit permits it.

---

## 6. PHP / Laravel (Blade Components & Livewire 3/4)

- **Livewire Focus Management:** Listen for `livewire:navigated` events to shift keyboard focus to main headings (`<h1>`) post-route navigation. Use Alpine.js `x-trap` for modal focus traps.
- **Node Morph Identity:** Apply stable `key(...)` directives on dynamic inputs to prevent Livewire DOM morphing from destroying active focus.

---

## 7. Ruby on Rails (Hotwire / Turbo / Stimulus)

- **Stimulus Focus Management:** Use Stimulus `connect()` to shift focus when dynamic HTML partials are injected.
- **Custom Turbo Stream Focus Action:** Create custom Turbo stream actions (`<turbo-stream action="focus" target="#input-id"></turbo-stream>`).
- **HTML-over-the-Wire Status:** When a Turbo update creates a genuine WCAG status message, update one coordinated persistent announcer with a bounded summary. Ordinary partial replacement remains silent and navigable; do not mirror the entire injected fragment or every stream operation into `aria-live`.
