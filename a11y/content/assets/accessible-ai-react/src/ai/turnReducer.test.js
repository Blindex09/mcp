import { describe, expect, it, vi } from "vitest"
import { conversationReducer, initialConversation } from "./turnReducer.js"

vi.stubGlobal("performance", { now: () => 1000 })

function event(type, seq, data = {}) { return { type, seq, turn_id: "t1", data } }

describe("accessible AI turn reducer", () => {
  it("groups repeated web tools and removes progress on completion", () => {
    let state = conversationReducer(initialConversation, event("ui.submitted", 0, { text: "pesquise" }))
    state = conversationReducer(state, event("tool.started", 1, { operation: "search_web" }))
    state = conversationReducer(state, event("tool.progress", 2, { operation: "search_web", message: "Navegando em página" }))
    state = conversationReducer(state, event("tool.completed", 3, { operation: "search_web", affected_count: 2 }))
    state = conversationReducer(state, event("tool.completed", 4, { operation: "fetch_web", affected_count: 1 }))
    const turn = state.turns[0]
    expect(turn.activityOrder).toEqual(["web_research"])
    expect(turn.activities.web_research.progress).toEqual([])
    expect(turn.activities.web_research.text).toBe("Executou pesquisa web; navegou em 3 páginas.")
  })

  it("replaces conversation compaction progress with an estimated saving", () => {
    let state = conversationReducer(initialConversation, event("ui.submitted", 0, { text: "Continue" }))
    state = conversationReducer(state, event("tool.started", 1, { operation: "context_compaction" }))
    state = conversationReducer(state, event("tool.completed", 2, {
      operation: "context_compaction", tokens_saved: 1200,
    }))
    const turn = state.turns[0]
    expect(turn.activityOrder).toEqual(["context_compaction"])
    expect(turn.activities.context_compaction.text).toBe(
      "Conversa compactada. Economizou cerca de 1200 tokens."
    )
  })

  it("ignores duplicate events and clears busy only on a terminal event", () => {
    let state = conversationReducer(initialConversation, event("ui.submitted", 0, { text: "olá" }))
    state = conversationReducer(state, event("assistant.delta", 1, { text: "Oi" }))
    state = conversationReducer(state, event("assistant.delta", 1, { text: " repetido" }))
    expect(state.turns[0].answerText).toBe("Oi")
    expect(state.turns[0].isBusy).toBe(true)
    state = conversationReducer(state, event("turn.completed", 2, { elapsed_ms: 1200 }))
    expect(state.turns[0].isBusy).toBe(false)
  })
})
