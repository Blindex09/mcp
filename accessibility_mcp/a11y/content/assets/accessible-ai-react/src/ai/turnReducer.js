import { activityGroup, completedText, isDirectMedia, runningText } from "./toolPresentation.js"

export const initialConversation = { turns: [], activeTurnId: null }

export function createTurn(id, userText, startedAt = performance.now()) {
  return {
    id, userText, answerText: "", reasoningText: "", status: "running", phase: "thinking",
    isBusy: true, startedAt, elapsedMs: 0, lastSeq: 0, error: null,
    activities: {}, activityOrder: [], sources: {}, media: [],
  }
}

function updateTurn(state, turnId, transform) {
  return { ...state, turns: state.turns.map(turn => turn.id === turnId ? transform(turn) : turn) }
}

function reduceActivity(turn, event) {
  const data = event.data || {}
  const group = activityGroup(data)
  const previous = turn.activities[group]
  const activity = previous ? { ...previous, progress: [...previous.progress] } : {
    group, status: "running", text: runningText(data), progress: [], executions: 0,
    affectedCount: 0, displayName: data.display_name, serverName: data.server_name,
    tokensSaved: 0,
    resultAction: data.result_action, itemSingular: data.item_singular, itemPlural: data.item_plural,
  }
  if (event.type === "tool.started") {
    activity.status = "running"
    activity.text = runningText(data)
  } else if (event.type === "tool.progress") {
    activity.progress = [...activity.progress, data.message].filter(Boolean).slice(-5)
  } else if (event.type === "tool.completed") {
    activity.status = "completed"
    activity.progress = []
    activity.executions += 1
    activity.affectedCount += Number(data.affected_count || 0)
    activity.tokensSaved += Number(data.tokens_saved || 0)
    activity.text = completedText(activity)
  } else if (event.type === "tool.failed") {
    activity.status = "failed"
    activity.progress = []
    activity.text = data.message || "A ferramenta não pôde ser executada."
  }
  return {
    ...turn,
    activities: { ...turn.activities, [group]: { ...activity } },
    activityOrder: previous ? turn.activityOrder : [...turn.activityOrder, group],
  }
}

export function conversationReducer(state, event) {
  const turnId = event.turn_id
  if (event.type === "ui.submitted") {
    return { ...state, activeTurnId: turnId, turns: [...state.turns, createTurn(turnId, event.data.text)] }
  }
  const current = state.turns.find(turn => turn.id === turnId)
  if (!current || event.seq <= current.lastSeq || current.status !== "running") return state

  return updateTurn(state, turnId, original => {
    let turn = { ...original, lastSeq: event.seq }
    if (event.type === "status.changed") turn.phase = event.data.phase || "working"
    if (event.type === "reasoning.delta") turn.reasoningText += event.data.text || ""
    if (event.type === "assistant.delta") turn.answerText += event.data.text || ""
    if (event.type.startsWith("tool.")) turn = reduceActivity(turn, event)
    if (event.type === "source.discovered" && event.data.url) {
      turn.sources = { ...turn.sources, [event.data.url]: event.data }
    }
    if (event.type === "media.completed" && isDirectMedia(event.data.operation)) {
      turn.media = [...turn.media, event.data]
      const group = activityGroup(event.data)
      if (turn.activities[group]) {
        const { [group]: removed, ...activities } = turn.activities
        turn.activities = activities
        turn.activityOrder = turn.activityOrder.filter(key => key !== group)
      }
    }
    if (["turn.completed", "turn.failed", "turn.cancelled"].includes(event.type)) {
      turn.status = event.type.split(".")[1]
      turn.isBusy = false
      turn.elapsedMs = Number(event.data.elapsed_ms || performance.now() - turn.startedAt)
      turn.error = event.type === "turn.completed" ? null : event.data.message || "A resposta não foi concluída."
      if (turn.status !== "completed") turn.answerIsPartial = Boolean(turn.answerText)
    }
    return turn
  })
}
