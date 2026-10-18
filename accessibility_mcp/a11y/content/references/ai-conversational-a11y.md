# AI Generative & Conversational UI Accessibility Guide (2026)

Accessibility specifications for Generative AI interfaces, LLM Streaming Responses, Prompt Textarea Focus, AI Artifacts, and Multimodal Voice Mode.

> Cross-reference: [W3C Community Group — Accessibility of machine learning and generative AI](https://w3c.github.io/ai-accessibility/) and the [W3C COGA Conversational/Voice Systems Research Module](https://w3c.github.io/coga/research-modules/Conversational-Voice-Systems.html) (Draft Note, public comment through 15 Apr 2026). Tool-execution and file-review specific patterns live in [agentic-ai-messaging-a11y.md](agentic-ai-messaging-a11y.md).

---

## 1. Real-Time LLM Text Streaming & Live Region Management

- **Default announcement contract:** After the user submits with Enter or the Send button, announce exactly one short state, "Digitando...". Keep thinking, web research, tool progress, reasoning, and token deltas silent. When a valid terminal event arrives, replace the live-region content once with the complete final answer.
- **No token announcements:** The visible response may stream character by character, but its container must not be a live region. Never announce tokens, sentences, intermediate paragraphs, phase changes, tool logs, or a separate "concluído" message by default.
- **Single announcement channel:** Keep one persistent, visually hidden `role="status"` region outside the visual transcript; do not repeat its implicit live-region properties. Clear and update it only for "Digitando..." and, later, the complete final response.
- **`aria-busy` Lifecycle (mandatory):** Set `aria-busy="true"` on the response container BEFORE the first token arrives; flip to `aria-busy="false"` only when generation actually completes. Without this, many AT combinations treat partial text as the final message. Set it back to `"true"` on retry/regenerate, and never leave it stuck at `"true"` if a stream errors out (wrap streaming in try/finally so the state flips on both success and failure).
- **Terminal validation:** Announce the accumulated answer only after an explicit successful terminal event. Do not announce partial text after cancellation, timeout, malformed stream, or failure.
- **Region Priming:** Initialize live regions EMPTY and wait ~2–3s before injecting content with `aria-relevant="text"` and `aria-atomic="false"` so screen readers register the region's existence before the first update.
- **Optional alternatives:** A product may offer other announcement modes only as explicit user preferences. The safe default is "Digitando..." followed by one complete-answer announcement.
- **Structured Output Alternative:** Where the product allows it, constrain the LLM to structured JSON (summary, key_points, action_items) and render as semantic HTML (heading + list + table). Structured outputs arrive as complete documents rather than token streams, eliminating the live-region problem entirely and serving multiple presentation modes (prose / scannable / narrated audio) from one source.
- **Cross-AT Testing:** Streaming behavior diverges significantly across screen readers — test with NVDA AND JAWS (not VoiceOver alone). NVDA 2026.1 no longer treats 0-width/height controls as invisible, which can expose previously-hidden "screen-reader only" regions during streams.

### Semantic rendering of model-authored Markdown

- Treat Markdown as a content interchange format, never as the final DOM. Render it with a maintained parser that escapes or rejects raw HTML by default; do not use `dangerouslySetInnerHTML` with model output.
- Map paragraphs to `<p>`, headings to a valid page hierarchy, unordered items to `<ul><li>`, sequential steps to `<ol><li>`, quotations to `<blockquote>`, and tabular data to a semantic `<table>` with headers when appropriate. Never simulate these structures with `<div>`, `<br>`, Unicode bullets, or numbered plain-text lines.
- Reserve ordered lists for instructions whose order matters. A response introduced as “passos”, “procedimento” or “etapas” must produce an `<ol>` in the accessibility tree.
- Do not show decorative Markdown artifacts such as `---`, `***`, `___`, empty `###`, or empty emphasis markers. Prefer spacing and CSS borders for visual separation. A thematic break with genuine document meaning may render as `<hr>`; decorative separators should be omitted.
- Preserve provider deltas verbatim while accumulating them. Never strip `#`, `*`, `_`, or `-` per token: a Markdown marker may span multiple deltas. Reparse the accumulated buffer for visual streaming, and validate the completed response as the authoritative semantic document.
- Do not ask the model to emit HTML as a substitute for frontend rendering. Provider output is untrusted text; prompt it for concise semantic Markdown and let the application create safe HTML.
- Test the completed response DOM, not merely the source string: verify heading order, list roles and item counts with a screen reader or accessibility-tree assertion.

### Transcript order, labels, and operational text

- Keep each turn in causal DOM order: user message; optional thinking control; tool/search activity; final assistant answer; consulted sources. Do not append thinking and tools below the answer merely because the answer placeholder was created first.
- Present the operational trace in one collapsed native disclosure per turn, not as headings or exposed regions. Its `<summary>` starts as “Pensando...” and finishes as “Pensou em Xs” (or “Pensou” below one second). Put thinking-safe status, governance notices, and localized tool summaries inside the disclosure in causal order. The final answer remains outside it. Tool states use product language such as “Pesquisando na web...” and “Executou pesquisa web; navegou em 3 páginas”, never raw protocol identifiers such as `web_search`; use `<p>` or `<span>`, not `h1`–`h6`.
- Use headings only for genuine document structure, such as the assistant answer's own sections or a “Fontes consultadas” section. Operational phases are state, not document outline.
- Name a message author once. Do not combine an article `aria-label="Mensagem de IA Assistente"`, `aria-roledescription="mensagem"`, and a visible heading “IA Assistente”; screen readers will repeat “mensagem” and the author. Prefer one visible author label and an otherwise unlabeled article/group.
- Deduplicate repeated tool cards by stable call identity or normalized tool name plus arguments. Deduplicate sources by canonical URL. Preserve legitimate distinct calls.
- Treat progress lines as transient state. While a tool runs, show details such as “Consultando...” and “Navegando em [página]”. As soon as it completes, remove those lines from the DOM and replace them with one localized persistent outcome, for example “Executou pesquisa web; navegou em 3 páginas”. Aggregate equivalent executions across the whole user/assistant turn, even when assistant text or another operation occurs between them. Do not retain both progress history and completion summary in the default transcript.
- Apply the same state-replacement grammar to every provider and tool category. File operations use “Editando arquivo {nome}...” / “Editando arquivos...” and finish as “Editou um arquivo.” / “Editou arquivos.” Commands use “Executando comando {comando}...” / “Executando comandos...” and finish as “Executou comando {comando}.” / “Executou comandos.” Determine singular/plural from normalized target counts, not from provider branding.
- Keep the final-answer live-region copy transient: insert it once to trigger the completion announcement, then clear the hidden region so virtual-cursor navigation does not encounter a second copy of the response. The visible answer remains the single persistent transcript copy.

### Configuration and meta-agent chats

Apply the same contract to assistants that create or edit agents, workflows, automations, connectors, or settings. A configuration chat is still an AI conversation; do not make its whole transcript `role="log"` or `aria-live`. On submit, announce only “Digitando...”; on a successful terminal response, announce the complete final reply once. Keep the visible transcript static and navigable.

Do not hide tool execution merely because tools change configuration instead of performing the final agent's work. Use the same causal presentation contract in every AI chat: user message, transient ordinary-text thinking state, sanitized tool activity, then final answer. Replace transient tool states with persistent terminal summaries before completion. Examples include “Consultou modelos e capacidades disponíveis.”, “Criou um agente.”, “Atualizou os conectores do agente.” and “Abriu a configuração de servidores MCP.” Never expose raw function names, arguments, credentials, internal IDs, or protocol payloads.

- Use a generic input label and placeholder that describes the action, not a product-specific example that a screen reader may mistake for existing text.
- When the assistant needs a credential, OAuth login, connector, MCP server, or advanced setting, navigate to or open the same accessible configuration component used by the form. Do not ask for secrets in the transcript.
- A context change may move focus to the opened dialog or configuration screen; identify it with a visible heading, place focus at the first required control or safest action, and restore focus when it closes.
- Announce the assistant's final explanatory reply once. Do not add a second “created”, “opened”, or “connected” announcement when that fact is already present in the reply.
- Sensitive capabilities require an accessible confirmation before activation. Automatic capability negotiation never overrides informed consent.

---

## 1.1. Provider Streaming API Reference (2026)

Getting tokens out of the model in the first place.

Section 1 above assumes token-by-token text is already arriving and covers how to render/announce it accessibly. This section is the layer underneath: the actual wire format each major LLM provider uses for streaming, needed before any of the `aria-live`/dual-channel/throttling guidance above has anything to consume. Verified against each provider's own 2026 docs; field names change between provider API generations, so re-check before relying on this if a provider ships a new API version.

**Provider families, by wire format** (5 distinct shapes cover the 7 commonly-integrated providers — several share a format):

| Provider(s) | Transport | Text delta | Tool-call arguments |
|---|---|---|---|
| Gemini (Interactions API) | SSE, `stream: true` | `step.delta` event, `delta.type=="text"` | `delta.type=="arguments_delta"`, partial JSON string — accumulate by step `index` |
| Anthropic (Messages API) | SSE | `content_block_delta`, `delta.type=="text_delta"` | `delta.type=="input_json_delta"` (`partial_json`) — accumulate by block `index`; `content_block_start`/`content_block_stop` bracket each block |
| OpenAI Responses API (also xAI/Grok on this API) | SSE, typed events | `response.output_text.delta` | `response.function_call_arguments.delta` — **or** skip incremental reconstruction entirely: the terminal `response.completed` event carries the *complete* final `response` object, so you can reuse whatever parser you already wrote for the non-streaming call on that one event and only use the `.delta` events for the live visual/announced text. Avoids maintaining two parsers for one API. |
| OpenAI Chat Completions (also most OpenAI-compatible providers: Kimi/Moonshot, Z.AI/GLM, Ollama's OpenAI-compatible endpoint, self-hosted gateways) | SSE, `choices[0].delta` | `choices[0].delta.content` | `choices[0].delta.tool_calls[].index` selects which in-progress call a fragment belongs to; `id`/`function.name` usually arrive whole in the first fragment for that index, `function.arguments` streams as string fragments to concatenate in order |
| Ollama native `/api/chat` (local or Ollama Cloud) | **NDJSON**, not SSE — one JSON object per line, no `data:` prefix | `message.content` per line (partial); reasoning is `message.thinking`, never top-level `thinking` for chat | Accumulate every `message.tool_calls` array across chunks; support multiple/parallel calls and do not assume a single call or a single fixed chunk |

**Practical notes carried over from a real multi-provider implementation:**

- Two response families (OpenAI Responses API, and to a lesser extent Gemini's Interactions API) send a terminal event that repeats the full final object. When that's true, don't hand-roll incremental reconstruction of the final result at all — parse the terminal event with your existing non-streaming parser, and use the `.delta` events purely to feed the live UI/announcement channel. This cuts the amount of provider-specific streaming code roughly in half and removes an entire class of "my incremental reconstruction doesn't match what the blocking call would have returned" bugs.
- Tool-call argument fragments are **not guaranteed to be valid JSON until the block/index closes** (`content_block_stop` for Anthropic, the matching `step.stop` for Gemini, or simply "no more `tool_calls[].index==N` fragments arrived" for OpenAI-shaped streams) — never attempt to `JSON.parse`/`json.loads` a partial argument buffer for a functional purpose; it exists only to know a call is in-progress.
- Apply the "avalanche effect" defense from §1 (throttled batching, dual-channel) at the point where you convert a raw provider delta into whatever your UI-layer live region consumes — not inside the provider parsing code itself. Keeps the parsing layer provider-specific and the accessibility layer provider-agnostic, so adding an 8th provider never touches the a11y code.
- **JSON-leak guard during streaming:** models occasionally emit raw JSON into the text-content channel instead of the tool-call channel (a model-side bug, not a spec violation you can prevent). Buffer the first non-whitespace characters of each streamed text block before forwarding anything live; if it starts with `{`, hold the entire block back and only decide whether to show it (and how) once the block is complete and you can check whether it's actually valid/parseable JSON. This is cheap (one string check) and prevents a user from seeing/hearing a flash of raw protocol JSON that a naive "just forward every delta immediately" implementation would emit.
- For a production-ready Ollama adapter and frontend event reducer, read [ollama-realtime-agent-ui.md](ollama-realtime-agent-ui.md). Do not expose the provider's NDJSON directly to the browser; normalize it at the backend boundary.

---

## 1.2. Case study: don't conflate "live-updating text" with "must auto-announce" (2026-08)

A native desktop AI-agent app (Windows, non-web toolkit) shipped LLM response streaming, then had to walk back an unrequested addition: it wired the OS-level accessible "live region changed" notification (see the wxPython note in [multilanguage-multiplatform-a11y.md §5](multilanguage-multiplatform-a11y.md#5-python-django-streamlit-pyside6--pyqt6-wxpython)) to fire on every streamed chunk, making the screen reader speak automatically as text arrived — mirroring `aria-live="polite"` on the web.

The user's actual, explicitly stated requirement was closer to §2's "Focus Preservation" combined with §1's "User Control" bullet: they wanted to read the streaming response themselves, with arrow keys, at their own pace — with the view **never** auto-scrolling or auto-speaking to follow new content. Two independent, easily-conflated concerns got bundled into one implementation by default:

1. **Visual/data liveness** — does new text appear as the model generates it? (Yes, wanted.)
2. **Assistive-technology auto-announcement** — does a screen reader speak new text unprompted, the moment it appears? (No — this user, and plausibly many others navigating a running conversation transcript manually, did not want this.)

This skill's own §1 already states this correctly in the abstract ("provide an accessibility toggle to turn off real-time text streaming in favor of a single announcement") — the mistake was implementing an opinionated default (auto-announce on) instead of treating it as an explicit choice, and specifically instead of defaulting to **off**. Concrete guidance to apply on every future build of this pattern, native or web:

- Treat auto-announcement of streamed/live content as **opt-in**, not opt-out, unless the product's own accessibility research says otherwise for its specific user base. A manual-navigation transcript (the AT user tabs/arrows through message history themselves, same as a sighted user scrolls) is a legitimate, common preference — it is not a lesser or fallback mode.
- If you do wire up auto-announcement (native: `NotifyWinEvent(EVENT_OBJECT_LIVEREGIONCHANGED, ...)` per §5 of the multi-platform guide; web: `aria-live` per §1 above), keep it toggleable independently of whether streaming itself is on — a user might want live-updating text on screen with zero auto-speech, which is exactly the case that got missed here.
- When a new message arrives while the user is mid-read of an earlier one (native: cursor/insertion-point position in a text control; web: scroll position / reading-order focus), never move their position to follow the new content. Capture the position before appending, restore it after — regardless of whether streaming or auto-announcement is enabled. This is the same rule as §2's "Focus Preservation," just restated for a non-focus cursor/scroll position rather than DOM focus.

---

## 1.3. Contrato de Apresentação da Interface para Respostas de IA (4 Fases)

Especificação completa da **Interface de Usuário Acessível** para exibir o fluxo de resposta de agentes de IA em tempo real (Pensando, Executando Ferramentas / Pesquisa Web, Transmissão incremental e Conclusão). SSE é uma opção entre backend e navegador; não presuma que o provedor também usa SSE (Ollama nativo usa NDJSON):

```text
[Usuário envia prompt] 
       │
       ▼
[1. FASE PENSANDO] ────────► Visualmente "Digitando..."; uma única anunciação após o envio
       │
       ▼
[2. FASE FERRAMENTA/WEB] ──► Regiões navegáveis, sem anunciação automática; HITL modal quando indispensável
       │
       ▼
[3. FASE STREAMING] ───────► Visual delta-a-delta, `aria-busy="true"`, renderização Markdown segura, links descritivos
       │
       ▼
[4. FASE CONCLUSÃO] ───────► `aria-busy="false"`, resposta final completa no único `role="status"`
```

### 1. Fase "Pensando" (Thinking / Reasoning Loop UI)
- **Contêiner Separado:** Exiba por padrão um status curto e seguro (por exemplo, "Analisando a solicitação"). Se o produto optar por mostrar a trilha `message.thinking` do Ollama, mantenha-a separada, recolhível e claramente identificada; não confunda status criado pelo orquestrador com raciocínio emitido pelo modelo.
- **Separação do Conteúdo Final:** O texto de pensamento NUNCA deve se misturar com a resposta final, permitindo que o leitor de tela leia o status de progresso sem poluir o histórico da mensagem principal.
- **Sem Cabeçalho Artificial:** Usar um botão/`<summary>` recolhido com o texto “Ver pensamento da IA”. Ao expandir, mostrar todo o pensamento acumulado como texto comum, antes das ferramentas e da resposta final; não usar `h1`–`h6` para pensamento.

### 2. Fase "Executando Ferramentas & Pesquisando na Web" (Tool & Web Search UI)
- **Sem regiões rotineiras:** Mostrar chamadas e pesquisas como texto comum em ordem causal. Criar uma região nomeada apenas para um painel substancial que o usuário precise localizar como unidade; não criar região por chamada nem uma região “turno ativo”.
- **Logs de Saída Acumulativos:** Mantenha logs visíveis e navegáveis, mas fora de regiões vivas. O leitor de tela deve acessá-los sob demanda, sem falar cada nova linha automaticamente.
- **Confirmação HITL (Human-in-the-Loop):** Modais de permissão crítica usam `role="alertdialog"`, `aria-modal="true"`, foco inicial no botão mais seguro ("Negar/Cancelar"), trava de teclado e restauração de foco ao fechar.
- **Texto Operacional sem Cabeçalho:** Exibir execução, navegação e conclusão em parágrafos/linhas comuns. Colocar essas linhas antes da resposta final e as fontes consultadas depois dela.
- **Substituição no Estado Terminal:** Durante a execução, mostrar linhas transitórias de navegação. Ao receber `tool.completed`, removê-las e manter somente o resumo agregado da execução; não acumular ruído histórico no turno concluído.

### 3. Fase "Transmissão Incremental" (Streaming UI)
- **Visual vs. Leitura Acessível:** O fluxo visual agrega deltas recebidos por SSE, WebSocket ou `fetch()` streaming. O contêiner da resposta ativa mantém `aria-busy="true"` durante toda a geração.
- **Prevenção do Efeito Avalanche:** Para o leitor de tela, a atualização não deve reiniciar a cada token individual; o texto é anunciado em frases/blocos ou no ritmo de navegação manual do usuário.
- **Renderização Segura & JSON-Leak Guard:** Preserve Markdown legítimo e renderize-o com parser seguro/sanitização; não remova `**` ou `--` de cada delta, pois isso altera texto e pode quebrar marcadores divididos entre chunks. Mantenha protocolo e chamadas de ferramenta fora do canal de texto e retenha um possível bloco JSON inicial até classificá-lo.
- **Links Descritivos (WCAG 2.4.4):** Todas as URLs ou resultados de pesquisa web devem ser convertidos em links descritivos `[Nome do Site](URL)` com `target="_blank"` e `aria-label="[Nome] (abre em uma nova aba)"`.

### 4. Fase "Conclusão & Preservação do Foco" (Completion & Focus Retention UI)
- **Encerramento do Estado Ativo:** Mudar para `aria-busy="false"` e inserir uma única vez a resposta completa no canal persistente de anúncio. Não emitir outro aviso "Resposta concluída".
- **Manutenção de Foco:** O foco do teclado NUNCA pula automaticamente para a resposta durante a digitação. O foco permanece no campo de texto (`<textarea>`), permitindo que o usuário navegue pelas mensagens usando atalhos (`Alt + Seta`).

---

## 1.5. WCAG 3.0 status for AI interfaces

WCAG 3.0 dated 3 March 2026 is an incomplete Working Draft. Its potential guidelines, requirements, assertions, scoring, and conformance model can change. Do not claim WCAG 3 conformance, a fixed requirement count, Bronze/Silver/Gold scoring, or a normative AI cognitive-load score from this draft.

Use WCAG 2.2 AA as the current conformance baseline. Use WCAG 3 and W3C AI-accessibility work only as research prompts for user testing, clear language, error recovery, personalization, cognitive load, and emerging interfaces. Automated tools cannot establish the usability of an AI conversation for people with cognitive disabilities; include human evaluation.

---

## 2. Prompt Input Focus Retention & Keyboard Navigation

- **Focus Preservation:** Submitting a prompt (`Enter` or click Send) MUST keep focus inside the prompt textarea. Focus must NEVER auto-jump into the response panel while text streams.
- **Navigation Shortcuts:** Implement global keyboard shortcuts (e.g. `Alt+Down`) or landmark regions enabling users to jump directly from input prompt to the latest generated response/artifact.
- **Drawer Focus Locks:** Floating AI assistant drawers/modals maintain focus traps while active and return focus to trigger button upon dismissal.

---

## 3. AI Tool / Artifact Accessibility Trees

- **Dual Target:** Accessibility tree serves screen readers (NVDA/VoiceOver) AND Autonomous LLM Agents.
- **Artifact Semantics:** Enclose generated code/previews inside `<aside role="complementary" aria-label="Generated Artifact: [Title]">`.
- **Status & Tool Execution:** Long-running actions apply `aria-busy="true"`. Keep routine progress/log text manually navigable and silent by default; use `role="log"` only when append-only auto-announcement is explicitly required. Code blocks need named copy controls, and preview iframes need descriptive `title` attributes.

---

## 4. Multi-Modal Voice & Screen Reader Interaction

- **Barge-in VAD/AEC:** Support sub-150ms Voice Activity Detection (VAD) and Acoustic Echo Cancellation (AEC) barge-in capability to cut off AI TTS immediately when user begins speaking.
- **Audio Ducking:** Automatically lower background application audio or screen reader output when voice agent is speaking.
- **Earcons:** Use distinct non-verbal audio cues to signal Listening, Thinking, Streaming, and Error states.
