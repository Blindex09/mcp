import { useEffect, useReducer, useRef, useState } from "react"
import { streamPost } from "../ai/eventStream.js"
import { conversationReducer, initialConversation } from "../ai/turnReducer.js"
import { Turn } from "./Turn.jsx"

export function AiConversation({ endpoint = "/api/chat" }) {
  const [state, dispatch] = useReducer(conversationReducer, initialConversation)
  const [prompt, setPrompt] = useState("")
  const [announcement, setAnnouncement] = useState("")
  const [now, setNow] = useState(() => performance.now())
  const inputRef = useRef(null)
  const controllerRef = useRef(null)

  useEffect(() => {
    const timer = setInterval(() => setNow(performance.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  async function submit(event) {
    event.preventDefault()
    const text = prompt.trim()
    if (!text) return
    const turnId = crypto.randomUUID()
    dispatch({ type: "ui.submitted", turn_id: turnId, data: { text } })
    setPrompt("")
    setAnnouncement("Digitando...")
    controllerRef.current = new AbortController()
    inputRef.current?.focus()
    let answerBuffer = ""
    try {
      await streamPost(endpoint, { prompt: text, turn_id: turnId }, providerEvent => {
        const normalized = { ...providerEvent, turn_id: providerEvent.turn_id || turnId }
        if (normalized.type === "assistant.delta") answerBuffer += normalized.data?.text || ""
        dispatch(normalized)
        if (normalized.type === "turn.completed") {
          setAnnouncement(answerBuffer)
          setTimeout(() => setAnnouncement(""), 1500)
        }
      }, controllerRef.current.signal)
    } catch (error) {
      dispatch({ type: "turn.failed", turn_id: turnId, seq: Number.MAX_SAFE_INTEGER, data: { message: error.message } })
    } finally {
      controllerRef.current = null
      inputRef.current?.focus()
    }
  }

  return (
    <main>
      <h1>Conversa com IA</h1>
      <div className="conversation" aria-label="Histórico da conversa">
        {state.turns.map(turn => <div data-turn-id={turn.id} key={turn.id}><Turn turn={turn} now={now} /></div>)}
      </div>
      <form onSubmit={submit}>
        <label htmlFor="prompt">Mensagem</label>
        <textarea
          ref={inputRef} id="prompt" value={prompt} onChange={event => setPrompt(event.target.value)}
          onKeyDown={event => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) submit(event)
          }}
        />
        <button type="submit">Enviar</button>
        {state.activeTurnId && state.turns.find(turn => turn.id === state.activeTurnId)?.isBusy && (
          <button type="button" onClick={() => controllerRef.current?.abort()}>Parar</button>
        )}
      </form>
      <div className="sr-only" role="status">{announcement}</div>
    </main>
  )
}
