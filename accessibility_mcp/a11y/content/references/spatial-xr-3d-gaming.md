# Spatial Computing (WebXR/AR/VR), 3D Canvas & Gaming Accessibility Guide (2026)

Specifications for **W3C WebXR Accessibility User Requirements (XAUR)**, **3D Spatial Audio Beacons**, **Gaze/Eye-Tracking Selection**, **Three.js / Babylon.js DOM Overlays**, and **Xbox Accessibility Guidelines (XAG/GAG)**.

---

## 1. W3C WebXR Accessibility User Requirements (XAUR 2026)

- **Motion-Agnostic Interaction:** Users must be able to interact without forced 6DoF physical standing, walking, or rapid head gestures.
- **Target Customization:** Bounding box hit-test sizes must support configurable scaling and magnetic target lock-on (3D Fitts' Law).
- **Text & UI Reflow:** 3D menus and HUDs must support dynamic scaling, high-contrast backdrops, and billboard/camera-facing reflow.
- **Audio downmixing:** 1-click mono audio downmix toggle for users with unilateral hearing loss, plus 5 independent volume sliders (Master, Voice, SFX, Ambient, Accessibility Beacons).
- **Vestibular Safety:** FOV vignetting/tunneling during camera movement, horizon anchoring, step-teleportation vs smooth locomotion toggles, and camera re-centering shortcut.

---

## 2. 3D Spatial Audio Beacons & Directional Subtitles

- **Spatial Audio Beacons:** Directional acoustic beacons (repeating ambient spatial sounds with unique pitch/timbre) guide blind users to 3D objectives.
- **3D Directional Subtitles:** Anchor subtitles in 3D space near sound sources or on a fixed HUD overlay, including speaker identification and distance tags (e.g. `[Footsteps approaching behind (3m)]`).

---

## 3. Gaze & Eye-Tracking Selection

- **Dwell Time Customization:** Configurable selection dwell timers (200ms to 2000ms) with radial visual progress indicators.
- **Magnetic Snapping:** Magnetic target lock-on where gaze rays snap automatically to the nearest interactive 3D node.
- **Midas Touch Safeguards:** Combine gaze with a secondary trigger (hardware switch, voice command "Select", or pinch gesture).

---

## 4. 3D Canvas Accessibility (Three.js & Babylon.js)

- **WebXR DOM Overlay API:** Render semantic HTML overlays (`<button>`, `<nav>`, `<dialog>`) directly over 3D scenes in WebXR sessions.
- **Parallel Accessible DOM Tree (PAT):** Mirror 3D scene graphs to an invisible HTML DOM tree. Forward DOM keyboard/screen-reader events to the 3D raycaster.
- **Visual 3D Focus:** Highlight focused 3D meshes with an outline shader or high-contrast material glow when focused via keyboard `Tab`.

---

## 5. Video Game Accessibility Guidelines (XAG & GAG)

- **Motor:** Full control remapping, auto-aim/magnetic lock-on, QTE auto-complete/hold toggles, single-switch support.
- **Vision:** High-contrast mesh outlines, screen reader TTS integration, spatial audio beacons, audio descriptions for 3D cutscenes.
- **Hearing:** 3D directional subtitles, visual sound radar, mono downmixing toggle.
- **Cognitive:** 3D wayfinding pathways / visual trails, pausable sessions, disable time limits.
