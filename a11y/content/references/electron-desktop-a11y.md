# Electron Desktop Accessibility Guide (2026)

Accessibility APIs, native menu role mapping, focus management across `WebContentsView` / `BrowserWindow`, IPC focus bridges, and Playwright automated testing for **Electron**.

---

## 1. Electron Accessibility APIs

- **`app.accessibilitySupportEnabled`:** Boolean indicating whether Chromium's accessibility tree generator is active.
- **`app.setAccessibilitySupportEnabled(enabled):`** Programmatically forces Chromium's accessibility tree generation ON. Must be invoked after `app.whenReady()`. Use when automatic screen reader detection fails.
- **`accessibility-support-changed` Event:** Emitted on `app` when screen reader status changes:
  ```javascript
  app.on('accessibility-support-changed', (event, accessibilitySupportEnabled) => {
    console.log('Accessibility mode:', accessibilitySupportEnabled);
  });
  ```

---

## 2. Native Menus & Accelerators

- **Native MenuItem Roles:** Use standard `role` properties (`undo`, `copy`, `paste`, `about`, `quit`, `close`) to map actions directly to OS accessibility primitives.
- **Cross-Platform Shortcuts:** Use `CommandOrControl` in `accelerator` so shortcuts automatically map to `Cmd` on macOS and `Ctrl` on Windows/Linux.
- **macOS VoiceOver Overrides:** Use `accessibilityLabel` on `MenuItem` to supply dedicated screen reader descriptions overriding visual labels.

---

## 3. Focus Management & WebContentsView

- **`WebContentsView` Focus:** Modern Electron uses `WebContentsView`. Shift focus programmatically via `view.webContents.focus()`. Wrap refocusing in `setTimeout(..., 0)` to prevent focus fighting loops.
- **Non-Focusable Tooltips / Overlays:** For floating overlays requiring zero focus stealing, prefer a secondary `BrowserWindow` with `{ focusable: false, parent: mainWindow }` over a `WebContentsView`.

---

## 4. IPC Focus Handoff Pattern

Synchronize Main and Renderer processes via IPC:

1. **Main Process Focus Broadcaster:**
   ```javascript
   mainWindow.on('focus', () => mainWindow.webContents.send('window-focus-change', true));
   mainWindow.on('blur', () => mainWindow.webContents.send('window-focus-change', false));
   ```
2. **IPC Focus Request:**
   ```javascript
   // Main process
   ipcMain.handle('focus-target-view', async (event, viewId) => {
     const targetView = getViewById(viewId);
     if (targetView) {
       targetView.webContents.focus();
       return true;
     }
     return false;
   });
   ```
3. **Renderer DOM Focus Alignment:** After native view focus completes, renderer calls `document.querySelector('#main-input').focus()` to maintain screen reader virtual cursor alignment.

---

## 5. Automated Testing with Playwright for Electron

Run automated WCAG audits against Electron windows using `_electron` and `@axe-core/playwright`:

```typescript
import { test, expect, _electron as electron } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

test('Electron main window passes WCAG 2.1 AA checks', async () => {
  const electronApp = await electron.launch({ args: ['.'] });
  const page = await electronApp.firstWindow();
  await page.waitForLoadState('domcontentloaded');

  const scanResults = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  expect(scanResults.violations).toEqual([]);
  await electronApp.close();
});
```

---

## 6. OS Platform Accessibility Mapping

- **Windows:** Chromium maps DOM to **UI Automation (UIA)** & **IAccessible2 (IA2)** for NVDA, JAWS, and Narrator.
- **macOS:** Chromium maps DOM to **NSAccessibility (AXAPI)** for VoiceOver (`AXRole`, `AXTitle`, `AXDescription`).
- **Linux:** Chromium exposes nodes via D-Bus to **AT-SPI2** for Orca.
