# Documents, Media & Video Accessibility Guide (2026)

Specifications for **PDF/UA-2 (ISO 14289-2)**, **EPUB 3.3 (EPUB Accessibility 1.1)**, **WebVTT & Extended Audio Description (WCAG SC 1.2.5/1.2.7)**, **HLS/DASH Streaming Manifest Accessibility**, and **Deafblind Transcripts (SC 1.2.8 / MAUR)**.

---

## 1. PDF/UA-2 (ISO 14289-2 / PDF 2.0) Standards

- **PDF 2.0 Tags:** Mandates structural elements: `Title`, `DocumentFragment`, `Aside`, `FENote` (footnotes/endnotes), `Em`, and `Strong`.
- **Native MathML:** Replaces raster math images with screen-reader-parseable MathML markup inside PDF 2.0 documents.
- **Associated Files (`/AF`):** Embeds CSV, XML, or source document metadata ensuring attachments retain accessibility semantics.
- **Structure Destinations:** Links target structural tags rather than visual coordinates, preventing broken links during reflow.

---

## 2. EPUB 3.3 Accessibility (EPUB Accessibility 1.1)

- **WCAG Baseline:** Conformance to **WCAG 2.x Level AA** is required.
- **Discoverability Metadata:** Mandates Schema.org/Dublin Core metadata: `accessMode`, `accessModeSufficient`, `accessibilityFeature`, `accessibilityHazard`, `accessibilitySummary`, `dcterms:conformsTo`.
- **Page List Navigation:** Mandates `<nav epub:type="page-list">` mapping digital pages to print equivalent page numbers for synchronized reading.

---

## 3. WebVTT & Extended Audio Description (WCAG SC 1.2.5 / 1.2.7)

- **Audio Description (SC 1.2.5 AA):** Spoken description track played during natural dialogue pauses in video.
- **Extended Audio Description (SC 1.2.7 AAA):** When visual content cannot fit in natural dialogue pauses, video playback **must automatically pause** (`video.pause()`), play the extended description, and **automatically resume** (`video.play()`).

---

## 4. HTML5 Custom Media Players & HLS/DASH Manifest Tags

- **HLS Manifest Signaling (`.m3u8`):** Declare accessibility tracks via `#EXT-X-MEDIA` with explicit `CHARACTERISTICS` tags:
  - Audio Description: `CHARACTERISTICS="public.accessibility.describes-video"`
  - Captions: `CHARACTERISTICS="public.accessibility.describes-music-and-sound"`
- **DASH Manifest Signaling (`.mpd`):** Declare accessibility via `<AdaptationSet>` elements using `<Role>` and `<Accessibility>` descriptors.

---

## 5. Deafblind Descriptive Transcripts (SC 1.2.8 / W3C MAUR)

- **Full Sensory Unification:** Combines dialogue + speaker IDs + sound effects (`[door slams]`) + **full visual descriptions** of actions, body language, scene changes, and on-screen graphics into a single document.
- **Refreshable Braille Format:** Linearized plain text or semantic HTML (`<h1>`-`<h6>`, plain timecodes `[03:45]`) that reads without grid/column dependencies.
