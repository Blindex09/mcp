# Frameworks & Mobile Accessibility Guide (2026)

This document covers modern accessibility patterns across **React**, **Angular 21**, **Android Native (Java/Kotlin/Jetpack Compose)**, and **iOS Native (Swift/SwiftUI)**.

---

## 1. Compliance Touch Target Standard Across Platforms

| Platform / Context | Minimum Touch Target | WCAG Standard | Spacing / Spacing Circle |
| :--- | :--- | :--- | :--- |
| **Web (CSS)** | **24×24 CSS px** | WCAG 2.2 AA (SC 2.5.8) | 24px diameter non-intersecting circle |
| **iOS (UIKit / SwiftUI)** | **44×44 pt** | Apple Human Interface Guidelines | Automatic via native controls / padding |
| **Android (Compose / Views)** | **48×48 dp** | Material Design Accessibility | `Modifier.defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)` |

*Design-system recommendation:* Prefer platform-native targets (44 pt iOS, 48 dp Android) and often 44 CSS px on web. Do not describe 44 CSS px as the WCAG 2.2 AA minimum; SC 2.5.8 AA is 24×24 CSS px with defined exceptions.

---

## 2. React Ecosystem: Headless UI Patterns

### A. React 19 & React Aria Components
- **React 19 `ref` as Prop:** Deprecates `forwardRef`. Custom accessible components accept `ref` directly as a prop, simplifying focus forwarding.
- **Server Actions & `useActionState` Feedback:** Use native `disabled` when activation must be prevented; `aria-disabled` communicates state but does not disable behavior. Announce only feedback that users need immediately, and avoid duplicating persistent visible results in a live region.
- **React Aria Components:** Prefer its documented components for tested semantics, keyboard interaction, focus, and internationalization. Do not assume every component uses draft ARIA or that focus containment is automatic in every composition.

### B. Vue 3.5+ Accessibility
- **SSR-Safe `useId()`:** Native `useId()` for SSR-safe unique ID generation. Guarantees matching IDs between server rendering and client hydration for `<label for="...">` and `aria-labelledby`.
- **Reka UI (Radix Vue):** Primary unstyled accessibility primitive library for Vue 3.5 / Nuxt 3 (shadcn-vue).
- **Teleport Focus Restoration:** Overlays rendered via `<Teleport to="body">` must explicitly trap focus and restore focus to trigger element on unmount.

### C. Svelte 5 Snippets & Runes
- **Snippets (`{#snippet ...}`) & Runes (`$state`, `$derived`):** Svelte 5 replaces slots with snippets. Snippets maintain full ARIA semantic integrity.
- **Bits UI v1 & Melt UI:** Headless accessibility libraries built specifically for Svelte 5 runes.

### D. Radix UI (shadcn/ui Foundation)
- **Architecture:** Unstyled primitive components (`@radix-ui/react-*`).
- **Focus Trapping:** Built on `@radix-ui/react-focus-trap` and `@radix-ui/react-focus-scope`. Automatically manages focus traps in dialogs/popovers and restores focus to triggering elements.

---

## 3. Angular 21 Ecosystem: `@angular/aria` & Signals

### A. `@angular/aria` Directives (Angular 21+)
Angular 21 introduces headless WAI-ARIA directive sets that bind directly to Angular Signals:
- `ngCombobox`, `ngComboboxInput`, `ngListbox`, `ngMenu`, `ngAccordion`.
- Reactive ARIA bindings via Signals: `[attr.aria-expanded]="isOpen()"`. When Signals update, DOM accessibility trees update without Digest cycle overhead.

```typescript
import { Component, signal } from '@angular/core';
import { Combobox, ComboboxInput } from '@angular/aria/combobox';

@Component({
  selector: 'app-custom-combobox',
  imports: [Combobox, ComboboxInput],
  template: `
    <label id="combo-label">Select Option</label>
    <div ngCombobox [value]="selectedOption()">
      <input ngComboboxInput [attr.aria-labelledby]="'combo-label'" />
    </div>
  `
})
export class CustomComboboxComponent {
  selectedOption = signal('Option 1');
}
```

### B. `@angular/cdk/a11y` Core Utilities
- **`LiveAnnouncer`:** Injects dynamic speech announcements into screen reader live regions (`aria-live="polite"` or `assertive`).
- **`FocusMonitor`:** Tracks focus origin (`mouse`, `keyboard`, `touch`, `programmatic`) and applies `.cdk-focused` / `.cdk-keyboard-focused` CSS classes to fulfill WCAG 2.4.13 focus appearance guidelines.
- **`cdkTrapFocus`:** Directive to lock keyboard focus inside modal windows.

---

## 4. Android Native: Jetpack Compose & Kotlin/Java Views

### A. Jetpack Compose Semantics Tree
Android TalkBack and Switch Access inspect the Compose **Semantics Tree** rather than visual nodes.

- **`Modifier.semantics`:** Assigns semantic properties (`contentDescription`, `role`, `stateDescription`, `liveRegion`).
- **`mergeDescendants = true`:** Aggregates child nodes (icon + title + subtitle) into a single TalkBack touch target.
- **`customActions`:** Implements single-pointer / non-drag alternatives for TalkBack actions menu (satisfying WCAG 2.5.7 Dragging Movements).

```kotlin
Column(
    modifier = Modifier.semantics(mergeDescendants = true) {
        stateDescription = "Unread"
        customActions = listOf(
            CustomAccessibilityAction("Mark as Read") {
                markAsRead()
                true
            }
        )
    }
) {
    Text("Alex")
    Text("Hey, are we meeting today?")
}
```

### B. Java / Kotlin Views Interop
- **`AccessibilityNodeInfoCompat` & `AccessibilityDelegateCompat`**: Used in legacy XML layouts to set custom actions, node descriptions, and live regions (`setAccessibilityLiveRegion`).

---

## 5. iOS Native: SwiftUI Accessibility & UIKit

### A. SwiftUI Accessibility Modifiers
- **`accessibilityElement(children:)`**:
  - `.combine`: Merges child views into a single VoiceOver element.
  - `.ignore`: Removes child views from VoiceOver traversal.
  - `.contain`: Maintains independent navigation inside container.
- **`accessibilityRepresentation(representation:)`**: Maps custom visual elements (e.g., custom canvas knob) to a native accessible control (e.g., `Slider`).
- **`accessibilityAddTraits(_:)`**: Adds structural traits (`.isButton`, `.isHeader`, `.isModal`, `.isTabBar`).
- **`accessibilityRotor`**: Registers custom VoiceOver rotor navigation items (e.g., "Error messages", "Headings").

```swift
struct RatingSlider: View {
    @Binding var rating: Double

    var body: some View {
        CustomVisualKnob(value: rating)
            .accessibilityRepresentation {
                Slider(value: $rating, in: 0...5) {
                    Text("User Rating")
                }
            }
    }
}
```

### B. Dynamic Type & `@ScaledMetric`
To support large font accessibility without layout clipping:
- **`@ScaledMetric`**: Automatically scales layout dimensions (padding, frames, icons) relative to Dynamic Type font styles.

### C. UIKit (`UIAccessibility`)
- Properties: `isAccessibilityElement`, `accessibilityLabel`, `accessibilityTraits`, `accessibilityCustomActions`.
- Speech Announcements: `UIAccessibility.post(notification: .announcement, argument: message)`.
- Post speech announcements only for important, bounded events. Do not announce every streamed token or tool-progress update, and do not duplicate labels already spoken by native controls.
