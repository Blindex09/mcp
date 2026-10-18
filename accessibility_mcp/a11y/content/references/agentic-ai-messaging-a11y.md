# Agentic AI & UI Messaging Accessibility Guide (2026)

Specifications for **Agentic AI UI Accessibility**, **Tool Execution UI**, **Human-in-the-Loop Permission Modals**, **Message Stream Navigation**, and **Rich AI Content Rendering** (Code blocks, Diffs, LaTeX Math, Artifacts).

> This is an actively-forming area of standards, not settled ARIA-APG-style spec. Cross-reference: [W3C Community Group — Accessibility of machine learning and generative AI](https://w3c.github.io/ai-accessibility/) and the [W3C COGA Conversational/Voice Systems Research Module](https://w3c.github.io/coga/research-modules/Conversational-Voice-Systems.html) (Draft Note, public comment period through 15 Apr 2026). Patterns below are synthesized best-practice, not ratified spec — expect them to keep evolving.

---

## 1. Tool Execution Accessibility

### A. Tool Call Cards & Subagent Hierarchies
- **Operational text, not headings:** Render routine tool state as ordinary `<p>`/`<span>` text. Do not add a region and heading for every call; this pollutes landmark and heading navigation. Put optional parameters behind a named disclosure button.
- **One collapsed trace per turn:** Group thinking, governance notices, tool progress, and terminal tool summaries inside one native `<details>` that is closed by default. Update its summary in place from “Pensando...” to “Pensou em Xs”. Keep the final answer outside. Opening the disclosure is the user's explicit request to inspect the trace; never auto-open or auto-announce its contents.
- **Subagent Nesting:** Subagents use nested regions with clear labels: `aria-label="Subagent: Codebase Researcher"`.

### B. Provider-independent execution state
- **Active State (`aria-busy="true"`):** Container sets `aria-busy="true"` during tool execution to prevent screen readers from reading incomplete or unstable outputs.
- **Silent progress:** Keep incremental details visible and manually navigable, but outside `aria-live`/`role="log"` by default. Tool progress must not interrupt the user.
- **Connectors and MCP:** Name the actual connector or MCP server/tool in visible status text. Use structured, localized metadata rather than provider IDs: “Executando Gmail...” / “Executou Gmail; leu 9 mensagens” and “Executando busca no servidor MCP Catálogo...” are patterns, not Gmail-specific rules. Group equivalent executions across the whole turn, but do not merge different connectors, MCP servers, actions, failures requiring attention, or permission decisions.
- **Turn duration:** Show one readable, non-live timer for the whole turn (“Processando há 54s”), then a stable terminal duration (“Processou em 54s”). Never speak every tick or create competing timers for individual tools.
- **Conversation compaction:** When bounded context requires compaction, expose one ordinary-text activity before subsequent model work: “Compactando conversa...”. Replace that same activity in place with “Conversa compactada. Economizou cerca de X tokens.” Do not retain both lines. Label the number as approximate unless it came from the exact tokenizer for the routed model. Keep the full source transcript available according to product retention policy; compaction changes model context, not the user's visible history. Treat this operational status like tool progress: visible and manually readable, outside live regions, so it does not compete with the one automatic final-answer announcement.
- **Direct media results:** Capability-gate image/audio controls. While active, show only “Criando imagem...”, “Descrevendo imagem...”, “Ouvindo...” or “Transcrevendo áudio...”. On completion, replace the progress state with the image, description, audio, or transcription itself; do not prepend a redundant past-tense completion sentence.
- **Replace, do not append:** When a call reaches its terminal state, remove transient progress lines and replace them with one persistent summary.
- **Recovered attempts are not transcript entries:** Keep failed intermediate attempts in technical diagnostics and metrics. If the same operation later succeeds in the turn, remove the transient failure from the ordinary transcript and fold the successful work into the operation summary. If no attempt succeeds, retain one clear terminal failure that tells the user what did not happen and what they can do next.
- **Normalize before rendering:** Convert every provider's tool protocol into application events carrying `operation`, `targets`, `status`, and `affected_count`. Frontend wording must depend on this stable contract, not provider-specific function names.

### B.1 Spoken Semantic State over Color Alone (WCAG 1.4.1)
- **Never rely on color alone:** Tool execution states must NEVER depend solely on visual color indicators (e.g. yellow for running, green for completed, red for failed). Every tool state, count of affected items, and execution duration must be explicitly stated in natural, readable text.
- **Natural spoken phrases with duration:**
  - Running (Gerúndio): `Editando arquivo {nome}...`, `Editando arquivos do projeto...`, `Executando comando...`, `Pesquisando na web...`, `Auditando acessibilidade da página...`
  - Completed (Passado + Duração): `Editou {n} arquivos em {t}s.`, `Editou um arquivo em {t}s.`, `Executou comando em {t}s.`, `Executou pesquisa web em {t}s.`, `Auditoria de acessibilidade concluída em {t}s.`
- **Navigable by Keyboard and Screen Readers:**
  - The tool call card must be focusable in the reading stream (`tabIndex="0"` or native element) with a complete accessible label (`aria-label="Status da ferramenta: Editou 3 arquivos em 2s."`), allowing screen reader users to navigate directly with Arrow keys (`↑` / `↓`) and hear the full spoken status out loud without needing visual inspection.

Recommended operation wording in Portuguese:

| Operation | Running, one target | Running, multiple | Completed, one | Completed, multiple |
|---|---|---|---|---|
| `file_edit` | `Editando arquivo {nome}...` | `Editando arquivos...` | `Editou um arquivo em {t}s.` | `Editou {n} arquivos em {t}s.` |
| `command` | `Executando comando {comando}...` | `Executando comandos...` | `Executou comando em {t}s.` | `Executou {n} comandos em {t}s.` |
| `web_navigation` | `Navegando em {página}` | progressive page lines | `Navegou em 1 página em {t}s.` | `Navegou em {n} páginas em {t}s.` |

When search and page navigation belong to one research block, use one combined terminal line: `Executou pesquisa web; navegou em 1 página em {t}s.` or `Executou pesquisa web; navegou em {n} páginas em {t}s.` Search queries, result counts, page titles, redirects, and failed URLs remain transient or available only in an explicitly opened diagnostic view. Count successful pages, not attempts. Reuse one stable operation/group id so updates replace the existing DOM node instead of appending duplicates.

Use correct localized singular/plural grammar. Do not expose sensitive command arguments, secrets, full private paths, or destructive parameters in the summary. A user-requested diagnostics disclosure may retain sanitized details separately.

### C. High-Risk Permission Modals (Human-in-the-Loop / HITL)
- **ARIA Attributes:** `role="alertdialog"`, `aria-modal="true"`, `aria-labelledby="modal-title"`, `aria-describedby="modal-desc"`.
- **Initial Focus:** Initial focus MUST land on the safest action button ("Decline/Cancel").
- **Focus Trap & Return Focus:** Trap keyboard focus (`Tab`/`Shift+Tab`) inside modal. `Esc` key cancels request. On close/resolve, focus **MUST RETURN** (`document.activeElement`) to the originating message/prompt in the chat timeline.

### E. MCP, connector, and capability configuration

- Reuse one configuration backend and one accessible UI component for both forms and conversational builders. The chat may automate selection and navigation, but must not maintain a smaller shadow configuration model.
- Discover provider/model capabilities live, preserve evidence and unknown states, and expose only supported controls. Do not infer support from a model name. Automatic selection must intersect user intent, application policy, endpoint support, and model support.
- For MCP, treat friendly permission labels as explanation only. Discover exact names through `tools/list`, persist a per-agent technical allowlist, and filter dispatched tools against it. Keep per-call approval enabled by default. An empty-selection UI must not accidentally mean “allow all”.
- If installation requires a catalog key, connector secret, or OAuth, open the existing secure dialog or browser flow. Never place the credential in the conversation, model context, live region, URL, or logs.
- Do not represent browser sandbox automation as control of the user's desktop. Name the real boundary and require a suitable, least-privilege integration for operating-system actions.
- Apply the complete activity presentation contract inside meta-agent/configuration chats too. Internal configuration tools may use simpler sanitized summaries, but they must not disappear from the visible causal transcript. Keep those summaries silent to assistive technology until the one final-answer announcement.

Copyable static transcript pattern:

```html
<section aria-labelledby="creator-title">
  <h2 id="creator-title">Criar agente por conversa</h2>
  <div id="creator-transcript" aria-label="Histórico da conversa"></div>
  <form id="creator-form">
    <label for="creator-input">Descreva o agente que deseja criar</label>
    <textarea id="creator-input"></textarea>
    <button>Enviar</button>
  </form>
</section>
<p id="ai-announcement" class="sr-only" role="status"></p>
```

The transcript intentionally has no `aria-live` or `role="log"`. Append visible user, progress, and assistant nodes there; update `ai-announcement` only with “Digitando...” and the validated final reply.

### D. Multi-File Batch Operations (File Tree + Per-File Review)

When an agent edits multiple files in one turn (the common "apply this refactor across N files" case), a single HITL modal per change doesn't scale — and a silent bulk-apply hides exactly the kind of risk HITL exists to surface. Combine a file-tree list with per-file review:

- **File list as a tree/listbox, not a flat wall of diffs:** `role="tree"` (or `role="listbox"` if there's no folder nesting) with one node per changed file, each labeled with filename + change type (`aria-label="App.tsx, modified"` / `"config.json, deleted"` / `"utils.ts, added"`). Reuse the roving-tabindex + Arrow-key pattern from [examples/treeview.html](../examples/treeview.html) — don't reinvent it for this context.
- **Selecting a file node shows that file's diff** in an adjacent region (`aria-controls` from the tree pointing at the diff container's id), not a modal per file — keeps the reviewer inside one continuous keyboard flow instead of a stack of dialogs.
- **Batch progress announcement:** while an agent applies approved changes across files, a single `role="status"` region announces bounded progress ("Applying changes: file 2 of 5 — utils.ts") — NOT one live-region interruption per file, which produces exactly the "avalanche" screen readers already struggle with during streaming (§ "Real-Time LLM Text Streaming" in [ai-conversational-a11y.md](ai-conversational-a11y.md)).
- **Per-file approve/reject controls:** each file node gets its own `aria-pressed` toggle or explicit Approve/Reject buttons — do not rely on a single top-level "Approve all" as the only path, since that removes the reviewer's ability to accept some files and decline others (a real HITL requirement, not just an a11y one).
- **Do NOT auto-move focus** to the next file after approving/rejecting one — let the reviewer stay in the tree and choose, exactly as SPA route-change focus rules forbid silently relocating focus (Core Principle #7 in [SKILL.md](../SKILL.md)).

---

## 2. Message Stream & Chat Timeline Accessibility

### A. Semantic Landmarks & Heading Hierarchy
- **Chat Timeline Landmark:** Wrap message stream in `<main aria-label="Conversation History">` or `<section role="region" aria-label="Message Stream">`.
- **Individual Messages:** Use an `<article>` or grouped container with one visible author label. Do not duplicate that label with `aria-roledescription` plus `aria-label`.
- **Heading Tree (H1 $\rightarrow$ H6):**
  - `<h1>`: Chat Session Title.
  - `<h2>`: Message Author ("User", "AI Assistant", "System").
  - `<h3>`: Genuine subsections inside AI responses or artifacts. Tool progress and thought state are not headings.

### B. Keyboard Shortcuts Contract
- `Alt + Up` / `Alt + Down`: Jump between messages (`<article>`).
- `Alt + I` / `Ctrl + K`: Jump to prompt textarea (`<textarea aria-label="Type your message">`).
- `Alt + L`: Jump to active tool log.
- `Esc`: Dismiss modal or close artifact inspector.

### C. Streaming Throttling during Thought Loops
- **Visual vs. Accessibility Stream:** Visual stream renders real-time tokens without `aria-live`. The single hidden announcement channel says “Digitando...” on submission and the complete final answer once on successful completion; thought and tool milestones remain silent.
- **Rule:** NEVER shift user programmatic focus while AI text is streaming.
- **Getting the tokens in the first place:** see [ai-conversational-a11y.md §1.1](ai-conversational-a11y.md#11-provider-streaming-api-reference-2026) for the actual wire format per LLM provider (Gemini, Anthropic, OpenAI Responses/Chat Completions, Ollama) — five different SSE/NDJSON shapes cover the commonly-integrated providers.
- **Auto-announce is a separate decision from "is it live":** default it OFF. See the real case study at [ai-conversational-a11y.md §1.2](ai-conversational-a11y.md#12-case-study-dont-conflate-live-updating-text-with-must-auto-announce-2026-08) — an agent tool-execution stream is exactly the kind of surface where it's tempting to wire automatic screen-reader announcement onto every progress update, and exactly where users mid-review of an earlier tool's output don't want to be interrupted by it.

---

## 3. Accessible Rich Content Rendering

### A. Code Blocks & Copy Feedback
- **Scrollability:** `<pre tabindex="0">` enables keyboard users to scroll horizontal code overflow.
- **Copy Feedback Announcer:** Include a dynamic `span[role="status"]` updated after the user activates Copy. Do not repeat the role's implicit `aria-live` properties.

### B. Code Diff Blocks (`+` / `-` Speech Overrides)
Screen readers often ignore line colors and omit `+`/`-` characters. Prefix diff lines with visually hidden speech overrides:
```html
<pre><code>
  <div class="diff-line diff-deleted">
    <span class="sr-only">Removed line:</span>
    <span>- console.log("old");</span>
  </div>
  <div class="diff-line diff-added">
    <span class="sr-only">Added line:</span>
    <span>+ console.log("new 2026 pattern");</span>
  </div>
</code></pre>
```

### B.1 Keyboard Navigation Between Diff Hunks

Sr-only prefixes fix what a screen reader announces per line — they don't fix how a keyboard user *gets* to the next changed line in a diff with hundreds of unchanged lines around it. VS Code's real, shipping "Accessible Diff Viewer" is the reference precedent: it lets users jump directly between changes rather than arrowing through every unchanged line, and dismiss the reviewer without losing their place.

- **Jump-to-next/previous-change**, not just Arrow-key line-by-line: give the diff container a keyboard shortcut that skips from one changed hunk directly to the next, mirroring VS Code's F7 / Shift+F7.
- **Don't reuse F7 verbatim in a browser tab** — VS Code is a desktop (Electron) app; on the open web, `F7` is Firefox's caret-browsing toggle and will fire a native confirm dialog instead of your handler. Bind an in-app-safe combo instead, e.g. `Alt+]` / `Alt+[` (next/previous change) or `Ctrl+Alt+N/P`, and document the exact binding in the diff container's own `aria-keyshortcuts` attribute so AT users can discover it.
- **Announce hunk position on jump:** moving to a hunk should announce something bounded like "Change 2 of 7, modified, line 41" via a `role="status"` region — not just silently move focus.
- **Escape returns focus** to whatever triggered the diff view (the tool-call card or file-tree node), same return-focus contract as the HITL modal in §1C.
- **Accept/reject a single hunk** (as distinct from the whole file) needs its own focusable, labeled control per hunk (`aria-label="Accept change: line 41"` / `"Reject change: line 41"`) — don't make hunk-level accept/reject a hover-only affordance.

### C. LaTeX Math Rendering
- Use native MathML (`<math>`) or `role="math"` with `aria-label="..."`.
- Allows screen reader users to navigate math sub-expressions (numerators, denominators, exponents) element by element using arrow keys.

### D. Interactive Artifacts & Carousels
- **Carousels:** Use `aria-roledescription="carousel"` and `aria-roledescription="slide"`. Inactive slides set `aria-hidden="true"`.
- **Artifact Side-Panel:** Use `role="region" aria-label="Artifact Inspector: [Name]"`. `Esc` key closes panel and returns focus to the message stream trigger.
