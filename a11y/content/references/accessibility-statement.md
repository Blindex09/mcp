# Accessibility Statement (Template — 2026)

Adapt this template for your organization. Publish it at a stable URL (e.g., `/accessibility`).
Be honest about what's fixed, what's in progress, and how users can report issues.

---

## Accessibility Statement for [Organization Name]

[Organization Name] is committed to making our digital services accessible to everyone, including people with disabilities. This statement covers [website/app name] at [URL].

## Conformance status

This [website/application] aims to conform to **WCAG 2.2 Level AA** technical standards. We are also monitoring the **WCAG 3.0 Working Draft** and will adopt relevant practices as the standard matures.

We have audited our key user flows — [homepage, search, checkout, account registration, contact form] — using a combination of:

- **Automated scanning**: axe-core, Lighthouse, WAVE
- **Manual keyboard testing** of every critical flow
- **Screen reader testing**: NVDA (Windows), VoiceOver (macOS/iOS), JAWS (Windows)
- **Mobile assistive tech**: VoiceOver (iOS), TalkBack (Android)

Automated tools detect approximately 30–40% of accessibility issues; we complement them with manual and assistive-technology testing to validate real user experience.

## What we've done

- Restored semantic HTML structure (landmarks, heading hierarchy, `<main>`, `<nav>`).
- Ensured all interactive elements are keyboard-operable with visible focus indicators.
- Added `aria-label` to icon-only buttons and descriptive `alt` text to content images.
- Implemented focus management and `aria-live` announcements for dynamic content and SPA route changes.
- Verified color contrast meets 4.5:1 (normal text) and 3:1 (large text) across all states (default, hover, focus, error, disabled).
- Respected `prefers-reduced-motion`, `prefers-color-scheme`, and `forced-colors` user preferences.

## What's in progress

- [Ongoing] Full keyboard-only pass on [remaining flows].
- [Q2 2026] Migrate the legacy [component] to an accessible design-system primitive.
- [Continuous] Captioning for video content added after [date].

## Known limitations

Despite our efforts, some content may not yet meet all accessibility standards:

- [Describe known gaps honestly — e.g., "third-party widgets on the blog comments may have contrast issues outside our control; we are working with the vendor."]
- Older archived documents may not be fully screen-reader-compatible; contact us for an alternative format.

## Reporting an accessibility issue

If you encounter an accessibility barrier on our site, please let us know so we can fix it:

- **Email**: [accessibility@organization.com]
- **Phone**: [number]
- **Online form**: [URL]

Please include:
- The page URL or screen where you encountered the issue.
- A description of the problem and the assistive technology you are using (e.g., NVDA, VoiceOver, keyboard only).
- What you were trying to do.

We aim to respond within [X] business days and to resolve critical barriers within [Y] days.

## Technical contact

Technical accessibility questions can be directed to [name / team / email].

## Date of last review

[YYYY-MM-DD]