# Page Structure Review — judging the content that is not interactive (2026)

`a11y_page_map` gives **facts** about all the content of a page (including open Shadow DOM and every iframe). This guide is how to
**judge** them. Nothing in the map is a verdict: the same fact can be fine or wrong depending on the page. Read the facts, look at the
screenshot (`a11y_screenshot`), and decide with the reasons below.

## 1. Headings and outline
Facts: `headings.outline` (level, text, size), `level_jumps`, `h1_count`, `first_level`.
- Does the outline read like a table of contents of the page? Read only the headings in order: could a screen-reader user find their way?
- A **level jump** (h1 → h3) is often a styling shortcut. Is there a real missing level, or a heading used for its look? Fix the markup, keep the size with CSS.
- Do heading **sizes** match their levels visually? A visual heading that is not a heading (bold `div`) is invisible to the outline; a heading used for its size is noise.
- One `h1` per page is the norm for a page's main topic; several can be legitimate in unusual layouts — decide by content.
- Headings inside Shadow DOM or iframes appear in the same outline with their own frame; check they continue the logic.

## 2. Landmarks
Facts: `landmarks.items`, `repeated_without_distinct_name`, `text_chars_outside_landmarks`.
- Is there exactly one `main`, and does it contain the primary content? Are navigation, header and footer identified?
- Two `nav` (or two `region`) without distinct names are ambiguous: what would you call each?
- Large amounts of text outside any landmark suggest content a landmark-navigating user will skip. Is that content important?
- Do not add landmarks for every block: too many is as bad as none.

## 3. Images and graphics
Facts per image: `alt` (**absent** vs **empty** vs text), `aria_label`, `title_attr`, `in_link_or_button`, `figcaption`, size, `visible`.
- **Absent alt** is a defect for content images (the file name may be read). **Empty alt (`""`)** is a deliberate "decorative" — right only if the image adds nothing.
- Does the alt text describe the **purpose in context**, not the file or a generic word ("image", "photo")? An image inside a link needs alt that says where the link goes.
- Repeated adjacent text and image (a product name beside its photo) usually wants empty alt on one of them. Charts and infographics need a text alternative for the data, not just a title.
- Icons (SVG/`role=img`) that convey meaning need a name; decorative icons should be hidden from assistive technology.
- Judge with the screenshot: what would the person miss if the image did not load?

## 4. Links
Facts: `links.items`, `same_text_different_destination`, `empty_text`, `has_img_only`, `target`.
- Same text pointing to different places ("Read more" ×6) is ambiguous out of context: does the surrounding context or an accessible name disambiguate?
- Link text should make sense on its own. Links that open new windows or files should say so.
- Empty links (icon only) need an accessible name; check `a11y_announce`.
- Different text, same destination is fine (but check consistency).

## 5. Forms and fields
Facts: `forms.forms[].fields` (label, aria, placeholder, autocomplete, required, describedby, fieldset legend), `fields_without_any_name`.
- Every field needs a persistent **label** (a placeholder is not one: it disappears and is not reliably announced).
- Personal-data fields should have `autocomplete` values (WCAG 1.3.5); required fields must be indicated in text, not only by color or an asterisk with no explanation.
- Groups (radios, checkboxes, address parts) need `fieldset/legend` or an equivalent group name.
- Are errors tied to fields (`aria-describedby`/`aria-errormessage`) and announced? Probe by submitting invalid data (in a local/test site) with `a11y_act` and read the effect.

## 6. Tables
Facts: `tables.items` (caption, headers, scope, thead, rows, cols, nested).
- A data table needs header cells (`th`) with correct `scope`; complex tables need explicit header associations. A layout table (no headers, used for positioning) should not be a table.
- Is there a caption or accessible name that says what the table contains? Are sort controls buttons inside headers with state exposed?

## 7. Reading order and visual order
Facts: `reading_order.inverted_pairs`, `inverted_ratio`, `adjacent_inversions_examples`, `css_order_used`, `tabindex_positive`.
- Screen readers and keyboard focus follow the DOM; sighted users follow the layout. Inversions from CSS `order`, floats, grid placement or absolute positioning create a mismatch.
- Look at the examples: is the DOM order still meaningful when read alone? If the visual order is the meaningful one, change the DOM order.
- Any `tabindex` greater than 0 is a smell: it overrides the natural order.

## 8. Media
Facts: `media` (controls, autoplay, muted, loop, tracks, duration).
- Video needs captions (`track kind=captions`) and, when visuals carry information, audio description; audio needs a transcript.
- Autoplay with sound, or moving content that cannot be paused, is a barrier. Are there visible, keyboard-operable controls?

## 9. iframes
Facts: `iframes` (title, src, sandbox), plus a separate map per frame.
- Every meaningful iframe needs a `title` that says what it contains. Is embedded content (video, map, payment, chat) operable by keyboard from inside? Probe with `a11y_dossier` (it lists elements inside iframes).

## 10. Live regions
Facts: `live_regions`.
- Are status messages in regions that already exist at load? A region added at the same time as its text is often not announced.
- Too many assertive regions or regions that update constantly are noise. Prove with `a11y_act` (announcements).

## 11. Hover-only content
Facts: `hover_reveals` (CSS `:hover` rules that change display/visibility/opacity, with trigger selector and counts); `delegated_listeners`.
- A trigger revealed only by `:hover` is unreachable by keyboard and touch unless it also opens on focus/click. Probe with `a11y_act hover` (effect) and `a11y_reach` (can the revealed links be reached?).
- Delegated listeners (document/window) mean actions are handled by an ancestor: the real target of a click is unknown to the dossier; test the behavior instead of trusting the list.

## 12. Document
Facts: `document` (lang, title, dir, viewport meta, parts with other language).
- The page language must be right; parts in another language need their own `lang`. The title should identify the page and the site; `viewport` must not disable zoom.

## 13. Report
For each finding: severity, where, the **fact** that shows it, why it matters to a person, the fix that keeps the design, and how you checked. Include
`a11y_coverage` (what was and was not covered) so a clean result is never read as full coverage. Sample several pages with `a11y_crawl` before generalizing.
