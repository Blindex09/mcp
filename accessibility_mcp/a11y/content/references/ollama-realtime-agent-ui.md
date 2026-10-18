# Ollama Real-Time Agent UI Contract

Use this reference when building a chat/agent interface that must show model output, progress, web research, tool execution, approval, errors, cancellation, and completion as they happen.

Official sources: [Chat API](https://docs.ollama.com/api/chat), [Streaming](https://docs.ollama.com/api/streaming), [Thinking](https://docs.ollama.com/capabilities/thinking), [Tool calling](https://docs.ollama.com/capabilities/tool-calling), [Web search](https://docs.ollama.com/capabilities/web-search), and [streaming errors](https://docs.ollama.com/api/errors). Re-check these sources when changing the adapter.

## 1. Keep three layers separate

1. Parse the provider protocol at the backend boundary.
2. Normalize provider chunks into stable application events.
3. Reduce application events into frontend state and accessible presentation.

Never let React components depend directly on Ollama's wire format. Ollama's native REST API streams `application/x-ndjson`; an SSE response from your FastAPI/Node backend is your own transport contract.

### Render answer text as semantic HTML

Ollama returns model-authored text fragments; it does not turn Markdown into browser HTML. Accumulate `message.content` unchanged and render it in the frontend with a safe Markdown parser. Disable raw HTML from model output. Render steps as `<ol><li>`, unordered groups as `<ul><li>`, headings within the page's existing heading hierarchy, and code as `<pre><code>`. Suppress decorative horizontal rules and empty Markdown markers instead of exposing `---`, `****`, or `###` to users and screen readers. Do not regex-strip Markdown from individual NDJSON chunks because markers can be split across chunks.

Include a system instruction requesting semantic Markdown and prohibiting decorative separators, but treat that instruction only as output-quality guidance. The frontend parser and semantic DOM remain the enforcement boundary.

### Preserve causal reading order

Render a turn as: user message → collapsed thinking control → tool/search text → final assistant answer → consulted-source links. Creating an empty assistant placeholder early must not force it ahead of tool events in the DOM. Thinking and tool execution are operational text, not headings: use `<details><summary>` and paragraphs, never `h1`–`h6`. Give each message one author label only, deduplicate equivalent tool calls and canonical source URLs, and clear the hidden final-answer announcer after its one announcement so it does not become a duplicate transcript entry.

Progress events describe the current state, not permanent transcript entries. Render `tool.progress` lines only while the call is running. On `tool.completed`, remove those lines and replace them with a single aggregated summary such as “Executou pesquisa web; navegou em 3 páginas”. Within one user/assistant turn, group repeated executions of the same operation into one evolving activity item and accumulate meaningful totals, for example “Executou pesquisa web; navegou em 6 páginas”. The grouping boundary is the whole turn, not adjacency: intermediate assistant text, reasoning, or a different operation does not open another group for that operation. A new user message starts a new turn and therefore a new set of operation summaries. Do the same for repeated file, command, navigation, and other tool operations. Preserve distinct items only when their outcome, risk, failure, or user action must be understood separately.

Show one visible turn timer such as “Processando há 54s” while work is active and replace it at the terminal state with “Processou em 54s”. Use a semantic timer or ordinary readable text with no live announcement; second-by-second changes must remain discoverable on demand without becoming automatic speech. Start timing when the user turn is submitted, stop it on success, failure, or cancellation, and measure with a monotonic clock on the client or authoritative elapsed metadata from the backend. Do not create one timer per tool.

If the application compacts a long conversation before the next provider call, show “Compactando conversa...” as ordinary operational text and replace the same stable activity item with “Conversa compactada. Economizou cerca de X tokens.” before continuing. Never render start and completion as two transcript rows. Use an exact count only with the routed model's exact tokenizer; otherwise say “cerca de”. Keep both states out of live regions and preserve the original visible transcript even when the provider context receives a summary.

Do not expose a generic “Ver parâmetros” control in the ordinary conversation history. Raw arguments are protocol diagnostics, often noisy or sensitive, and do not help users understand the outcome. If an expert diagnostics mode is explicitly required, validate and redact arguments, place them outside the conversational reading flow, and keep it opt-in.

Although this adapter is Ollama-specific, emit provider-neutral metadata for every tool: `operation` (`file_edit`, `command`, `web_navigation`, or another product-defined value), `targets`, and terminal `affected_count`. This lets the same frontend apply singular/plural file and command wording without inspecting Ollama function-call shapes. See [agentic-ai-messaging-a11y.md](agentic-ai-messaging-a11y.md) for the cross-provider wording matrix.

Treat connectors and MCP as first-class operation families, not generic tools. Connector events should carry `operation: "connector"`, a stable `connector_name`, a localized `display_name`, and, when there is a countable outcome, `result_action`, `affected_count`, `item_singular`, and `item_plural`. This permits “Executando Gmail...” followed by “Executou Gmail; leu 9 mensagens.” without hard-coding Gmail. MCP events should carry `operation: "mcp"`, `server_name`, and the tool's localized `display_name`, producing “Executando busca no servidor MCP Catálogo...” and a corresponding terminal summary. Never infer the connector or server merely from a user-facing sentence when structured metadata is available.

Apply the same whole-turn grouping rule independently per connector and per MCP server/tool/action. Repeated Gmail reads can accumulate into one Gmail-read result, while Gmail send, Slack, and a distinct MCP server remain separate because they represent different outcomes or integrations. Intermediate assistant text does not reset these groups; a new user message does.

Media operations depend on declared provider/model capabilities. Do not display image-generation, vision-description, listening, or transcription controls when the selected route cannot perform them. Use transient present-progress text — “Criando imagem...”, “Descrevendo imagem...”, “Ouvindo...” or “Transcrevendo áudio...” — outside live regions. When the operation finishes, remove that progress text and render the generated image, image description, playable audio, or transcription directly below in the normal result flow. Do not add redundant terminal prose such as “Criou a imagem”, “Ouviu o áudio”, “Descreveu” or “Transcreveu”; the resulting media or text is the completion. Generated images need useful alternative text or an adjacent description, audio needs an accessible player, and transcription/description must be real semantic text.

## 2. Parse native `/api/chat` correctly

Send `stream: true`. Set `think` to a supported boolean or level; GPT-OSS expects `low`, `medium`, or `high`. For every NDJSON line:

```text
chunk.message.thinking    -> reasoning delta
chunk.message.content     -> answer delta
chunk.message.tool_calls  -> zero or more completed tool-call objects
chunk.done                -> provider generation ended
chunk.done_reason         -> provider stop reason
chunk.error               -> mid-stream failure, even when HTTP already started as 200
```

For `/api/chat`, do not read top-level `thinking`. That shape belongs to `/api/generate`; chat uses `message.thinking`.

Decode incrementally, retain an incomplete final line between network chunks, parse only newline-terminated JSON, and flush the decoder at EOF. Treat malformed lines as protocol errors with diagnostics; do not silently discard them.

Accumulate `thinking`, `content`, and every `tool_call` for the assistant message. If tools were requested, append that complete assistant message to conversation history, execute all approved calls, append one `role: "tool"` message per result with the matching `tool_name`, and call the model again. Repeat until a generation produces no tool calls. Put a configurable maximum on agent-loop iterations.

## 3. Normalize to an application event envelope

Use versioned, ordered events. A minimal envelope is:

```json
{
  "v": 1,
  "turn_id": "turn_...",
  "event_id": "evt_...",
  "seq": 17,
  "type": "assistant.delta",
  "ts": "2026-08-05T12:00:00Z",
  "data": { "text": "partial text" }
}
```

Implement at least these event types:

| Event | Required data | Frontend effect |
|---|---|---|
| `turn.started` | model/request metadata | Create active turn; set busy |
| `status.changed` | safe label, phase | Show "thinking", "searching", or "working" status |
| `reasoning.delta` | text | Append to a separate optional/recolhível reasoning panel |
| `assistant.delta` | text | Append exactly once to the active answer |
| `tool.started` | `tool_call_id`, name, arguments | Create a tool card keyed by ID |
| `tool.progress` | `tool_call_id`, message | Append bounded progress/log output |
| `tool.approval_required` | call ID, risk, summary | Open accessible HITL dialog |
| `tool.completed` | call ID, safe result summary | Mark that tool complete |
| `tool.failed` | call ID, safe error | Mark failed; keep other tools independent |
| `source.discovered` | title, URL, optional snippet | Add/update a cited source keyed by canonical URL |
| `turn.completed` | stop reason, usage/timing | Clear busy; announce the complete accumulated answer once |
| `turn.failed` | code, user-safe message, retryable | Clear busy; retain partial answer and show retry |
| `turn.cancelled` | reason | Clear busy; retain and label partial answer |
| `heartbeat` | none | Keep proxies alive; no visible UI change |

Do not overload `tool.started` to mean completion. Do not keep one global `activeToolCall`; store tools by `tool_call_id` plus display order so parallel and sequential calls render correctly.

If using SSE, emit `id:` from `event_id`, an explicit `event:` name, JSON in `data:`, UTF-8 headers, `Cache-Control: no-cache`, and proxy-buffering controls where applicable. Use monotonically increasing `seq` to ignore duplicates and detect gaps. SSE over `fetch()` is appropriate for POST bodies; `EventSource` is GET-only and reconnect-oriented.

## 4. Model the frontend as a reducer

Keep one normalized turn object instead of unrelated state variables:

```text
turn = {
  id, phase, status, isBusy,
  reasoningText, answerText,
  toolsById, toolOrder, sources,
  stopReason, error, lastSeq
}
```

Apply events through one pure reducer. Reject events for another `turn_id`; ignore `seq <= lastSeq`; make terminal events idempotent. Batch visual answer updates with `requestAnimationFrame` or a short buffer to avoid a React render for every tiny token while retaining low perceived latency.

Use one incremental stream parser for the initial request and approval-resume path. Preserve partial SSE frames across `reader.read()` boundaries, support multi-line `data:` fields, flush `TextDecoder` at EOF, and handle JSON parse failures explicitly.

Abort the upstream Ollama request when the browser disconnects or the user cancels. A network EOF without `turn.completed`, `turn.failed`, or `turn.cancelled` is not success.

## 5. Present progress without exposing protocol

- Show safe orchestrator statuses such as "Analisando", "Pesquisando na web" and "Executando ferramenta". Do not fabricate them as model reasoning.
- Keep raw `message.thinking` separate from final content. Make it collapsible or omit it according to product policy; never mix it into the answer or logs.
- Render tool arguments only after schema validation and redact secrets. Treat tool output as untrusted text, not HTML.
- Present web search and web fetch through the same operation summary for the turn when they form one research activity. Emit deduplicated `source.discovered` results as they arrive; do not create one permanent history card for every internal request.
- Preserve legitimate Markdown across delta boundaries. Accumulate raw text first, then render with a safe Markdown parser; never mutate each token with regex cleanup.
- Do not infer tool execution from keywords in the user's prompt. Give the model declared `tools`, consume `message.tool_calls`, validate arguments, authorize/execute server-side, append results, and continue the agent loop.

The native web endpoints are `POST https://ollama.com/api/web_search` with `query` and optional `max_results` (maximum 10), and `POST https://ollama.com/api/web_fetch` with `url`. They require an Ollama API key. For search-heavy agents, Ollama recommends a context length of about 32k or more.

## 6. Accessibility contract

- Stream visually without making the visible token container a live region by default.
- Provide one persistent hidden announcement region. On submission announce "Digitando..."; do not update it at phase boundaries.
- Set `aria-busy="true"` on the active response/turn, not the entire conversation history; clear it on every terminal path.
- Keep the visible streamed answer, reasoning, tools, searches, and logs outside live regions. Do not announce tokens or buffered intermediate blocks.
- Keep keyboard focus and the user's scroll/read position stable. Auto-scroll only while the user is already at the end; otherwise show a "new content" affordance.
- Make tool logs navigable on demand without `role="log"` or `aria-live` in the default mode.
- On `turn.completed`, announce the complete accumulated final answer exactly once. Do not also announce "completed". Do not announce partial output after a truncated, cancelled, or failed stream.
- A critical approval uses an accessible modal/`alertdialog`, initial focus on the safest action, focus containment, Escape behavior, and focus restoration.

## 7. Ollama capability-aware accessibility

Apply these rules only to user-facing behavior. Keep model discovery, routing policy, credentials, and provider administration outside the accessibility layer.

### Model capability controls

- Query model capabilities before rendering provider-specific controls. Expose image upload only when the selected or automatic route can use a `vision` model; expose reasoning controls only for `thinking`; expose agent tools only for `tools`.
- When a control is unavailable, prefer hiding it if it has no value. If users need to understand why it is unavailable, keep it disabled with `aria-describedby` pointing to a concise explanation such as "Este modelo não aceita imagens".
- Announce an automatic model change only when it changes available interaction, for example: "Modelo alterado para análise de imagens". Do not announce internal ranking, fallback order, cost, or provider IDs unless the user asks for diagnostics.
- Preserve the user's prompt, attachments, focus, and reading position when switching or falling back between models.

### Accessible vision and attachments

- Use a visible `<label>` for image upload; state accepted formats, maximum count, and size before selection. Keep the native file input keyboard-operable.
- After selection, announce one bounded summary such as "2 imagens selecionadas" and render a semantic list containing each filename, validation state, and a named Remove button.
- Give meaningful previews alternative text when known. Use `alt=""` only for a preview that duplicates an adjacent filename/description. Never expose base64, object URLs, hashes, or transport metadata as accessible text.
- Associate format, size, upload, safety, and model-compatibility errors with the file input or affected item through `aria-describedby`; use `role="alert"` only when the error blocks submission.
- Keep upload progress separate from answer streaming. Announce coarse milestones or completion, not byte-level progress.
- Identify model-generated image descriptions as AI output. Preserve user-authored alternative text and never silently replace it with a generated description.

### Context limits and truncation

- Warn before submission when prompts, conversation history, attachments, or search results may exceed the selected model's context. Never truncate user content silently.
- State what may be omitted and offer accessible actions: shorten the conversation, remove an attachment, summarize older turns, or choose a larger-context model.
- Keep the warning adjacent to the submit control and programmatically associate it with the prompt. Do not move focus unless submission is blocked.

### Terminal states and stop reasons

- Map provider termination to truthful user-facing states. Announce normal `stop` as completed; token/context limit as incomplete due to limit; user abort as cancelled; timeout/disconnect/provider error as failed with partial content retained.
- Never announce "completed" merely because the network reached EOF. Require a valid terminal event.
- Label retained partial content as partial and provide named Retry/Continue actions. Preserve the user's reading position when more content is appended.

### Retry, rate limits, and fallback

- Present HTTP 429 as a temporary rate limit with an available retry time when known. Present 502/timeouts as provider availability failures. Present mid-stream NDJSON `error` as a failed partial response even when HTTP began with 200.
- Keep error copy short in the assertive channel. Put diagnostics, model IDs, attempt history, and raw provider messages in a user-opened `<details>` region.
- On automatic retry or fallback, announce one bounded state change. Do not announce every internal attempt. Provide Stop and manual Retry controls, and never create an endless retry loop.
- Restore `aria-busy="false"` on every failed, cancelled, or exhausted-retry path.

### Usage and generation details

- Put token counts, timing, `done_reason`, and model information in an optional `<details>` region outside live regions. Do not auto-announce metrics after every response.
- Use semantic description lists or tables for metrics. Include units and human-readable durations; do not rely on color alone for thresholds.
- Do not present log probabilities as factual confidence. If exposed for expert diagnostics, explain their scope and provide equivalent text for any visual chart.

### Compatibility endpoints

- Preserve the same accessible application-event contract when using Ollama's native, OpenAI-compatible, or Anthropic-compatible endpoint. Provider wire format must not change focus, announcements, labels, or terminal-state semantics.
- Test each adapter independently for split frames, tool arguments, reasoning blocks, errors, and completion. Do not infer accessibility equivalence merely because the final text looks the same.

## 8. Definition of done

Verify all of the following:

- Reasoning arrives from `message.thinking`; final text arrives from `message.content`.
- Native NDJSON and browser-facing SSE/WebSocket are parsed independently with boundary tests.
- Multiple and parallel tool calls keep distinct IDs, logs, results, and statuses.
- Repeated calls remain distinct in state/telemetry but are grouped into one concise operation summary per turn in the default interface, even when assistant text or another operation occurs between them. Totals are accumulated; a new user message resets the groups, and failures that require action remain distinguishable.
- The assistant message plus tool results are returned to Ollama until the loop ends.
- Mid-stream `{ "error": ... }`, non-2xx responses, cancellation, timeout, disconnect, malformed frames, and EOF without terminal event all produce non-success terminal UI.
- The final Ollama `done`/`done_reason` and usage/timing metadata are preserved in `turn.completed`.
- No JSON/tool protocol flashes in the answer; no secret appears in tool arguments or logs.
- React rendering is batched, but displayed text remains byte-for-byte equivalent to accumulated answer deltas.
- Screen-reader announcements are bounded; focus and manual reading position do not jump.
- Tests cover split UTF-8 code points, split NDJSON/SSE frames, duplicate events, out-of-order turn IDs, cancel during tool execution, and retry/resume behavior.
