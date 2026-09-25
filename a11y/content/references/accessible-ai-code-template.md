# Accessible AI interface code template

Use `assets/accessible-ai-react/` when building or adapting a web/Electron AI conversation interface. The template consumes provider-neutral events; pair it with any backend that emits the documented envelope. Do not make components parse Ollama, OpenAI, Anthropic, Gemini, xAI, MCP, or connector wire formats directly.

Copy the asset into the target project and adapt visual design around these invariants:

- one turn reducer owns answer, reasoning, tools, sources, media, terminal state, timing, and event ordering;
- visible answer tokens stream outside live regions;
- one hidden `role="status"` announces `Digitando...` after submission and the complete successful answer once;
- focus remains in the prompt; streaming never moves it;
- `aria-busy` belongs to the active turn and clears on every terminal path;
- reasoning and operational state are ordinary text, not headings or landmarks;
- equivalent tools group across the whole turn and transient progress disappears on completion;
- conversation compaction is one replace-in-place activity with an honestly labeled token estimate;
- files, commands, connectors, MCP, research, images, descriptions, audio, and transcription use normalized operation metadata;
- messages expose the author once; ARIA does not duplicate visible labels;
- final Markdown becomes safe semantic HTML; raw model HTML is disabled;
- approval uses native `<dialog>`, safest initial focus, Escape cancellation, and focus restoration.

The asset contains reusable logic rather than product styling:

- `src/ai/eventStream.js`: POST streaming SSE parser with split-frame buffering and terminal validation.
- `src/ai/turnReducer.js`: idempotent provider-neutral event reducer.
- `src/ai/toolPresentation.js`: localized grouping and singular/plural summaries.
- `src/components/AiConversation.jsx`: prompt, transcript, one announcement channel, stop action.
- `src/components/Turn.jsx`: causal semantic rendering.
- `src/components/SafeMarkdown.jsx`: safe Markdown-to-DOM boundary.
- `src/components/ApprovalDialog.jsx`: accessible HITL example.
- `src/accessible-ai.css`: visually hidden content, focus, targets, forced-color-friendly styling.
- `src/ai/turnReducer.test.js`: regression examples for grouping, deduplication, and terminal busy state.

Adaptation requirements:

1. Map the backend's events to the envelope before dispatching. Keep stable `turn_id`, increasing `seq`, normalized `operation`, stable tool/group identity, safe display names, and `affected_count`.
2. Replace Portuguese presentation strings through the product's localization system; preserve grammar and semantics.
3. Render direct media results in place of their transient progress text. Supply useful alternative text, accessible audio controls, and semantic transcript/description text.
4. Add product-specific retry, continue, attachment, source canonicalization, diagnostics, and approval transport without placing them in live regions.
5. Test completed DOM and accessibility-tree output with NVDA plus Chrome/Firefox, keyboard-only use, zoom/reflow, forced colors, reduced motion, and at least one other target screen reader/platform.

Do not copy `node_modules`, build output, logs, credentials, raw provider arguments, or an application's product-specific labels. Do not add `aria-live` to the visible transcript, answer, thinking, activity list, timer, or tool log.
